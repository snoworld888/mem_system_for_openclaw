"""
Token计数工具（基于tiktoken，快速本地计算）
"""
from __future__ import annotations
import tiktoken

_ENCODER: tiktoken.Encoding | None = None


def get_encoder() -> tiktoken.Encoding:
    global _ENCODER
    if _ENCODER is None:
        # cl100k_base 适用于 GPT-4 / Claude 近似估算
        _ENCODER = tiktoken.get_encoding("cl100k_base")
    return _ENCODER


def count_tokens(text: str) -> int:
    """快速计算文本token数"""
    if not text:
        return 0
    enc = get_encoder()
    return len(enc.encode(text))


def truncate_to_tokens(text: str, max_tokens: int) -> str:
    """将文本截断到指定token数"""
    if not text:
        return text
    enc = get_encoder()
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])


def estimate_messages_tokens(messages: list[dict]) -> int:
    """估算messages列表的token数（含格式overhead）"""
    total = 0
    for msg in messages:
        # 每条消息有约4 token的开销
        total += 4 + count_tokens(msg.get("content", ""))
        total += count_tokens(msg.get("role", ""))
    total += 2  # priming tokens
    return total
