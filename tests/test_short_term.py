"""
短期记忆 (ShortTermMemoryManager) 单元测试
覆盖：
  - add_turn 基本写入
  - get_recent_turns 正确返回 & token 裁剪
  - compress_old_turns 压缩 & 摘要保留
  - clear_session 清空
  - 持久化（重建 manager 后数据仍在）
  - 边界：空会话、单轮、大量轮次
"""
import asyncio
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ────────────────────────── 基础 CRUD ─────────────────────────── #

class TestSTMBasic:

    def test_add_single_turn(self, stm):
        """添加单条对话，能正确取回"""
        stm.add_turn("s1", "user", "你好")
        info = stm.get_session_info("s1")
        assert info["turn_count"] == 1
        assert info["total_tokens"] > 0

    def test_add_multiple_turns(self, stm):
        """多条对话顺序正确"""
        messages = ["第一句话", "第二句话", "第三句话"]
        for i, msg in enumerate(messages):
            stm.add_turn("s1", "user" if i % 2 == 0 else "assistant", msg)
        info = stm.get_session_info("s1")
        assert info["turn_count"] == 3

    def test_different_sessions_isolated(self, stm):
        """不同 session 数据互不干扰"""
        stm.add_turn("session_a", "user", "session A 的内容")
        stm.add_turn("session_b", "user", "session B 的内容")
        a = stm.get_session_info("session_a")
        b = stm.get_session_info("session_b")
        assert a["turn_count"] == 1
        assert b["turn_count"] == 1

    def test_empty_session_returns_zero(self, stm):
        """不存在的 session 返回零值，不报错"""
        info = stm.get_session_info("nonexistent")
        assert info["turn_count"] == 0
        assert info["total_tokens"] == 0
        assert info["has_summary"] is False

    def test_clear_session(self, stm):
        """清空后 session 信息归零"""
        stm.add_turn("s1", "user", "要被清除的内容")
        stm.clear_session("s1")
        info = stm.get_session_info("s1")
        assert info["turn_count"] == 0

    def test_clear_nonexistent_session_no_error(self, stm):
        """清空不存在的 session 不报错"""
        stm.clear_session("ghost_session")  # should not raise


# ───────────────────── get_recent_turns ──────────────────────── #

class TestSTMGetRecentTurns:

    @pytest.mark.asyncio
    async def test_returns_all_when_within_limit(self, stm):
        """轮次未超限时全部返回"""
        for i in range(5):
            stm.add_turn("s1", "user", f"消息 {i}")
        turns, summary = await stm.get_recent_turns("s1", max_turns=10, max_tokens=5000)
        assert len(turns) == 5
        assert summary == ""

    @pytest.mark.asyncio
    async def test_respects_max_turns(self, stm):
        """max_turns 限制生效"""
        for i in range(20):
            stm.add_turn("s1", "user", f"消息 {i}")
        turns, _ = await stm.get_recent_turns("s1", max_turns=5, max_tokens=99999)
        assert len(turns) <= 5

    @pytest.mark.asyncio
    async def test_respects_max_tokens(self, stm):
        """超过 max_tokens 时按 token 裁剪"""
        # 添加 10 条，每条约 20 token
        for i in range(10):
            stm.add_turn("s1", "user", "这是一段文字，大约二十个字左右的内容。")
        turns, _ = await stm.get_recent_turns("s1", max_turns=100, max_tokens=50)
        # 50 tokens 最多容纳 2-3 条
        total_tokens = sum(t.token_count for t in turns)
        assert total_tokens <= 60  # 允许少量误差

    @pytest.mark.asyncio
    async def test_returns_latest_turns_when_trimmed(self, stm):
        """token 裁剪时保留最新轮次"""
        contents = [f"第{i}条消息" for i in range(10)]
        for c in contents:
            stm.add_turn("s1", "user", c)
        turns, _ = await stm.get_recent_turns("s1", max_turns=5, max_tokens=9999)
        # 应该是最后 5 条
        returned_contents = [t.content for t in turns]
        assert "第9条消息" in returned_contents

    @pytest.mark.asyncio
    async def test_empty_session_returns_empty(self, stm):
        """空 session 返回空列表"""
        turns, summary = await stm.get_recent_turns("empty_s", max_turns=10, max_tokens=2000)
        assert turns == []
        assert summary == ""

    @pytest.mark.asyncio
    async def test_returns_existing_summary(self, stm):
        """compress 后再 get，应返回摘要"""
        for i in range(10):
            stm.add_turn("s1", "user", f"消息内容{i}")
        await stm.compress_old_turns("s1", keep_last=3)
        _, summary = await stm.get_recent_turns("s1", max_turns=10, max_tokens=9999)
        assert summary != ""


