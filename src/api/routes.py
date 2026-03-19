"""
FastAPI REST接口（备用/调试用）
可以用 curl 或 HTTP 客户端测试记忆服务
"""
from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.memory.models import (
    MemoryType, ImportanceLevel, MemoryItem,
    QueryRequest, AddMemoryRequest, AddTurnRequest, SearchRequest,
)
from src.memory.short_term import ShortTermMemoryManager
from src.memory.long_term import LongTermMemoryManager
from src.memory.assembler import ContextAssembler
from src.memory.compressor import extract_key_facts

settings = get_settings()
stm = ShortTermMemoryManager(settings)
ltm = LongTermMemoryManager(settings)
assembler = ContextAssembler(stm, ltm)

app = FastAPI(
    title="Memory Server",
    description="OpenClaw 记忆服务 - 长期/短期/Profile/规则",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "ltm_stats": ltm.get_stats()}


@app.post("/memory/query")
async def query_memory(req: QueryRequest):
    """
    主接口：检索并组装上下文，返回可注入LLM的messages
    """
    ctx = await assembler.assemble(req)
    return {
        "messages": ctx.to_messages(),
        "total_tokens": ctx.total_tokens,
        "has_rules": bool(ctx.rules),
        "has_profile": bool(ctx.profile),
        "ltm_hits": bool(ctx.long_term_relevant),
        "stm_turns": len(ctx.short_term),
    }


@app.post("/memory/turn")
async def add_turn(req: AddTurnRequest):
    """添加一轮对话"""
    turn = stm.add_turn(req.session_id, req.role, req.content)

    # 自动提取事实
    extracted = []
    if settings.auto_extract_facts and req.role == "user":
        facts = extract_key_facts(req.content)
        for fact in facts:
            item = MemoryItem(
                session_id=req.session_id,
                memory_type=MemoryType.LONG_TERM,
                content=fact,
                importance=ImportanceLevel.MEDIUM,
                tags=["auto_extracted"],
            )
            ltm.add_memory(item)
            extracted.append(fact)

    # 检查是否超限
    info = stm.get_session_info(req.session_id)
    compressed = False
    if info["total_tokens"] > settings.stm_max_tokens:
        await stm.compress_old_turns(req.session_id, keep_last=settings.stm_keep_last)
        compressed = True

    return {
        "token_count": turn.token_count,
        "extracted_facts": extracted,
        "auto_compressed": compressed,
    }


@app.post("/memory/save")
async def save_memory(req: AddMemoryRequest):
    """保存到长期记忆"""
    item = MemoryItem(
        session_id=req.session_id,
        memory_type=req.memory_type,
        content=req.content,
        importance=req.importance,
        tags=req.tags,
        metadata=req.metadata,
    )
    mem_id = ltm.add_memory(item)
    return {"id": mem_id}


@app.post("/memory/search")
async def search_memory(req: SearchRequest):
    """语义搜索"""
    results = []
    for mt in req.memory_types:
        hits = ltm.search(
            query=req.query,
            memory_type=mt,
            session_id=req.session_id,
            top_k=req.top_k,
            threshold=req.threshold,
        )
        for item, score in hits:
            results.append({
                "id": item.id,
                "memory_type": mt.value,
                "content": item.content,
                "score": round(score, 4),
                "importance": item.importance.value,
                "tags": item.tags,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return {"results": results[:req.top_k]}


@app.post("/memory/rule")
async def add_rule(content: str, priority: int = 2, tags: list[str] = None):
    """添加准则"""
    item = MemoryItem(
        session_id="global",
        memory_type=MemoryType.RULE,
        content=content,
        importance=ImportanceLevel(priority),
        tags=tags or [],
    )
    mem_id = ltm.add_memory(item)
    return {"id": mem_id}


@app.post("/memory/profile")
async def add_profile(content: str, session_id: str = "global", priority: int = 2):
    """添加用户信息"""
    item = MemoryItem(
        session_id=session_id,
        memory_type=MemoryType.PROFILE,
        content=content,
        importance=ImportanceLevel(priority),
    )
    mem_id = ltm.add_memory(item)
    return {"id": mem_id}


@app.post("/memory/compress/{session_id}")
async def compress_session(session_id: str, keep_last: int = 6):
    """手动压缩session"""
    before = stm.get_session_info(session_id)
    await stm.compress_old_turns(session_id, keep_last=keep_last)
    after = stm.get_session_info(session_id)
    return {
        "before_tokens": before["total_tokens"],
        "after_tokens": after["total_tokens"],
        "saved": before["total_tokens"] - after["total_tokens"],
    }


@app.delete("/memory/session/{session_id}")
async def clear_session(session_id: str):
    """清空短期记忆"""
    stm.clear_session(session_id)
    return {"status": "cleared"}


@app.get("/memory/stats")
async def get_stats(session_id: str = ""):
    return {
        "ltm": ltm.get_stats(),
        "stm": stm.get_session_info(session_id) if session_id else {},
    }
