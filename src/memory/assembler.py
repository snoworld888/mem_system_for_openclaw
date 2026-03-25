"""
记忆上下文组装器
- 将各类记忆拼装为最终注入LLM的上下文
- 严格控制总token数，按优先级裁剪
- 准则 > 用户信息 > 相关长期记忆 > 短期对话
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from src.memory.models import (
    MemoryContext, MemoryType, ImportanceLevel,
    QueryRequest, ConversationTurn,
)
from src.utils.token_counter import count_tokens, truncate_to_tokens

if TYPE_CHECKING:
    from src.memory.short_term import ShortTermMemoryManager
    from src.memory.long_term import LongTermMemoryManager


class ContextAssembler:
    """
    组装最终上下文，平衡准确性和token消耗。
    分配策略（默认 max_tokens=2000）：
      - 准则 (rules):    最多 300 tokens（固定优先保留）
      - 用户信息 (profile): 最多 200 tokens
      - 长期记忆:          最多 600 tokens
      - 短期对话:          剩余 token（保证至少有最近几轮）
    """

    RULE_BUDGET = 300
    PROFILE_BUDGET = 200
    LTM_BUDGET = 600

    def __init__(
        self,
        stm: "ShortTermMemoryManager",
        ltm: "LongTermMemoryManager",
    ):
        self.stm = stm
        self.ltm = ltm

    async def assemble(self, req: QueryRequest) -> MemoryContext:
        ctx = MemoryContext()
        used_tokens = 0
        max_tokens = req.max_tokens

        # ── 1. 准则（最高优先，强制保留）───────────────────────────
        if req.include_rules:
            rules_text = self._build_rules()
            if rules_text:
                budget = min(self.RULE_BUDGET, max_tokens // 6)
                rules_text = truncate_to_tokens(rules_text, budget)
                ctx.rules = rules_text
                used_tokens += count_tokens(rules_text)

        # ── 2. 用户画像（次优先）────────────────────────────────────
        if req.include_profile:
            profile_text = self._build_profile(req.session_id)
            if profile_text:
                budget = min(self.PROFILE_BUDGET, max(50, max_tokens - used_tokens - 1000))
                profile_text = truncate_to_tokens(profile_text, budget)
                ctx.profile = profile_text
                used_tokens += count_tokens(profile_text)

        # ── 3. 长期记忆（语义检索）──────────────────────────────────
        remaining_for_ltm = min(
            self.LTM_BUDGET,
            max(0, max_tokens - used_tokens - 400),  # 至少留400给短期
        )
        if remaining_for_ltm > 50 and req.ltm_top_k > 0:
            ltm_text = self._build_ltm(
                req.session_id, req.query,
                top_k=req.ltm_top_k,
                max_tokens=remaining_for_ltm,
            )
            if ltm_text:
                ctx.long_term_relevant = ltm_text
                used_tokens += count_tokens(ltm_text)

        # ── 4. 短期记忆（最近对话）──────────────────────────────────
        stm_budget = max(200, max_tokens - used_tokens)
        if req.stm_turns <= 0:
            # stm_turns=0 明确表示不需要任何对话轮次
            turns, old_summary = [], None
        else:
            turns, old_summary = await self.stm.get_recent_turns(
                req.session_id,
                max_turns=req.stm_turns,
                max_tokens=stm_budget,
            )

        # 如果有历史摘要，插入到profile块
        if old_summary:
            summary_note = f"\n\n[早期对话摘要]\n{truncate_to_tokens(old_summary, 200)}"
            ctx.profile = (ctx.profile or "") + summary_note
            used_tokens += count_tokens(summary_note)

        ctx.short_term = turns
        used_tokens += sum(count_tokens(t.content) for t in turns)

        ctx.total_tokens = used_tokens
        return ctx

    def _build_rules(self) -> str:
        """从LTM获取所有规则，按优先级排序，去重"""
        items = self.ltm.get_all(MemoryType.RULE)
        if not items:
            return ""
        # 按importance排序，内容去重
        items.sort(key=lambda x: x.importance.value, reverse=True)
        seen = set()
        lines = []
        for item in items:
            key = item.content.strip()[:60]
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {item.content}")
        return "\n".join(lines)

    def _build_profile(self, session_id: str) -> str:
        """构建用户画像文本"""
        items = self.ltm.get_all(MemoryType.PROFILE, session_id=session_id)
        if not items:
            # 尝试全局profile（无session过滤）
            items = self.ltm.get_all(MemoryType.PROFILE)
        if not items:
            return ""
        items.sort(key=lambda x: x.importance.value, reverse=True)
        lines = [item.content for item in items[:10]]
        return "\n".join(lines)

    def _build_ltm(
        self,
        session_id: str,
        query: str,
        top_k: int,
        max_tokens: int,
    ) -> str:
        """语义检索相关长期记忆，控制token预算"""
        results = self.ltm.search(
            query=query,
            memory_type=MemoryType.LONG_TERM,
            session_id=session_id,
            top_k=top_k,
            threshold=0.1,  # 使用较低阈值保证召回，上层用score排序
        )
        if not results:
            return ""

        seen = set()  # 去重
        lines = []
        budget_left = max_tokens
        for item, score in results:
            # 去重
            content_key = item.content[:50]
            if content_key in seen:
                continue
            seen.add(content_key)
            # 只取摘要或截断内容
            text = truncate_to_tokens(item.content, min(200, budget_left))
            tokens = count_tokens(text)
            if budget_left - tokens < 0:
                break
            lines.append(f"[score={score:.2f}] {text}")
            budget_left -= tokens
            # 更新访问记录
            self.ltm.update_access(MemoryType.LONG_TERM, item.id)

        return "\n".join(lines)