# ─────────────────── compress_old_turns ──────────────────────── #

class TestSTMCompress:

    @pytest.mark.asyncio
    async def test_compress_reduces_turn_count(self, stm):
        """压缩后轮次数量减少"""
        for i in range(12):
            stm.add_turn("s1", "user" if i % 2 == 0 else "assistant", f"内容{i}")
        before = stm.get_session_info("s1")["turn_count"]
        await stm.compress_old_turns("s1", keep_last=4)
        after = stm.get_session_info("s1")["turn_count"]
        assert after == 4
        assert before > after

    @pytest.mark.asyncio
    async def test_compress_generates_summary(self, stm):
        """压缩后有摘要"""
        for i in range(10):
            stm.add_turn("s1", "user", f"这是第{i}轮对话，内容比较重要")
        await stm.compress_old_turns("s1", keep_last=3)
        info = stm.get_session_info("s1")
        assert info["has_summary"] is True

    @pytest.mark.asyncio
    async def test_compress_keep_last_correct(self, stm):
        """keep_last 精确控制保留轮数"""
        for i in range(20):
            stm.add_turn("s1", "user", f"消息{i}")
        await stm.compress_old_turns("s1", keep_last=6)
        info = stm.get_session_info("s1")
        assert info["turn_count"] == 6

    @pytest.mark.asyncio
    async def test_compress_skips_if_few_turns(self, stm):
        """轮次少于 keep_last 时不触发压缩"""
        for i in range(3):
            stm.add_turn("s1", "user", f"消息{i}")
        await stm.compress_old_turns("s1", keep_last=5)  # keep_last > 当前轮次
        info = stm.get_session_info("s1")
        assert info["turn_count"] == 3  # 不变
        assert info["has_summary"] is False

    @pytest.mark.asyncio
    async def test_compress_multiple_times_merges_summary(self, stm):
        """多次压缩，摘要累积"""
        for i in range(20):
            stm.add_turn("s1", "user", f"话题A讨论内容第{i}轮")
        await stm.compress_old_turns("s1", keep_last=5)
        first_summary = stm.get_session_info("s1")

        for i in range(10):
            stm.add_turn("s1", "user", f"话题B新内容{i}")
        await stm.compress_old_turns("s1", keep_last=5)
        second_summary = stm.get_session_info("s1")

        assert second_summary["has_summary"] is True


# ───────────────────── 持久化 ─────────────────────────────────── #

class TestSTMPersistence:

    def test_data_persists_across_manager_rebuild(self, settings):
        """Manager 重建后数据仍然存在"""
        from src.memory.short_term import ShortTermMemoryManager
        m1 = ShortTermMemoryManager(settings)
        m1.add_turn("s1", "user", "持久化测试内容")
        m1.add_turn("s1", "assistant", "助手的回复内容")

        # 新建 Manager，模拟重启
        m2 = ShortTermMemoryManager(settings)
        info = m2.get_session_info("s1")
        assert info["turn_count"] == 2

    def test_clear_also_removes_file(self, settings):
        """clear 后磁盘文件也删除"""
        from src.memory.short_term import ShortTermMemoryManager
        import os
        m = ShortTermMemoryManager(settings)
        m.add_turn("s1", "user", "内容")
        m.clear_session("s1")

        # 重建，应为空
        m2 = ShortTermMemoryManager(settings)
        info = m2.get_session_info("s1")
        assert info["turn_count"] == 0
