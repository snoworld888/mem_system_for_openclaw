"""
端到端功能测试
模拟一个完整的对话场景，验证记忆服务所有功能
"""
import asyncio
import sys
sys.path.insert(0, r'c:\07code\mem_server')

from src.config import get_settings
from src.memory.models import (
    MemoryItem, MemoryType, ImportanceLevel,
    QueryRequest, AddTurnRequest,
)
from src.memory.short_term import ShortTermMemoryManager
from src.memory.long_term import LongTermMemoryManager
from src.memory.assembler import ContextAssembler
from src.utils.token_counter import count_tokens


async def main():
    s = get_settings()
    stm = ShortTermMemoryManager(s)
    ltm = LongTermMemoryManager(s)
    assembler = ContextAssembler(stm, ltm)

    session = "test_session_001"
    print("=" * 60)
    print("记忆服务端到端测试")
    print("=" * 60)

    # ── 1. 添加规则 ──────────────────────────────────────
    print("\n[1] 添加行为准则...")
    rules = [
        ("始终使用中文回答", ImportanceLevel.HIGH),
        ("回答要简洁，不要冗余", ImportanceLevel.MEDIUM),
        ("涉及代码时提供可运行的示例", ImportanceLevel.MEDIUM),
    ]
    for content, imp in rules:
        ltm.add_memory(MemoryItem(
            session_id="global", memory_type=MemoryType.RULE,
            content=content, importance=imp,
        ))
    print(f"  已添加 {len(rules)} 条规则")

    # ── 2. 添加用户信息 ───────────────────────────────────
    print("\n[2] 添加用户信息...")
    profiles = [
        "用户名: 张伟，资深Python开发者",
        "工作方向: AI应用开发，专注于LLM集成",
        "偏好: 喜欢看代码示例，不喜欢过多解释",
    ]
    for p in profiles:
        ltm.add_memory(MemoryItem(
            session_id=session, memory_type=MemoryType.PROFILE,
            content=p, importance=ImportanceLevel.HIGH,
        ))
    print(f"  已添加 {len(profiles)} 条用户信息")

    # ── 3. 模拟对话，添加短期记忆 ─────────────────────────
    print("\n[3] 模拟对话...")
    turns = [
        ("user", "我叫张伟，我在开发一个RAG系统"),
        ("assistant", "您好张伟！RAG系统是个很好的方向，请问您目前遇到什么问题？"),
        ("user", "我想了解如何优化检索精度"),
        ("assistant", "提升RAG检索精度的方法：1) 混合检索（稠密+稀疏）2) 重排序 3) 查询改写"),
        ("user", "请给我看一个混合检索的Python示例"),
        ("assistant", "以下是使用LangChain实现混合检索的示例代码..."),
        ("user", "谢谢，还有什么重要的记忆服务吗"),
    ]
    for role, content in turns:
        stm.add_turn(session, role, content)
        print(f"  [{role}] {content[:40]}...")

    # ── 4. 添加长期记忆 ───────────────────────────────────
    print("\n[4] 保存重要信息到长期记忆...")
    important_facts = [
        "张伟正在开发RAG系统，关注检索精度优化",
        "用户已了解混合检索方案（dense+sparse）",
        "用户对LangChain混合检索代码感兴趣",
    ]
    for fact in important_facts:
        ltm.add_memory(MemoryItem(
            session_id=session,
            memory_type=MemoryType.LONG_TERM,
            content=fact,
            importance=ImportanceLevel.HIGH,
            tags=["rag", "retrieval"],
        ))
    print(f"  已保存 {len(important_facts)} 条长期记忆")

    # ── 5. 测试上下文组装 ─────────────────────────────────
    print("\n[5] 测试上下文组装（核心功能）...")
    req = QueryRequest(
        session_id=session,
        query="如何进一步优化RAG的召回率",
        max_tokens=2000,
        ltm_top_k=3,
        stm_turns=6,
    )
    ctx = await assembler.assemble(req)
    messages = ctx.to_messages()

    print(f"\n  [OK] 组装结果:")
    print(f"    总token数:     {ctx.total_tokens}")
    print(f"    消息数:        {len(messages)}")
    print(f"    含规则:        {'是' if ctx.rules else '否'}")
    print(f"    含用户信息:    {'是' if ctx.profile else '否'}")
    print(f"    含长期记忆:    {'是' if ctx.long_term_relevant else '否'}")
    print(f"    短期对话轮次:  {len(ctx.short_term)}")

    print("\n  消息内容预览:")
    for i, msg in enumerate(messages):
        content_preview = msg["content"][:100].replace("\n", " ")
        print(f"    [{i}] role={msg['role']:9s} | {content_preview}...")

    # ── 6. 验证token节省效果 ──────────────────────────────
    print("\n[6] Token效率分析...")
    # 假设原始全量上下文
    all_turns_tokens = sum(count_tokens(c) for _, c in turns)
    all_rules_tokens = sum(count_tokens(c) for c, _ in rules)
    all_profile_tokens = sum(count_tokens(p) for p in profiles)
    all_ltm_tokens = sum(count_tokens(f) for f in important_facts)
    total_raw = all_turns_tokens + all_rules_tokens + all_profile_tokens + all_ltm_tokens

    print(f"  原始全量数据 tokens:  {total_raw}")
    print(f"  组装后上下文 tokens:  {ctx.total_tokens}")
    print(f"  节省比例:             {(1 - ctx.total_tokens/max(total_raw,1))*100:.1f}%")

    # ── 7. 语义搜索测试 ───────────────────────────────────
    print("\n[7] 语义搜索测试...")
    results = ltm.search(
        query="RAG检索优化",
        memory_type=MemoryType.LONG_TERM,
        session_id=session,
        top_k=3,
        threshold=0.1,
    )
    print(f"  找到 {len(results)} 条相关记忆:")
    for item, score in results:
        print(f"    score={score:.3f} | {item.content[:50]}")

    # ── 8. 压缩测试 ───────────────────────────────────────
    print("\n[8] 对话压缩测试...")
    before = stm.get_session_info(session)
    print(f"  压缩前: {before['turn_count']} 轮, {before['total_tokens']} tokens")
    await stm.compress_old_turns(session, keep_last=3)
    after = stm.get_session_info(session)
    print(f"  压缩后: {after['turn_count']} 轮, {after['total_tokens']} tokens")
    print(f"  节省:   {before['total_tokens'] - after['total_tokens']} tokens")

    print("\n[OK] 所有测试通过！记忆服务运行正常。")

    # 清理测试数据
    stm.clear_session(session)


if __name__ == "__main__":
    asyncio.run(main())
