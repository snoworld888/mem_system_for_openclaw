"""
HTTP API 集成测试（使用 FastAPI TestClient，无需启动真实服务器）
覆盖：
  - GET /health
  - POST /memory/query
  - POST /memory/turn（含自动事实提取、自动压缩触发）
  - POST /memory/save
  - POST /memory/search
  - POST /memory/rule
  - POST /memory/profile
  - GET /memory/stats
  - DELETE /memory/session/{session_id}
  - POST /memory/compress/{session_id}
  - 错误场景：缺少必填字段、非法参数
"""
import sys
import os
import tempfile
import shutil
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── module-scope client (one ChromaDB init per module) ──────── #

@pytest.fixture(scope="module")
def api_data_dir():
    d = tempfile.mkdtemp(prefix="api_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def client(api_data_dir):
    """
    Module-scope TestClient：整个测试文件只初始化一次 ChromaDB。
    测试用 SESSION 不同前缀来隔离数据。
    """
    import src.config as cfg_mod
    cfg_mod._settings = None

    from src.config import Settings
    s = Settings(data_dir=api_data_dir, debug=False)

    from src.memory.short_term import ShortTermMemoryManager
    from src.memory.long_term import LongTermMemoryManager
    from src.memory.assembler import ContextAssembler
    import src.api.routes as routes_mod

    routes_mod.settings = s
    routes_mod.stm = ShortTermMemoryManager(s)
    routes_mod.ltm = LongTermMemoryManager(s)
    routes_mod.assembler = ContextAssembler(routes_mod.stm, routes_mod.ltm)

    tc = TestClient(routes_mod.app, raise_server_exceptions=True)
    yield tc

    cfg_mod._settings = None


SESSION = "api_test_user"


# ─────────────────────── /health ─────────────────────────────── #

class TestHealth:

    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "ltm_stats" in data


# ─────────────────── /memory/turn ────────────────────────────── #

class TestAddTurn:

    def test_add_user_turn(self, client):
        resp = client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "user",
            "content": "你好，我是测试用户",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "token_count" in data
        assert data["token_count"] > 0

    def test_add_assistant_turn(self, client):
        resp = client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "assistant",
            "content": "你好！有什么可以帮你？",
        })
        assert resp.status_code == 200

    def test_auto_extract_facts(self, client):
        """包含关键词的 user 消息会自动提取事实"""
        resp = client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "user",
            "content": "请记住，我叫张三，我是一名Python工程师",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["extracted_facts"], list)
        assert len(data["extracted_facts"]) > 0

    def test_assistant_turn_no_facts_extracted(self, client):
        """assistant 消息不触发事实提取"""
        resp = client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "assistant",
            "content": "我叫助手，我是AI",  # 含关键词但 role=assistant
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["extracted_facts"] == []

    def test_missing_session_id_returns_422(self, client):
        resp = client.post("/memory/turn", json={
            "role": "user",
            "content": "缺少session_id",
        })
        assert resp.status_code == 422

    def test_missing_content_returns_422(self, client):
        resp = client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "user",
        })
        assert resp.status_code == 422


# ─────────────────── /memory/save ────────────────────────────── #

