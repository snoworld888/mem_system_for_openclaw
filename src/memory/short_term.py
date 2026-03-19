"""
短期记忆管理器
- 维护最近N轮对话（在内存中，基于session）
- 当超出token上限时，自动压缩早期对话为摘要
- 支持持久化到JSON文件
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from src.memory.models import ConversationTurn, ShortTermMemory
from src.memory.compressor import rule_based_compress, llm_compress
from src.utils.token_counter import count_tokens

if TYPE_CHECKING:
    from src.config import Settings


class ShortTermMemoryManager:
    def __init__(self, settings: "Settings"):
        self.settings = settings
        self._sessions: dict[str, ShortTermMemory] = {}
        self._storage_dir = os.path.join(settings.data_dir, "stm")
        os.makedirs(self._storage_dir, exist_ok=True)

    def _session_file(self, session_id: str) -> str:
        safe = session_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self._storage_dir, f"{safe}.json")

    def _load_session(self, session_id: str) -> ShortTermMemory:
        """从磁盘加载session，不存在则新建"""
        if session_id in self._sessions:
            return self._sessions[session_id]
        path = self._session_file(session_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                stm = ShortTermMemory.model_validate(data)
                self._sessions[session_id] = stm
                return stm
            except Exception:
                pass
        stm = ShortTermMemory(session_id=session_id)
        self._sessions[session_id] = stm
        return stm

    def _save_session(self, stm: ShortTermMemory):
        path = self._session_file(stm.session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stm.model_dump(mode="json"), f, ensure_ascii=False, indent=2)

    def add_turn(self, session_id: str, role: str, content: str) -> ConversationTurn:
        """添加一轮对话"""
        stm = self._load_session(session_id)
        tokens = count_tokens(content)
        turn = ConversationTurn(role=role, content=content, token_count=tokens)
        stm.turns.append(turn)
        stm.total_tokens += tokens
        self._save_session(stm)
        return turn

    async def get_recent_turns(
        self,
        session_id: str,
        max_turns: int = 10,
        max_tokens: int = 1500,
        compress_old: bool = True,
    ) -> tuple[list[ConversationTurn], str]:
        """
        获取最近对话轮次。
        返回: (turns列表, 早期摘要)
        自动在token超限时压缩老对话。
        """
        stm = self._load_session(session_id)

        # 先取最近 max_turns 轮
        recent = stm.turns[-max_turns:] if len(stm.turns) > max_turns else stm.turns[:]

        # 检查token是否超限，超限则从头裁剪
        total = sum(t.token_count or count_tokens(t.content) for t in recent)
        while recent and total > max_tokens:
            removed = recent.pop(0)
            total -= removed.token_count or count_tokens(removed.content)

        # 如果有被裁剪的部分，返回已有摘要
        summary = stm.compressed_summary
        return recent, summary

    async def compress_old_turns(self, session_id: str, keep_last: int = 6):
        """
        将历史对话压缩，只保留最后 keep_last 轮在记忆中
        """
        stm = self._load_session(session_id)
        if len(stm.turns) <= keep_last:
            return

        to_compress = stm.turns[:-keep_last]
        kept = stm.turns[-keep_last:]

        # 压缩旧对话
        new_summary = await llm_compress(
            to_compress, self.settings,
            max_tokens=self.settings.stm_compress_tokens
        )

        # 如果已有旧摘要，合并
        if stm.compressed_summary:
            combined = f"{stm.compressed_summary}\n{new_summary}"
            new_summary = rule_based_compress(
                [], max_tokens=self.settings.stm_compress_tokens
            ) or combined[:self.settings.stm_compress_tokens * 3]

        stm.compressed_summary = new_summary
        stm.summary_tokens = count_tokens(new_summary)
        stm.turns = kept
        stm.total_tokens = sum(count_tokens(t.content) for t in kept)
        self._save_session(stm)

    def clear_session(self, session_id: str):
        """清空会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
        path = self._session_file(session_id)
        if os.path.exists(path):
            os.remove(path)

    def get_session_info(self, session_id: str) -> dict:
        stm = self._load_session(session_id)
        return {
            "session_id": session_id,
            "turn_count": len(stm.turns),
            "total_tokens": stm.total_tokens,
            "has_summary": bool(stm.compressed_summary),
            "summary_tokens": stm.summary_tokens,
        }
