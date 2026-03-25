"""
pytest 共享 Fixture
"""
import sys
import os
import tempfile
import shutil
import pytest
import pytest_asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="function")
def tmp_data_dir():
    """每个测试用独立的临时数据目录，测试完自动清理"""
    d = tempfile.mkdtemp(prefix="mem_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _make_settings(data_dir):
    """Helper: 创建使用指定目录的 Settings（绕过全局缓存）"""
    import src.config as cfg_mod
    cfg_mod._settings = None
    from src.config import Settings
    s = Settings(data_dir=data_dir, debug=False)
    os.makedirs(s.data_dir, exist_ok=True)
    return s


# ── function-scope (每个测试独立) ──────────────────────────────── #

@pytest.fixture(scope="function")
def settings(tmp_data_dir):
    s = _make_settings(tmp_data_dir)
    yield s
    import src.config as cfg_mod
    cfg_mod._settings = None


@pytest.fixture(scope="function")
def stm(settings):
    from src.memory.short_term import ShortTermMemoryManager
    return ShortTermMemoryManager(settings)


@pytest.fixture(scope="function")
def ltm(settings):
    from src.memory.long_term import LongTermMemoryManager
    return LongTermMemoryManager(settings)


@pytest.fixture(scope="function")
def assembler(stm, ltm):
    from src.memory.assembler import ContextAssembler
    return ContextAssembler(stm, ltm)


# ── module-scope (LTM 测试用：初始化 ChromaDB 很慢) ──────────────── #

@pytest.fixture(scope="module")
def module_tmp_dir():
    d = tempfile.mkdtemp(prefix="mem_module_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture(scope="module")
def module_ltm(module_tmp_dir):
    """module 级别的 LTM，避免每个测试都重初始化 ChromaDB"""
    import src.config as cfg_mod
    cfg_mod._settings = None
    from src.config import Settings
    from src.memory.long_term import LongTermMemoryManager
    s = Settings(data_dir=module_tmp_dir, debug=False)
    os.makedirs(s.data_dir, exist_ok=True)
    return LongTermMemoryManager(s)

