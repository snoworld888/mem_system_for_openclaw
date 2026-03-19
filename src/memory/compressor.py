"""
记忆压缩器：负责将长对话压缩为摘要，减少token消耗
支持两种模式：
  1. 本地规则压缩（无需LLM，速度快）
  2. LLM摘要压缩（调用外部API，效果好）
"""
from __future__ import annotations
import re
import httpx
from typing import TYPE_CHECKING

from src.memory.models import ConversationTurn
from src.utils.token_counter import count_tokens, truncate_to_tokens

if TYPE_CHECKING:
    from src.config import Settings


def rule_based_compress(turns: list[ConversationTurn], max_tokens: int = 300) -> str:
    """
    基于规则的快速压缩：
    - 提取关键信息句
    - 去除重复内容
    - 保留最重要的轮次
    """
    if not turns:
        return ""

    lines = []
    for turn in turns:
        role_label = "用户" if turn.role == "user" else "助手"
        # 每条只取前150个字符（保留核心信息）
        content = turn.content.strip()
        content = re.sub(r"\s+", " ", content)
        if len(content) > 150:
            content = content[:150] + "..."
        lines.append(f"{role_label}: {content}")

    summary = "\n".join(lines)
    # 如果还超了，再截断
    return truncate_to_tokens(summary, max_tokens)


async def llm_compress(
    turns: list[ConversationTurn],
    settings: "Settings",
    max_tokens: int = 300,
) -> str:
    """
    使用LLM对对话进行摘要压缩（效果好，但需要API调用）
    """
    if not turns or not settings.openai_api_key:
        return rule_based_compress(turns, max_tokens)

    dialogue = "\n".join(
        f"{'用户' if t.role == 'user' else '助手'}: {t.content}"
        for t in turns
    )

    prompt = (
        "请将以下对话压缩为简洁摘要，保留关键信息、决策和重要事实，"
        f"控制在{max_tokens // 3}个汉字以内，用第三人称描述：\n\n{dialogue}"
    )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": settings.compress_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        # 降级到规则压缩
        return rule_based_compress(turns, max_tokens)


def extract_key_facts(text: str) -> list[str]:
    """
    从文本中提取关键事实（用于自动升级为长期记忆）
    基于规则：包含"记住"、"我叫"、"我是"、"我的"等关键词
    """
    facts = []
    sentences = re.split(r"[。！？.!?\n]", text)
    keywords = [
        "记住", "请记住", "我叫", "我是", "我的", "我们", "我需要",
        "我喜欢", "我不喜欢", "我习惯", "我工作", "我住在", "重要",
        "一定要", "必须", "不能", "禁止", "注意",
    ]
    for sent in sentences:
        sent = sent.strip()
        if len(sent) > 5 and any(kw in sent for kw in keywords):
            facts.append(sent)
    return facts[:5]  # 最多返回5条
