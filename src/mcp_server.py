"""
MCP (Model Context Protocol) Server
面向 OpenClaw / Claude Desktop 等客户端

工具列表：
  1. query_memory         - 检索并组装上下文（主要工具）
  2. add_turn             - 添加对话轮次到短期记忆
  3. save_memory          - 保存到长期记忆/profile/规则
  4. search_memory        - 语义搜索记忆
  5. add_rule             - 添加行为准则
  6. add_profile          - 添加/更新用户常用信息
  7. compress_session     - 手动压缩当前session
  8. get_stats            - 获取记忆统计信息
  9. clear_session        - 清空短期记忆
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool, TextContent, CallToolResult,
    ListToolsResult,
)

from src.config import get_settings
from src.memory.models import (
    MemoryType, ImportanceLevel,
    QueryRequest, AddMemoryRequest, AddTurnRequest, SearchRequest,
    MemoryItem,
)
from src.memory.short_term import ShortTermMemoryManager
from src.memory.long_term import LongTermMemoryManager
from src.memory.assembler import ContextAssembler
from src.memory.compressor import extract_key_facts

logger = logging.getLogger(__name__)

# ── 全局单例 ─────────────────────────────────────────────────────────────
_settings = None
_stm: ShortTermMemoryManager | None = None
_ltm: LongTermMemoryManager | None = None
_assembler: ContextAssembler | None = None


def _init():
    global _settings, _stm, _ltm, _assembler
    if _stm is None:
        _settings = get_settings()
        _stm = ShortTermMemoryManager(_settings)
        _ltm = LongTermMemoryManager(_settings)
        _assembler = ContextAssembler(_stm, _ltm)


# ── MCP工具定义 ──────────────────────────────────────────────────────────
TOOLS: list[Tool] = [
    Tool(
        name="query_memory",
        description=(
            "【主要工具】根据当前查询检索并组装记忆上下文，返回可直接注入LLM的messages列表。"
            "包含准则、用户信息、相关长期记忆、最近对话。严格控制token预算。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "会话ID"},
                "query": {"type": "string", "description": "当前用户输入，用于检索相关记忆"},
                "max_tokens": {"type": "integer", "default": 2000, "description": "最大token预算"},
                "include_rules": {"type": "boolean", "default": True},
                "include_profile": {"type": "boolean", "default": True},
                "ltm_top_k": {"type": "integer", "default": 3, "description": "长期记忆检索数量"},
                "stm_turns": {"type": "integer", "default": 10, "description": "保留最近N轮对话"},
            },
            "required": ["session_id", "query"],
        },
    ),
    Tool(
        name="add_turn",
        description=(
            "添加一轮对话到短期记忆。每次用户发言或AI回复后调用。"
            "当对话过长时自动触发压缩，保持token高效。"
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "role": {"type": "string", "enum": ["user", "assistant", "system"]},
                "content": {"type": "string"},
                "auto_extract": {
                    "type": "boolean",
                    "default": True,
                    "description": "是否自动从内容中提取关键事实存入长期记忆",
                },
            },
            "required": ["session_id", "role", "content"],
        },
    ),
    Tool(
        name="save_memory",
        description="手动保存内容到长期记忆（LONG_TERM类型）",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "content": {"type": "string"},
                "importance": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4],
                    "description": "重要性：1=低, 2=中, 3=高, 4=关键",
                    "default": 2,
                },
                "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                "summary": {"type": "string", "description": "简短摘要，用于向量索引（可选）"},
            },
            "required": ["session_id", "content"],
        },
    ),
    Tool(
        name="search_memory",
        description="语义搜索记忆库，返回相关记忆列表",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "query": {"type": "string"},
                "memory_type": {
                    "type": "string",
                    "enum": ["long_term", "profile", "rule"],
                    "default": "long_term",
                },
                "top_k": {"type": "integer", "default": 5},
                "threshold": {"type": "number", "default": 0.3},
            },
            "required": ["session_id", "query"],
        },
    ),
    Tool(
        name="add_rule",
        description="添加行为准则。准则会在每次对话中自动注入，引导AI行为。",
        inputSchema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "准则内容"},
                "priority": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4],
                    "default": 2,
                    "description": "优先级（越高越靠前）",
                },
                "tags": {"type": "array", "items": {"type": "string"}, "default": []},
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="add_profile",
        description="添加或更新用户常用信息（如姓名、偏好、背景）。每次对话自动注入。",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "default": "global"},
                "content": {"type": "string", "description": "用户信息内容"},
                "priority": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4],
                    "default": 2,
                },
                "tags": {"type": "array", "items": {"type": "string"}, "default": []},
            },
            "required": ["content"],
        },
    ),
    Tool(
        name="compress_session",
        description="手动触发当前session的对话压缩，将早期对话摘要化以节省token",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "keep_last": {"type": "integer", "default": 6, "description": "保留最近N轮"},
            },
            "required": ["session_id"],
        },
    ),
    Tool(
        name="get_stats",
        description="获取记忆服务统计信息",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "default": ""},
            },
            "required": [],
        },
    ),
    Tool(
        name="clear_session",
        description="清空指定session的短期记忆",
        inputSchema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
            },
            "required": ["session_id"],
        },
    ),
]


# ── 工具处理器 ───────────────────────────────────────────────────────────
async def handle_query_memory(args: dict) -> str:
    req = QueryRequest(
        session_id=args["session_id"],
        query=args["query"],
        max_tokens=args.get("max_tokens", 2000),
        include_rules=args.get("include_rules", True),
        include_profile=args.get("include_profile", True),
        ltm_top_k=args.get("ltm_top_k", 3),
        stm_turns=args.get("stm_turns", 10),
    )
    ctx = await _assembler.assemble(req)
    messages = ctx.to_messages()
    return json.dumps({
        "messages": messages,
        "total_tokens": ctx.total_tokens,
        "breakdown": {
            "rules_tokens": len(_settings and ctx.rules or ""),
            "profile_tokens": len(ctx.profile or ""),
            "ltm_tokens": len(ctx.long_term_relevant or ""),
            "stm_turns": len(ctx.short_term),
        },
    }, ensure_ascii=False, indent=2)


async def handle_add_turn(args: dict) -> str:
    session_id = args["session_id"]
    role = args["role"]
    content = args["content"]
    auto_extract = args.get("auto_extract", True)

    turn = _stm.add_turn(session_id, role, content)

    # 自动提取关键事实
    extracted = []
    if auto_extract and role == "user":
        facts = extract_key_facts(content)
        for fact in facts:
            item = MemoryItem(
                session_id=session_id,
                memory_type=MemoryType.LONG_TERM,
                content=fact,
                importance=ImportanceLevel.MEDIUM,
                tags=["auto_extracted"],
            )
            _ltm.add_memory(item)
            extracted.append(fact)

    # 检查是否需要压缩
    info = _stm.get_session_info(session_id)
    compressed = False
    if info["total_tokens"] > _settings.stm_max_tokens:
        await _stm.compress_old_turns(session_id, keep_last=_settings.stm_keep_last)
        compressed = True

    return json.dumps({
        "status": "ok",
        "token_count": turn.token_count,
        "extracted_facts": extracted,
        "auto_compressed": compressed,
        "session_tokens": info["total_tokens"],
    }, ensure_ascii=False)


async def handle_save_memory(args: dict) -> str:
    item = MemoryItem(
        session_id=args["session_id"],
        memory_type=MemoryType.LONG_TERM,
        content=args["content"],
        summary=args.get("summary", ""),
        importance=ImportanceLevel(args.get("importance", 2)),
        tags=args.get("tags", []),
    )
    mem_id = _ltm.add_memory(item)
    return json.dumps({"status": "ok", "id": mem_id}, ensure_ascii=False)


async def handle_search_memory(args: dict) -> str:
    mt = MemoryType(args.get("memory_type", "long_term"))
    results = _ltm.search(
        query=args["query"],
        memory_type=mt,
        session_id=args.get("session_id"),
        top_k=args.get("top_k", 5),
        threshold=args.get("threshold", 0.3),
    )
    items = [
        {"id": item.id, "content": item.content, "score": round(score, 4),
         "importance": item.importance.value, "tags": item.tags}
        for item, score in results
    ]
    return json.dumps({"results": items, "count": len(items)}, ensure_ascii=False, indent=2)


async def handle_add_rule(args: dict) -> str:
    item = MemoryItem(
        session_id="global",
        memory_type=MemoryType.RULE,
        content=args["content"],
        importance=ImportanceLevel(args.get("priority", 2)),
        tags=args.get("tags", []),
    )
    mem_id = _ltm.add_memory(item)
    return json.dumps({"status": "ok", "id": mem_id}, ensure_ascii=False)


async def handle_add_profile(args: dict) -> str:
    item = MemoryItem(
        session_id=args.get("session_id", "global"),
        memory_type=MemoryType.PROFILE,
        content=args["content"],
        importance=ImportanceLevel(args.get("priority", 2)),
        tags=args.get("tags", []),
    )
    mem_id = _ltm.add_memory(item)
    return json.dumps({"status": "ok", "id": mem_id}, ensure_ascii=False)


async def handle_compress_session(args: dict) -> str:
    session_id = args["session_id"]
    keep_last = args.get("keep_last", 6)
    before = _stm.get_session_info(session_id)
    await _stm.compress_old_turns(session_id, keep_last=keep_last)
    after = _stm.get_session_info(session_id)
    return json.dumps({
        "status": "ok",
        "before_tokens": before["total_tokens"],
        "after_tokens": after["total_tokens"],
        "saved_tokens": before["total_tokens"] - after["total_tokens"],
    }, ensure_ascii=False)


async def handle_get_stats(args: dict) -> str:
    ltm_stats = _ltm.get_stats()
    session_id = args.get("session_id", "")
    stm_info = _stm.get_session_info(session_id) if session_id else {}
    return json.dumps({
        "ltm_counts": ltm_stats,
        "stm": stm_info,
    }, ensure_ascii=False, indent=2)


async def handle_clear_session(args: dict) -> str:
    _stm.clear_session(args["session_id"])
    return json.dumps({"status": "ok"}, ensure_ascii=False)


HANDLERS = {
    "query_memory": handle_query_memory,
    "add_turn": handle_add_turn,
    "save_memory": handle_save_memory,
    "search_memory": handle_search_memory,
    "add_rule": handle_add_rule,
    "add_profile": handle_add_profile,
    "compress_session": handle_compress_session,
    "get_stats": handle_get_stats,
    "clear_session": handle_clear_session,
}


# ── MCP Server 入口 ──────────────────────────────────────────────────────
async def run_mcp_server():
    _init()
    server = Server("mem-server")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        handler = HANDLERS.get(name)
        if not handler:
            return [TextContent(type="text", text=json.dumps({"error": f"未知工具: {name}"}))]
        try:
            result = await handler(arguments)
            return [TextContent(type="text", text=result)]
        except Exception as e:
            logger.exception(f"工具 {name} 执行失败")
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_mcp_server())
