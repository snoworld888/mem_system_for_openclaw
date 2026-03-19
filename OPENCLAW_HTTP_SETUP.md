# OpenClaw 接入指南（HTTP REST 方式）

## 快速开始

既然 OpenClaw 不支持 MCP，我们改用 **HTTP REST API** 方式。

### 1. 启动记忆服务（HTTP 模式）

```bash
cd c:\07code\mem_server
python main.py
```

服务启动后监听：`http://127.0.0.1:7000`

### 2. 在 OpenClaw 中添加自定义工具

OpenClaw 通常支持通过 HTTP API 集成外部工具。具体步骤：

1. 打开 OpenClaw 设置
2. 找到 **"Tools"** 或 **"Integrations"** 或 **"Custom API"**
3. 添加新的 HTTP 端点或自定义工具

### 3. 配置记忆服务的主要端点

| 功能 | 方法 | URL | 说明 |
|------|------|-----|------|
| 查询上下文 | POST | `http://127.0.0.1:7000/memory/query` | 组装所有上下文 |
| 添加对话 | POST | `http://127.0.0.1:7000/memory/turn` | 记录每轮对话 |
| 保存记忆 | POST | `http://127.0.0.1:7000/memory/save` | 保存到长期记忆 |
| 搜索记忆 | POST | `http://127.0.0.1:7000/memory/search` | 语义搜索 |
| 添加规则 | POST | `http://127.0.0.1:7000/memory/rule` | 添加行为准则 |
| 添加用户信息 | POST | `http://127.0.0.1:7000/memory/profile` | 添加用户背景 |
| 健康检查 | GET | `http://127.0.0.1:7000/health` | 服务状态 |

### 4. 测试 API

打开浏览器，访问 Swagger 文档：
```
http://127.0.0.1:7000/docs
```

可以直接在网页上测试所有 API。

---

## 工作流示例

### 示例 1：查询上下文（最常用）

**请求：**
```bash
curl -X POST http://127.0.0.1:7000/memory/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "query": "我想要什么",
    "max_tokens": 2000
  }'
```

**响应：**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "<rules>...\n<user_profile>...\n<relevant_memories>..."
    },
    {
      "role": "user",
      "content": "..."
    }
  ],
  "total_tokens": 456
}
```

### 示例 2：添加对话轮次

**请求：**
```bash
curl -X POST http://127.0.0.1:7000/memory/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "role": "user",
    "content": "我叫张三，我是工程师"
  }'
```

**响应：**
```json
{
  "token_count": 12,
  "extracted_facts": ["我叫张三", "我是工程师"],
  "auto_compressed": false
}
```

### 示例 3：保存到长期记忆

**请求：**
```bash
curl -X POST http://127.0.0.1:7000/memory/save \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "content": "用户喜欢Python和机器学习",
    "importance": 3,
    "tags": ["preference", "tech"]
  }'
```

---

## 在 OpenClaw 中集成

### 方式 A：如果 OpenClaw 支持自定义插件

将以下 Python 代码保存为插件，让 OpenClaw 加载：

```python
# memory_plugin.py
import requests
import json

class MemoryPlugin:
    def __init__(self):
        self.base_url = "http://127.0.0.1:7000"
    
    def query_memory(self, session_id: str, query: str, max_tokens: int = 2000):
        """查询记忆上下文"""
        resp = requests.post(
            f"{self.base_url}/memory/query",
            json={
                "session_id": session_id,
                "query": query,
                "max_tokens": max_tokens
            }
        )
        return resp.json()
    
    def add_turn(self, session_id: str, role: str, content: str):
        """添加对话"""
        resp = requests.post(
            f"{self.base_url}/memory/turn",
            json={
                "session_id": session_id,
                "role": role,
                "content": content
            }
        )
        return resp.json()
    
    def save_memory(self, session_id: str, content: str, importance: int = 2):
        """保存记忆"""
        resp = requests.post(
            f"{self.base_url}/memory/save",
            json={
                "session_id": session_id,
                "content": content,
                "importance": importance
            }
        )
        return resp.json()
```

### 方式 B：使用 Python 脚本直接调用

如果 OpenClaw 支持执行 Python 脚本，可以这样：

```python
import requests

session = "openclaw_user_001"

# 1. 查询上下文
ctx = requests.post(
    "http://127.0.0.1:7000/memory/query",
    json={"session_id": session, "query": "今天天气如何"}
).json()

messages = ctx["messages"]  # 直接用于 LLM

# 2. 记录用户输入
requests.post(
    "http://127.0.0.1:7000/memory/turn",
    json={"session_id": session, "role": "user", "content": "天气不错"}
)

# 3. 记录 AI 回复
requests.post(
    "http://127.0.0.1:7000/memory/turn",
    json={"session_id": session, "role": "assistant", "content": "是的，今天阳光明媚"}
)

# 4. 如果用户说了重要信息，保存
requests.post(
    "http://127.0.0.1:7000/memory/save",
    json={
        "session_id": session,
        "content": "用户喜欢天气好的日子",
        "importance": 2
    }
)
```

---

## 常见问题

**Q: 服务会一直运行吗？**
A: 是的，`python main.py` 会持续运行。你可以：
   - 后台运行：`start python main.py`
   - 或创建 Windows 定时任务随机启动

**Q: 多个 OpenClaw 实例能共用一个服务吗？**
A: 可以。只要地址相同（127.0.0.1:7000），所有实例都能访问。

**Q: 如何确保数据安全？**
A: 目前服务没有认证。如果需要：
   - 只在本机运行
   - 或在 nginx 前面加认证层
   - 或用防火墙限制访问

**Q: Token 预算是怎么工作的？**
A: 每次 `query_memory` 时，会自动按优先级分配：
   - 规则：≤300 tokens
   - 用户信息：≤200 tokens
   - 长期记忆：≤600 tokens
   - 短期对话：剩余（自动压缩早期轮次）

---

## 建议的集成方式

**最简单：OpenClaw 的系统提示词中加入：**

```
你可以调用以下 HTTP 工具：
1. POST http://127.0.0.1:7000/memory/query - 查询记忆上下文
2. POST http://127.0.0.1:7000/memory/turn - 记录对话
3. POST http://127.0.0.1:7000/memory/save - 保存重要信息

工作流：
- 每次对话开始：调用 query_memory 获取上下文
- 每轮结束：调用 add_turn 记录对话
- 用户说重要信息时：调用 save_memory 保存
```

然后让 AI 自己决定何时调用这些端点。

---

## 下一步

1. **启动服务**：
   ```bash
   cd c:\07code\mem_server
   python main.py
   ```

2. **验证服务**：
   ```bash
   curl http://127.0.0.1:7000/health
   ```

3. **查看 API 文档**：
   ```
   http://127.0.0.1:7000/docs
   ```

4. **根据 OpenClaw 的功能，选择集成方式**

有其他问题吗？