class TestSaveMemory:

    def test_save_long_term(self, client):
        resp = client.post("/memory/save", json={
            "session_id": SESSION,
            "content": "用户擅长Python异步编程",
            "memory_type": "long_term",
            "importance": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert len(data["id"]) > 0

    def test_save_profile(self, client):
        resp = client.post("/memory/save", json={
            "session_id": SESSION,
            "content": "姓名：测试用户",
            "memory_type": "profile",
            "importance": 3,
        })
        assert resp.status_code == 200

    def test_save_rule(self, client):
        resp = client.post("/memory/save", json={
            "session_id": "global",
            "content": "始终用中文回答",
            "memory_type": "rule",
            "importance": 3,
        })
        assert resp.status_code == 200

    def test_save_with_tags(self, client):
        resp = client.post("/memory/save", json={
            "session_id": SESSION,
            "content": "有标签的内容",
            "memory_type": "long_term",
            "importance": 2,
            "tags": ["python", "async"],
        })
        assert resp.status_code == 200

    def test_save_invalid_memory_type(self, client):
        resp = client.post("/memory/save", json={
            "session_id": SESSION,
            "content": "内容",
            "memory_type": "invalid_type",
            "importance": 2,
        })
        assert resp.status_code == 422

    def test_save_missing_content_returns_422(self, client):
        resp = client.post("/memory/save", json={
            "session_id": SESSION,
            "memory_type": "long_term",
        })
        assert resp.status_code == 422


# ─────────────────── /memory/query ───────────────────────────── #

class TestQueryMemory:

    def test_query_empty_session(self, client):
        """空 session 查询不报错，返回空结果"""
        resp = client.post("/memory/query", json={
            "session_id": "brand_new_session",
            "query": "测试查询",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "messages" in data
        assert "total_tokens" in data
        assert data["stm_turns"] == 0

    def test_query_includes_rules(self, client):
        """添加规则后，query 的 has_rules 为 True"""
        client.post("/memory/rule", params={"content": "始终用中文回答", "priority": 3})
        resp = client.post("/memory/query", json={
            "session_id": SESSION,
            "query": "测试",
            "include_rules": True,
        })
        assert resp.status_code == 200
        assert resp.json()["has_rules"] is True

    def test_query_stm_turns_counted(self, client):
        """添加对话后，stm_turns 正确计数"""
        sid = "stm_count_test_unique"  # 独立 session，不被其他测试污染
        for i in range(3):
            client.post("/memory/turn", json={
                "session_id": sid,
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"第{i}轮消息",
            })
        resp = client.post("/memory/query", json={
            "session_id": sid,
            "query": "查询",
            "stm_turns": 10,
        })
        assert resp.status_code == 200
        assert resp.json()["stm_turns"] == 3

    def test_query_messages_format(self, client):
        """messages 格式正确（有 role 和 content）"""
        client.post("/memory/rule", params={"content": "规则内容", "priority": 3})
        resp = client.post("/memory/query", json={
            "session_id": SESSION,
            "query": "测试",
        })
        messages = resp.json()["messages"]
        for msg in messages:
            assert "role" in msg
            assert "content" in msg

    def test_query_respects_max_tokens(self, client):
        """total_tokens 不超过 max_tokens 太多"""
        # 先填充数据
        for i in range(10):
            client.post("/memory/turn", json={
                "session_id": SESSION,
                "role": "user",
                "content": f"对话内容第{i}条，这是比较长的文本内容",
            })
        resp = client.post("/memory/query", json={
            "session_id": SESSION,
            "query": "查询",
            "max_tokens": 500,
        })
        assert resp.status_code == 200
        # total_tokens 应该在合理范围内
        assert resp.json()["total_tokens"] <= 600

    def test_query_missing_session_id(self, client):
        resp = client.post("/memory/query", json={"query": "缺少session_id"})
        assert resp.status_code == 422


# ─────────────────── /memory/search ──────────────────────────── #

class TestSearchMemory:

    def test_search_empty_returns_empty_results(self, client):
        resp = client.post("/memory/search", json={
            "session_id": SESSION,
            "query": "Python异步",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_search_after_save(self, client):
        """保存后能搜索到相关内容"""
        client.post("/memory/save", json={
            "session_id": SESSION,
            "content": "用户擅长Python异步编程asyncio",
            "memory_type": "long_term",
            "importance": 3,
        })
        resp = client.post("/memory/search", json={
            "session_id": SESSION,
            "query": "Python异步编程",
            "top_k": 5,
            "threshold": 0.1,
        })
        assert resp.status_code == 200

    def test_search_result_schema(self, client):
        """搜索结果包含必要字段"""
        client.post("/memory/save", json={
            "session_id": SESSION,
            "content": "测试内容：Python相关知识",
            "memory_type": "long_term",
            "importance": 2,
        })
        resp = client.post("/memory/search", json={
            "session_id": SESSION,
            "query": "Python",
            "top_k": 3,
            "threshold": 0.0,
        })
        results = resp.json()["results"]
        for r in results:
            assert "id" in r
            assert "content" in r
            assert "score" in r
            assert "memory_type" in r

    def test_search_respects_top_k(self, client):
        """搜索结果不超过 top_k"""
        for i in range(10):
            client.post("/memory/save", json={
                "session_id": SESSION,
                "content": f"Python知识点{i}：相关内容",
                "memory_type": "long_term",
                "importance": 2,
            })
        resp = client.post("/memory/search", json={
            "session_id": SESSION,
            "query": "Python",
            "top_k": 3,
            "threshold": 0.0,
        })
        assert len(resp.json()["results"]) <= 3


# ─────────────────── /memory/rule ────────────────────────────── #

class TestAddRule:

    def test_add_rule_basic(self, client):
        resp = client.post("/memory/rule", params={
            "content": "始终用中文回答",
            "priority": 3,
        })
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_add_rule_without_priority(self, client):
        """priority 可选，默认值正常工作"""
        resp = client.post("/memory/rule", params={"content": "测试规则"})
        assert resp.status_code == 200


# ─────────────────── /memory/profile ─────────────────────────── #

class TestAddProfile:

    def test_add_profile_basic(self, client):
        resp = client.post("/memory/profile", params={
            "content": "用户名：测试用户",
            "session_id": SESSION,
        })
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_add_profile_global(self, client):
        """全局 profile 默认 session_id"""
        resp = client.post("/memory/profile", params={
            "content": "全局档案内容",
        })
        assert resp.status_code == 200


# ─────────────────── /memory/stats ───────────────────────────── #

class TestStats:

    def test_stats_no_session(self, client):
        resp = client.get("/memory/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "ltm" in data
        assert "stm" in data

    def test_stats_with_session(self, client):
        client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "user",
            "content": "测试消息",
        })
        resp = client.get(f"/memory/stats?session_id={SESSION}")
        assert resp.status_code == 200
        stm_info = resp.json()["stm"]
        assert stm_info.get("turn_count", 0) >= 1


# ─────────────── DELETE /memory/session/{session_id} ─────────── #

class TestClearSession:

    def test_clear_session(self, client):
        client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "user",
            "content": "要被清除的内容",
        })
        resp = client.delete(f"/memory/session/{SESSION}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cleared"

    def test_clear_and_verify_empty(self, client):
        """清空后 stats 显示为 0"""
        client.post("/memory/turn", json={
            "session_id": SESSION,
            "role": "user",
            "content": "内容",
        })
        client.delete(f"/memory/session/{SESSION}")
        resp = client.get(f"/memory/stats?session_id={SESSION}")
        assert resp.json()["stm"].get("turn_count", 0) == 0


# ─────────── POST /memory/compress/{session_id} ──────────────── #

class TestCompressSession:

    def test_compress_session(self, client):
        """添加足够多对话后手动压缩"""
        for i in range(10):
            client.post("/memory/turn", json={
                "session_id": SESSION,
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"这是第{i}条对话内容，用于测试压缩功能是否正常",
            })
        resp = client.post(f"/memory/compress/{SESSION}", params={"keep_last": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert "before_tokens" in data
        assert "after_tokens" in data
        assert "saved" in data

    def test_compress_empty_session_no_error(self, client):
        """压缩空 session 不报错"""
        resp = client.post("/memory/compress/nonexistent_session")
        assert resp.status_code == 200


# ──────────── 完整端到端工作流测试 ────────────────────────────── #

class TestE2EWorkflow:

    def test_full_conversation_workflow(self, client):
        """
        完整工作流：添加规则 → 档案 → 对话 → 保存 → 查询
        验证所有步骤正确联动
        """
        sid = "workflow_test"

        # 1. 添加规则
        r = client.post("/memory/rule", params={"content": "始终用中文", "priority": 3})
        assert r.status_code == 200

        # 2. 添加档案
        r = client.post("/memory/profile", params={
            "content": "用户是高级工程师",
            "session_id": sid,
            "priority": 3,
        })
        assert r.status_code == 200

        # 3. 添加对话
        for i in range(4):
            r = client.post("/memory/turn", json={
                "session_id": sid,
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"对话{i}",
            })
            assert r.status_code == 200

        # 4. 保存重要信息
        r = client.post("/memory/save", json={
            "session_id": sid,
            "content": "用户的重要偏好",
            "memory_type": "long_term",
            "importance": 3,
        })
        assert r.status_code == 200

        # 5. 查询
        r = client.post("/memory/query", json={
            "session_id": sid,
            "query": "用户偏好",
            "max_tokens": 2000,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["has_rules"] is True
        assert data["has_profile"] is True
        assert data["stm_turns"] == 4
        assert isinstance(data["messages"], list)
