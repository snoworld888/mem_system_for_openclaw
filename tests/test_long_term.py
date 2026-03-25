"""
Long Term Memory (LongTermMemoryManager) Unit Tests
Uses module_ltm fixture to share one ChromaDB instance per module (init ~15s).
Each test class uses a unique session_id prefix for isolation.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory.models import MemoryItem, MemoryType, ImportanceLevel


def make_item(session_id="ltm_s1", memory_type=MemoryType.LONG_TERM,
              content="test content", importance=ImportanceLevel.MEDIUM, tags=None):
    return MemoryItem(
        session_id=session_id,
        memory_type=memory_type,
        content=content,
        importance=importance,
        tags=tags or [],
    )


# ─────────────────── add_memory / get_all ────────────────────── #

class TestLTMAddAndGet:

    def test_add_and_retrieve_long_term(self, module_ltm):
        item = make_item(session_id="add_ltm", content="Python is an interpreted language")
        module_ltm.add_memory(item)
        results = module_ltm.get_all(MemoryType.LONG_TERM, session_id="add_ltm")
        contents = [r.content for r in results]
        assert "Python is an interpreted language" in contents

    def test_add_and_retrieve_profile(self, module_ltm):
        item = make_item(session_id="add_profile", memory_type=MemoryType.PROFILE,
                         content="username: Alice")
        module_ltm.add_memory(item)
        results = module_ltm.get_all(MemoryType.PROFILE, session_id="add_profile")
        assert any("Alice" in r.content for r in results)

    def test_add_and_retrieve_rule(self, module_ltm):
        item = make_item(session_id="global",
                         memory_type=MemoryType.RULE,
                         content="always reply in Chinese",
                         importance=ImportanceLevel.HIGH)
        module_ltm.add_memory(item)
        results = module_ltm.get_all(MemoryType.RULE)
        assert any("Chinese" in r.content for r in results)

    def test_add_multiple_items(self, module_ltm):
        for i in range(5):
            module_ltm.add_memory(make_item(session_id="add_multi",
                                            content=f"fact {i}: python knowledge"))
        results = module_ltm.get_all(MemoryType.LONG_TERM, session_id="add_multi")
        assert len(results) >= 5

    def test_add_returns_id(self, module_ltm):
        item = make_item(session_id="add_id")
        mem_id = module_ltm.add_memory(item)
        assert isinstance(mem_id, str)
        assert len(mem_id) > 0

    def test_get_all_empty_session_returns_list(self, module_ltm):
        results = module_ltm.get_all(MemoryType.LONG_TERM, session_id="totally_empty_session_xyz")
        assert results == []

    def test_session_filter_in_get_all(self, module_ltm):
        module_ltm.add_memory(make_item(session_id="filter_alice", content="Alice content"))
        module_ltm.add_memory(make_item(session_id="filter_bob",   content="Bob content"))
        alice_results = module_ltm.get_all(MemoryType.LONG_TERM, session_id="filter_alice")
        for r in alice_results:
            assert r.session_id == "filter_alice"


# ───────────────────────── search ────────────────────────────── #

class TestLTMSearch:

    def test_search_returns_results(self, module_ltm):
        module_ltm.add_memory(make_item(session_id="search_s1",
                                        content="Python async programming uses asyncio"))
        module_ltm.add_memory(make_item(session_id="search_s1",
                                        content="async/await is a Python 3.5+ feature"))
        results = module_ltm.search(
            query="Python async",
            memory_type=MemoryType.LONG_TERM,
            session_id="search_s1",
            top_k=5,
            threshold=0.1,
        )
        assert len(results) > 0
        for item, score in results:
            assert 0.0 <= score <= 1.0
            assert isinstance(item, MemoryItem)

    def test_search_respects_top_k(self, module_ltm):
        for i in range(8):
            module_ltm.add_memory(make_item(session_id="search_topk",
                                            content=f"Python knowledge point {i}"))
        results = module_ltm.search(
            query="Python",
            memory_type=MemoryType.LONG_TERM,
            session_id="search_topk",
            top_k=3,
            threshold=0.0,
        )
        assert len(results) <= 3

    def test_search_empty_session_returns_empty(self, module_ltm):
        results = module_ltm.search(
            query="anything",
            memory_type=MemoryType.LONG_TERM,
            session_id="absolutely_empty_session_abc123",
            top_k=5,
            threshold=0.1,
        )
        assert results == []

    def test_search_session_isolation(self, module_ltm):
        module_ltm.add_memory(make_item(session_id="iso_user_a", content="user_a Python skills"))
        module_ltm.add_memory(make_item(session_id="iso_user_b", content="user_b Python skills"))
        results = module_ltm.search(
            query="Python skills",
            memory_type=MemoryType.LONG_TERM,
            session_id="iso_user_a",
            top_k=5,
            threshold=0.0,
        )
        for item, _ in results:
            assert item.session_id == "iso_user_a"

    def test_search_high_threshold_no_crash(self, module_ltm):
        module_ltm.add_memory(make_item(session_id="thresh_s", content="unrelated ABC123"))
        results = module_ltm.search(
            query="XYZXYZXYZ",
            memory_type=MemoryType.LONG_TERM,
            session_id="thresh_s",
            top_k=5,
            threshold=0.99,
        )
        assert isinstance(results, list)

    def test_search_results_sorted_by_score(self, module_ltm):
        module_ltm.add_memory(make_item(session_id="sort_s",
                                        content="Python language features: simple and readable"))
        module_ltm.add_memory(make_item(session_id="sort_s",
                                        content="Java is another programming language"))
        module_ltm.add_memory(make_item(session_id="sort_s",
                                        content="Python asyncio is very powerful for async tasks"))
        results = module_ltm.search(
            query="Python async",
            memory_type=MemoryType.LONG_TERM,
            session_id="sort_s",
            top_k=3,
            threshold=0.0,
        )
        if len(results) >= 2:
            scores = [score for _, score in results]
            assert scores == sorted(scores, reverse=True)


# ───────────────────── update_access / delete ─────────────────── #

class TestLTMAccessAndDelete:

    def test_update_access_does_not_raise(self, module_ltm):
        item = make_item(session_id="access_s")
        module_ltm.add_memory(item)
        module_ltm.update_access(MemoryType.LONG_TERM, item.id)  # should not raise

    def test_delete_memory(self, module_ltm):
        item = make_item(session_id="del_s", content="content to be deleted")
        module_ltm.add_memory(item)
        before = module_ltm.get_all(MemoryType.LONG_TERM, session_id="del_s")
        assert any(r.content == "content to be deleted" for r in before)

        module_ltm.delete_memory(MemoryType.LONG_TERM, item.id)
        after = module_ltm.get_all(MemoryType.LONG_TERM, session_id="del_s")
        assert all(r.content != "content to be deleted" for r in after)

    def test_delete_nonexistent_no_error(self, module_ltm):
        module_ltm.delete_memory(MemoryType.LONG_TERM, "nonexistent-id-99999")


# ───────────────────── get_stats ─────────────────────────────── #

class TestLTMStats:

    def test_stats_returns_dict(self, module_ltm):
        stats = module_ltm.get_stats()
        assert isinstance(stats, dict)

    def test_stats_has_memory_type_keys(self, module_ltm):
        """stats 应包含 long_term / profile / rule 等 key"""
        module_ltm.add_memory(make_item(session_id="stats_s"))
        stats = module_ltm.get_stats()
        # get_stats 返回 {memory_type: count}，至少有一个 key
        assert len(stats) > 0

    def test_stats_long_term_count_increases(self, module_ltm):
        """添加 long_term 记忆后，long_term 计数增加"""
        before = module_ltm.get_stats().get("long_term", 0)
        module_ltm.add_memory(make_item(session_id="stats_grow2", content="count test item"))
        after = module_ltm.get_stats().get("long_term", 0)
        assert after >= before + 1


# ────────────── importance levels & tags ─────────────────────── #

class TestLTMImportanceAndTags:

    def test_all_importance_levels_stored(self, module_ltm):
        for level in [ImportanceLevel.LOW, ImportanceLevel.MEDIUM,
                      ImportanceLevel.HIGH, ImportanceLevel.CRITICAL]:
            item = make_item(session_id="imp_s",
                             content=f"importance {level.name} content",
                             importance=level)
            module_ltm.add_memory(item)
        results = module_ltm.get_all(MemoryType.LONG_TERM, session_id="imp_s")
        assert len(results) >= 4

    def test_tags_stored_correctly(self, module_ltm):
        item = make_item(session_id="tag_s", content="tagged content",
                         tags=["python", "async"])
        module_ltm.add_memory(item)
        results = module_ltm.get_all(MemoryType.LONG_TERM, session_id="tag_s")
        tagged = [r for r in results if "python" in r.tags]
        assert len(tagged) >= 1
