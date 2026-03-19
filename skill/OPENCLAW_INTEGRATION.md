# OpenClaw 记忆服务集成指南

本文档说明如何在 OpenClaw 中集成并使用记忆服务。

---

## 快速开始

### 1. 启动记忆服务

```bash
cd c:\07code\mem_server
python main.py
```

服务将在 `http://127.0.0.1:7000` 上运行。

### 2. 在 OpenClaw 中调用

#### 方式 A：通过系统提示词（最简单）

在 OpenClaw 的系统提示词中添加：

```
【记忆管理】
你有一个记忆服务可以帮助你保持长期上下文。

对话前流程：
1. 调用记忆查询：GET/POST http://127.0.0.1:7000/memory/query
   请求体：{
     "session_id": "{{user_id}}",
     "user_query": "{{current_message}}"
   }
2. 从响应中提取 messages 字段
3. 将这些消息添加到你的上下文中

对话后流程：
1. 调用保存对话：POST http://127.0.0.1:7000/memory/turn
   请求体：{
     "session_id": "{{user_id}}",
     "user_message": "{{user_input}}",
     "assistant_message": "{{your_response}}"
   }
2. 如果用户说了重要信息，也可调用保存接口

【关键提示】
- 始终优先遵守返回的 "rules" 字段中的准则
- 用户的背景信息在 "profile" 字段中
- 相关的历史记忆在 "long_term_relevant" 字段中
```

#### 方式 B：使用集成脚本（推荐用于自动化）

如果 OpenClaw 支持自定义脚本/插件，可以使用：

```python
# 在 OpenClaw 的脚本中导入
import sys
sys.path.append('c:/07code/mem_server/skill/scripts')

from memory_client import MemoryClient

# 初始化
client = MemoryClient("http://127.0.0.1:7000")

# 查询记忆
ctx = client.query_memory(
    session_id="user_123",
    user_query="用户当前消息"
)

# 使用返回的 messages
for msg in ctx.messages:
    # 添加到 LLM 上下文
    pass

# 记录对话
client.add_turn(
    session_id="user_123",
    user_message="用户说的话",
    assistant_message="你的回应"
)
```

#### 方式 C：使用命令行工具

```bash
# 查询上下文
python skill/scripts/openclaw_integration.py query "user_123" "我需要什么帮助？"

# 记录对话
python skill/scripts/openclaw_integration.py turn "user_123" "用户消息" "AI回应"

# 保存重要信息
python skill/scripts/openclaw_integration.py save "user_123" long_term "用户信息"

# 查看统计
python skill/scripts/openclaw_integration.py stats "user_123"
```

---

## 集成场景示例

### 场景 1：始终带上用户背景

**目标**：每次回复时，AI 都知道用户的背景信息

**步骤**：

```javascript
// OpenClaw 系统提示词中的伪代码
对话前：
  ctx = http.post("http://127.0.0.1:7000/memory/query", {
    session_id: user.id,
    user_query: message
  })
  
  // 将规则和用户档案注入到你的上下文中
  system_context = ctx.rules + "\n" + ctx.profile + "\n" + ctx.short_term
```

### 场景 2：智能记忆关键信息

**目标**：用户说了重要信息时，自动保存到长期记忆

**步骤**：

```
在你的回复中，如果检测到用户透露了以下信息，立即调用保存接口：
- 个人偏好（"我喜欢..."、"我擅长..."）
- 背景信息（"我是..."、"我在...工作"）
- 任务需求（"我想..."、"我需要..."）
- 约束条件（"请不要..."、"我不能..."）

调用格式：
POST http://127.0.0.1:7000/memory/save
{
  "session_id": "{{user_id}}",
  "content": "检测到的重要信息",
  "memory_type": "long_term",
  "importance": "high"
}
```

### 场景 3：定期总结长对话

**目标**：长对话自动压缩，保持 Token 效率

**步骤**：

```
如果检测到对话已进行超过20轮，调用统计接口：
GET http://127.0.0.1:7000/memory/stats?session_id={{user_id}}

如果 short_term_tokens 超过 1500，记忆服务会自动压缩。
你无需手动干预。
```

---

## API 速查表

### 最常用的 3 个接口

#### 1. 查询上下文（对话前调用）⭐

```bash
POST http://127.0.0.1:7000/memory/query
Content-Type: application/json

{
  "session_id": "user_123",
  "user_query": "用户的问题",
  "max_tokens": 2000
}
```

**返回示例**：
```json
{
  "session_id": "user_123",
  "rules": "- 遵守隐私\n- 准确性第一",
  "profile": "用户名：张三\n职位：工程师",
  "short_term": "[Turn 1] User: 你好\nAssistant: 你好！",
  "long_term_relevant": "[score=0.92] 用户擅长Python",
  "total_tokens": 450,
  "messages": [
    {"role": "system", "content": "【准则】..."},
    {"role": "system", "content": "【用户档案】..."},
    {"role": "user", "content": "【对话历史】..."}
  ]
}
```

#### 2. 记录对话（对话后调用）

```bash
POST http://127.0.0.1:7000/memory/turn
Content-Type: application/json

{
  "session_id": "user_123",
  "user_message": "用户说的话",
  "assistant_message": "AI的回应",
  "important": false
}
```

#### 3. 保存重要信息

