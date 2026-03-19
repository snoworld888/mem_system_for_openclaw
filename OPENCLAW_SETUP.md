# OpenClaw 接入指南

## 问题诊断

如果遇到错误：`Unrecognized key: "***"`，说明 OpenClaw 不认识配置中的某些字段。

## 解决方案

根据你的 OpenClaw 版本，选择对应的配置方式：

### 方案 A：OpenClaw 2026.2+ （推荐）

OpenClaw 2026.2+ 可能有**独立的 MCP 配置目录**。

1. 打开 OpenClaw 设置 → Integrations / Tools / MCP Servers
2. 寻找"Add MCP Server"或"Import MCP Config"选项
3. 选择本项目的 `mcp_servers.json` 文件或手动输入：

```json
{
  "memory": {
    "command": "python",
    "args": ["main.py", "--mcp"],
    "cwd": "c:/07code/mem_server"
  }
}
```

### 方案 B：OpenClaw CLI 方式

如果 OpenClaw 支持命令行配置：

```bash
openclaw mcp add memory --command python --args "main.py --mcp" --cwd "c:/07code/mem_server"
```

### 方案 C：系统环境变量方式

某些 OpenClaw 版本支持环境变量配置 MCP 服务器：

```bash
# 在系统环境变量中添加
OPENCLAW_MCP_MEMORY_COMMAND=python
OPENCLAW_MCP_MEMORY_ARGS=main.py --mcp
OPENCLAW_MCP_MEMORY_CWD=c:/07code/mem_server
```

## 验证配置是否成功

1. **重启 OpenClaw**
2. 在 Agent 的系统提示词中加入：
   ```
   使用 query_memory 工具查询记忆上下文，使用 add_turn 记录对话。
   ```
3. 在对话中尝试调用 memory 的工具
4. 如果能看到 9 个工具列表，说明接入成功

## 常见错误

| 错误 | 原因 | 解决 |
|------|------|------|
| `Unrecognized key` | MCP 配置格式不对 | 检查 key 名称（`mcp` vs `mcpServers` vs `mcpServer`） |
| `Command not found` | Python 路径错误 | 使用完整路径：`c:/python/python.exe` 或在 PATH 中 |
| `Module not found` | 项目路径错误 | 确认 `c:/07code/mem_server` 存在 |
| `Connection refused` | 端口被占用 | 改用 `--mcp` stdio 模式（不占用端口） |

## 调试技巧

1. **单独测试服务**：
   ```bash
   cd c:\07code\mem_server
   python main.py --mcp
   ```
   看是否有错误输出

2. **检查日志**：OpenClaw 通常在以下位置有日志
   - Windows: `%APPDATA%\openclaw\logs\`
   - Linux/Mac: `~/.openclaw/logs/`

3. **简化测试**：先用 HTTP 模式验证服务正常
   ```bash
   python main.py
   # 打开 http://127.0.0.1:7000/health
   ```

## 不确定的地方

如果还是无法接入，请提供：
1. OpenClaw 版本号
2. 完整的错误日志
3. 你尝试的配置内容
