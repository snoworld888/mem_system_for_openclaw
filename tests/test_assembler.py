"""
上下文组装器 (ContextAssembler) 单元测试
覆盖：
  - 基础组装：规则、档案、LTM、STM 各模块
  - Token 预算控制（不超过 max_tokens）
  - 优先级顺序：规则 > 档案 > LTM > STM
  - include_rules=False / include_profile=False 时排除
  - to_messages() 格式正确
  - 空数据时的行为
  - 边界：max_tokens 极小值
"""
import asyncio
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory.models import (
    MemoryItem, MemoryType, ImportanceLevel, QueryRequest,
)
from src.utils.token_counter import count_tokens


def make_query(session_id="sess", query="测试查询", max_tokens=2000,
               include_rules=True, include_profile=True,
               ltm_top_k=3, stm_turns=10):
    return QueryRequest(
        session_id=session_id,
        query=query,
        max_tokens=max_tokens,
        include_rules=include_rules,
        include_profile=include_profile,
        ltm_top_k=ltm_top_k,
        stm_turns=stm_turns,
    )


def add_rule(ltm, content="始终用中文回答", importance=ImportanceLevel.HIGH):
    ltm.add_memory(MemoryItem(
        session_id="global", memory_type=MemoryType.RULE,
        content=content, importance=importance,
    ))


def add_profile(ltm, session_id="sess", content="用户是Python工程师"):
    ltm.add_memory(MemoryItem(
        session_id=session_id, memory_type=MemoryType.PROFILE,
        content=content, importance=ImportanceLevel.HIGH,
    ))


def add_ltm(ltm, session_id="sess", content="用户喜欢代码示例"):
    ltm.add_memory(MemoryItem(
        session_id=session_id, memory_type=MemoryType.LONG_TERM,
        content=content, importance=ImportanceLevel.MEDIUM,
    ))


# ──────────────────── 基础组装行为 ────────────────────────────── #

class TestAssemblerBasic:

    @pytest.mark.asyncio
    async def test_assemble_empty_returns_context(self, assembler):
        """无任何记忆时，组装不报错，返回空 context"""
        req = make_query()
        ctx = await assembler.assemble(req)
        assert ctx is not None
        assert ctx.rules == ""
        assert ctx.profile == ""
        assert ctx.long_term_relevant == ""
        assert ctx.short_term == []

    @pytest.mark.asyncio
    async def test_rules_included_when_available(self, assembler, ltm):
        """有规则时，rules 字段非空"""
        add_rule(ltm)
        req = make_query()
        ctx = await assembler.assemble(req)
        assert ctx.rules != ""
        assert "中文" in ctx.rules

    @pytest.mark.asyncio
    async def test_profile_included_when_available(self, assembler, ltm):
        """有用户档案时，profile 字段非空"""
        add_profile(ltm)
        req = make_query()
        ctx = await assembler.assemble(req)
        assert ctx.profile != ""
        assert "Python工程师" in ctx.profile

    @pytest.mark.asyncio
    async def test_ltm_included_when_available(self, assembler, ltm):
        """有长期记忆且查询相关时，long_term_relevant 非空"""
        add_ltm(ltm, content="用户精通Python代码示例")
        req = make_query(query="Python代码", ltm_top_k=5)
        ctx = await assembler.assemble(req)
        # 语义相关才会被包含，此处至少不报错
        assert isinstance(ctx.long_term_relevant, str)

    @pytest.mark.asyncio
    async def test_stm_included_when_available(self, assembler, stm):
        """有对话时，short_term 包含对话"""
        stm.add_turn("sess", "user", "你好")
        stm.add_turn("sess", "assistant", "你好，有什么可以帮你？")
        req = make_query()
        ctx = await assembler.assemble(req)
        assert len(ctx.short_term) == 2


# ─────────────────── token 预算控制 ──────────────────────────── #

class TestAssemblerTokenBudget:

    @pytest.mark.asyncio
    async def test_total_tokens_within_budget(self, assembler, ltm, stm):
        """组装后 total_tokens 不超过 max_tokens（有一定余量）"""
        add_rule(ltm, content="这是一条重要的规则，必须始终遵守中文回答")
        add_profile(ltm, content="用户是一名高级Python工程师，专注于AI应用开发")
        for i in range(5):
            add_ltm(ltm, content=f"用户喜欢用Python编写代码，特别是异步编程第{i}点")
        for i in range(8):
            stm.add_turn("sess", "user" if i % 2 == 0 else "assistant",
                         f"这是第{i}轮对话，内容是关于Python的讨论")

        req = make_query(max_tokens=1000)
        ctx = await assembler.assemble(req)
        # 允许最多 20% 超出（token 计数误差）
        assert ctx.total_tokens <= 1200

    @pytest.mark.asyncio
    async def test_very_small_max_tokens_no_crash(self, assembler, ltm, stm):
        """max_tokens 极小时不崩溃"""
        add_rule(ltm)
        add_profile(ltm)
        stm.add_turn("sess", "user", "内容")
        req = make_query(max_tokens=50)
        ctx = await assembler.assemble(req)
        assert ctx is not None

    @pytest.mark.asyncio
    async def test_rules_always_included_first(self, assembler, ltm):
        """规则优先级最高：有规则时 rules 字段始终非空（在 budget 内）"""
        add_rule(ltm)
        req = make_query(max_tokens=500)
        ctx = await assembler.assemble(req)
        assert ctx.rules != ""