```bash
POST http://127.0.0.1:7000/memory/save
Content-Type: application/json

{
  "session_id": "user_123",
  "content": "要保存的内容",
  "memory_type": "long_term",
  "importance": "high"
}
```

### 其他接口

```bash
# 语义搜索
POST http://127.0.0.1:7000/memory/search
{ "session_id": "user_123", "query": "...", "top_k": 3 }

# 添加用户档案
POST http://127.0.0.1:7000/memory/profile
{ "session_id": "user_123", "content": "...", "action": "add" }

# 添加规则
POST http://127.0.0.1:7000/memory/rule
{ "session_id": "user_123", "content": "...", "importance": "high" }

# 查看统计
GET http://127.0.0.1:7000/memory/stats?session_id=user_123

# 清空会话
POST http://127.0.0.1:7000/memory/clear
{ "session_id": "user_123" }

# 健康检查
GET http://127.0.0.1:7000/health
```

---

## 与 OpenClaw 的协议

### 上下文注入协议

当 `/memory/query` 返回时，`messages` 字段包含了一个可直接用于 LLM 的消息数组：

```json
{
  "messages": [
    {
      "role": "system",
      "content": "【行为准则】\n- 遵守隐私保护\n- 准确性第一"
    },
    {
      "role": "system",
      "content": "【用户档案】\n姓名：张三\n职位：Python工程师"
    },
    {
      "role": "user",
      "content": "【最近对话历史】\n..."
    }
  ]
}
```

**使用方式**：
1. 调用 `/memory/query`
2. 将返回的 `messages` 数组添加到你的消息列表中
3. 继续添加当前用户消息
4. 传给 LLM

### 举例

```python
# 调用记忆服务
memory_ctx = requests.post(
    "http://127.0.0.1:7000/memory/query",
    json={"session_id": "user_123", "user_query": "..."}
).json()

# 构建最终消息列表
messages = memory_ctx["messages"]  # 获取背景信息
messages.append({"role": "user", "content": current_user_input})

# 传给 LLM
response = llm.chat(messages)

# 记录对话
requests.post(
    "http://127.0.0.1:7000/memory/turn",
    json={
        "session_id": "user_123",
        "user_message": current_user_input,
        "assistant_message": response
    }
)
```

---

## 故障排查

### 问题：`Connection refused: http://127.0.0.1:7000`

**原因**：记忆服务未启动

**解决**：
```bash
cd c:\07code\mem_server
python main.py
```

### 问题：记忆未被保存

**可能原因**：
1. 没有调用 `/memory/turn` 记录对话
2. 没有调用 `/memory/save` 显式保存

**解决**：
- 对话后一定要调用 `/memory/turn`
- 重要信息要显式调用 `/memory/save`

### 问题：Token 消耗仍然很多

**原因**：
- 短期记忆积累过多
- 长期记忆检索不够精准

**解决**：
1. 定期检查统计：`GET /memory/stats`
2. 必要时清空旧会话：`POST /memory/clear`
3. 调整 token 预算：修改 `.env` 配置

---

## 配置调优

### 减少 Token 消耗

在 `.env` 中调整：

```bash
# 降低返回上限
DEFAULT_MAX_TOKENS=1200

# 降低长期记忆预算
ASSEMBLY_LTM_TOKENS=400

# 提高压缩触发阈值
STM_MAX_TOKENS=1000
```

### 提高记忆精度

```bash
# 使用更好的嵌入模型
EMBEDDING_MODEL=sentence-transformers/multilingual-e5-large

# 降低检索阈值（更敏感）
# 修改 assembler.py 中的 threshold=0.1
```

---

## 性能参考

| 操作 | 延迟 | 消耗 |
|------|------|------|
| 查询上下文 | 50-200ms | 30-100 tokens |
| 记录对话 | 10-50ms | - |
| 保存信息 | 50-100ms | - |
| 搜索（向量） | 100-500ms | - |
| 搜索（TF-IDF） | 10-50ms | - |

---

## 最佳实践

1. **始终调用 `/memory/query`**
   - 对话前调用，获取用户背景
   - 这是最有效的 Token 节省方式

2. **关键时刻调用 `/memory/save`**
   - 用户透露偏好时
   - 用户说出关键信息时
   - 但不要过度保存（会增加搜索时间）

3. **定期清理**
   - 测试时经常清空：`POST /memory/clear`
   - 生产环境定期备份 `./data` 目录

4. **监控统计**
   - 每小时检查 `GET /memory/stats`
   - 及时发现和处理问题

---

## 高级用法

### 自定义集成

如果 OpenClaw 支持自定义脚本，可以修改 `skill/scripts/memory_client.py` 来添加自定义逻辑。

### 扩展 API

如需添加新接口，修改 `src/api/routes.py` 并重启服务。

### 数据导出

记忆数据存储在 `./data/chromadb/` 中，可以备份或迁移：

```bash
# 备份
robocopy .\data\chromadb\ .\backup\chromadb\ /E

# 从备份恢复
robocopy .\backup\chromadb\ .\data\chromadb\ /E
```

---

## 需要帮助？

- 查看完整文档：`SKILL.md`
- 查看 API 文档：访问 `http://127.0.0.1:7000/docs`
- 查看集成示例：`scripts/memory_client.py`

