# MEMORY.md — EHAP-V4.0 / mem_server 项目长期记忆

## 项目概述
- 路径: `c:\07code\mem_server`
- 四层记忆系统: Rules > Profile > Long Term Memory > Short Term Memory
- 技术栈: Python + FastAPI + ChromaDB + pytest

## 测试状态（2026-03-24 最新）
**全部通过: 117 passed, 0 failed**
| 模块 | 测试数 | 文件 |
|------|--------|------|
| Compressor & TokenCounter | 24 | tests/test_compressor.py |
| Short Term Memory (STM) | 19 | tests/test_short_term.py |
| Long Term Memory (LTM) | 21 | tests/test_long_term.py |
| Context Assembler | 19 | tests/test_assembler.py |
| HTTP API Integration | 34 | tests/test_api_integration.py |

## 关键修复记录
- `short_term.py`: `get_recent_turns(max_turns=0)` 时 Python `-0 == 0` bug，已修复（返回空列表）
- `assembler.py`: `stm_turns <= 0` 时提前跳过 STM 查询
- Windows pytest tmpdir bug: 在 `pytest.ini` 中使用 `-p no:tmpdir` 规避
- ChromaDB 初始化慢: 使用 `scope="module"` fixture 共享实例

## 重要配置
- 服务端口: 7000（曾经是 8765）
- pytest.ini: `addopts = -v --tb=short -p no:tmpdir`
- conftest.py: function-scope (独立测试) + module-scope (LTM共享)

## 项目文件
- `skill/SKILL.md` 等 OpenClaw skill 文档已更新到 7000 端口
- `main.py` 支持 `--port` 和 `--host` 命令行参数