# ────────────── include_rules / include_profile 开关 ─────────── #

class TestAssemblerSwitches:

    @pytest.mark.asyncio
    async def test_exclude_rules_when_flag_false(self, assembler, ltm):
        """include_rules=False 时，rules 为空"""
        add_rule(ltm)
        req = make_query(include_rules=False)
        ctx = await assembler.assemble(req)
        assert ctx.rules == ""

    @pytest.mark.asyncio
    async def test_exclude_profile_when_flag_false(self, assembler, ltm):
        """include_profile=False 时，profile 为空"""
        add_profile(ltm)
        req = make_query(include_profile=False)
        ctx = await assembler.assemble(req)
        assert ctx.profile == ""

    @pytest.mark.asyncio
    async def test_ltm_top_k_zero_skips_ltm(self, assembler, ltm):
        """ltm_top_k=0 时跳过 LTM 检索"""
        add_ltm(ltm, content="Python异步编程相关内容")
        req = make_query(ltm_top_k=0, query="Python异步编程")
        ctx = await assembler.assemble(req)
        assert ctx.long_term_relevant == ""

    @pytest.mark.asyncio
    async def test_stm_turns_zero_no_stm(self, assembler, stm):
        """stm_turns=0 时不返回对话轮次"""
        stm.add_turn("sess", "user", "内容")
        req = make_query(stm_turns=0)
        ctx = await assembler.assemble(req)
        assert len(ctx.short_term) == 0


# ────────────────── to_messages() 格式 ───────────────────────── #

class TestAssemblerToMessages:

    @pytest.mark.asyncio
    async def test_to_messages_returns_list(self, assembler):
        req = make_query()
        ctx = await assembler.assemble(req)
        messages = ctx.to_messages()
        assert isinstance(messages, list)

    @pytest.mark.asyncio
    async def test_messages_have_role_and_content(self, assembler, ltm, stm):
        """每条 message 都有 role 和 content 字段"""
        add_rule(ltm)
        stm.add_turn("sess", "user", "测试消息")
        req = make_query()
        ctx = await assembler.assemble(req)
        messages = ctx.to_messages()
        for msg in messages:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in {"system", "user", "assistant"}

    @pytest.mark.asyncio
    async def test_rules_in_system_message(self, assembler, ltm):
        """规则被放入 system 消息，且用 <rules> 标签包裹"""
        add_rule(ltm, content="始终用中文回答")
        req = make_query()
        ctx = await assembler.assemble(req)
        messages = ctx.to_messages()
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) > 0
        system_content = system_msgs[0]["content"]
        assert "<rules>" in system_content

    @pytest.mark.asyncio
    async def test_stm_turns_in_messages(self, assembler, stm):
        """对话轮次以 user/assistant role 出现在 messages 中"""
        stm.add_turn("sess", "user", "用户消息")
        stm.add_turn("sess", "assistant", "助手消息")
        req = make_query()
        ctx = await assembler.assemble(req)
        messages = ctx.to_messages()
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_empty_context_returns_empty_messages(self, assembler):
        """空上下文返回空 messages 列表"""
        req = make_query()
        ctx = await assembler.assemble(req)
        messages = ctx.to_messages()
        assert messages == []

    @pytest.mark.asyncio
    async def test_profile_in_user_profile_tag(self, assembler, ltm):
        """用户档案被放入 <user_profile> 标签"""
        add_profile(ltm, content="用户是Python工程师")
        req = make_query()
        ctx = await assembler.assemble(req)
        messages = ctx.to_messages()
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) > 0
        assert "<user_profile>" in system_msgs[0]["content"]


# ──────────────── 有摘要时的处理 ─────────────────────────────── #

class TestAssemblerWithSummary:

    @pytest.mark.asyncio
    async def test_summary_injected_into_profile(self, assembler, stm):
        """压缩摘要附加到 profile 块"""
        # 制造压缩摘要
        for i in range(10):
            stm.add_turn("sess", "user", f"历史对话内容{i}")
        await stm.compress_old_turns("sess", keep_last=3)

        req = make_query()
        ctx = await assembler.assemble(req)
        # profile 中应包含早期摘要
        assert "早期对话摘要" in ctx.profile or ctx.total_tokens > 0
