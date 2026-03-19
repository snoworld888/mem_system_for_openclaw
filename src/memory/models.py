"""
记忆数据模型
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"    # 短期记忆：最近对话轮次
    LONG_TERM = "long_term"      # 长期记忆：重要事实/经验
    PROFILE = "profile"          # 常用信息：用户画像
    RULE = "rule"                # 准则：行为规范


class ImportanceLevel(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class MemoryItem(BaseModel):
    """单条记忆"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    memory_type: MemoryType
    content: str
    summary: str = ""            # 压缩摘要，用于快速检索
    importance: ImportanceLevel = ImportanceLevel.MEDIUM
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    accessed_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = 0
    token_count: int = 0         # 缓存token计数，避免重复计算


class ConversationTurn(BaseModel):
    """一轮对话"""
    role: str                     # user / assistant / system
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_count: int = 0


class ShortTermMemory(BaseModel):
    """短期记忆：最近对话窗口"""
    session_id: str
    turns: list[ConversationTurn] = Field(default_factory=list)
    total_tokens: int = 0
    compressed_summary: str = ""  # 被淘汰的早期对话的压缩摘要
    summary_tokens: int = 0


class ProfileItem(BaseModel):
    """用户常用信息条目"""
    key: str                      # 如 "name", "language", "timezone"
    value: str
    description: str = ""
    priority: int = 0             # 越大越优先注入


class RuleItem(BaseModel):
    """行为准则条目"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    category: str = "general"     # general / safety / style / domain
    priority: int = 0             # 越大越优先
    enabled: bool = True


class MemoryContext(BaseModel):
    """组装后的记忆上下文，用于注入给LLM"""
    rules: str = ""               # 准则块
    profile: str = ""             # 用户信息块
    long_term_relevant: str = ""  # 相关长期记忆
    short_term: list[ConversationTurn] = Field(default_factory=list)  # 近期对话
    total_tokens: int = 0

    def to_messages(self) -> list[dict]:
        """转换为标准messages格式"""
        messages = []
        parts = []
        if self.rules:
            parts.append(f"<rules>\n{self.rules}\n</rules>")
        if self.profile:
            parts.append(f"<user_profile>\n{self.profile}\n</user_profile>")
        if self.long_term_relevant:
            parts.append(f"<relevant_memories>\n{self.long_term_relevant}\n</relevant_memories>")
        if parts:
            messages.append({"role": "system", "content": "\n\n".join(parts)})
        for turn in self.short_term:
            messages.append({"role": turn.role, "content": turn.content})
        return messages


class QueryRequest(BaseModel):
    """检索请求"""
    session_id: str
    query: str
    max_tokens: int = 2000        # 最大允许token数
    include_rules: bool = True
    include_profile: bool = True
    ltm_top_k: int = 3            # 长期记忆召回数量
    stm_turns: int = 10           # 短期记忆保留轮数


class AddMemoryRequest(BaseModel):
    """添加记忆请求"""
    session_id: str
    content: str
    memory_type: MemoryType
    importance: ImportanceLevel = ImportanceLevel.MEDIUM
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AddTurnRequest(BaseModel):
    """添加对话轮次请求"""
    session_id: str
    role: str
    content: str


class SearchRequest(BaseModel):
    """语义搜索请求"""
    session_id: str
    query: str
    memory_types: list[MemoryType] = Field(default_factory=lambda: [MemoryType.LONG_TERM])
    top_k: int = 5
    threshold: float = 0.3
