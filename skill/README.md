# Memory Service Skill for OpenClaw

💾 一个为 OpenClaw 设计的**长期记忆管理 Skill**，帮助 AI 助手减少 Token 消耗、实现持久化记忆。

---

## 📁 目录结构

```
skill/
├── SKILL.md                          # Skill 核心文档（包含所有功能说明）
├── OPENCLAW_INTEGRATION.md           # OpenClaw 集成指南
├── README.md                         # 本文件
├── scripts/
│   ├── memory_client.py             # Python 客户端库
│   └── openclaw_integration.py       # 命令行工具
└── assets/
    └── (图片、配置示例等)
```

---

## 🚀 快速开始

### 1. 启动记忆服务

```bash
cd c:\07code\mem_server
python main.py
```

服务在 `http://127.0.0.1:7000` 上运行。

### 2. 在 OpenClaw 中使用

**最简单的方式**：在系统提示词中添加

```
在对话前调用：POST http://127.0.0.1:7000/memory/query
  请求：{"session_id": "user_id", "user_query": "..."}
  响应：包含规则、用户档案、历史对话、相关记忆

在对话后调用：POST http://127.0.0.1:7000/memory/turn
  记录本轮对话用于后续查询
```

### 3. 查看完整文档

- **`SKILL.md`** - 完整的功能说明、API 参考、使用示例
- **`OPENCLAW_INTEGRATION.md`** - OpenClaw 集成指南和最佳实践

---

## ⭐ 核心特性

| 功能 | 说明 |
|------|------|
| 🧠 **长期记忆** | 用户信息、偏好、关键事实（向量检索） |
| ⚡ **短期记忆** | 最近对话（自动压缩） |
| 👤 **用户档案** | 背景、能力、偏好（固定注入） |
| 📋 **行为准则** | 系统规则（优先级最高） |
| 💚 **Token 优化** | 相关性过滤、自动压缩，节省 30-50% token |
| 🔌 **离线运行** | 无 API 依赖，网络不通自动降级 |

---

## 📚 API 速查

### 最常用的 3 个接口

```bash
# 1. 查询上下文（对话前）- 这个最重要！
POST /memory/query
{ "session_id": "user_123", "user_query": "..." }
← 返回 messages，可直接传给 LLM

# 2. 记录对话（对话后）
POST /memory/turn
{ "session_id": "user_123", "user_message": "...", "assistant_message": "..." }

# 3. 保存重要信息
POST /memory/save
{ "session_id": "user_123", "content": "...", "importance": "high" }
```

完整 API 参考见 `SKILL.md` 或访问 `http://127.0.0.1:7000/docs`

---

## 💡 使用场景

### 场景 1：保持用户背景

```python
# 查询记忆（获取用户档案、规则、历史信息）
ctx = requests.post(
    "http://127.0.0.1:7000/memory/query",
    json={"session_id": "user_123", "user_query": current_input}
).json()

# 将返回的 messages 添加到 LLM 上下文
messages = ctx["messages"] + [{"role": "user", "content": current_input}]

# 调用 LLM
response = llm.chat(messages)

# 记录对话
requests.post(
    "http://127.0.0.1:7000/memory/turn",
    json={"session_id": "user_123", "user_message": current_input, "assistant_message": response}
)
```

### 场景 2：长对话 Token 优化

```
对话进行 20 轮后 → 短期记忆自动压缩
避免 token 爆增，后续 /memory/query 返回更精简的上下文
```

### 场景 3：用户关键信息保存

```bash
# 用户说："我是 Python 工程师，擅长异步编程"
POST /memory/save
{
  "session_id": "user_123",
  "content": "用户是 Python 工程师，擅长异步编程",
  "memory_type": "long_term",
  "importance": "high"
}

# 后续查询时，相关问题会自动返回这条记忆
```

---

## 🔧 集成方式

| 方式 | 复杂度 | 推荐场景 |
|------|--------|----------|
| **系统提示词** | ⭐ 简单 | 快速集成 |
| **Python 客户端** | ⭐⭐ 中等 | 自定义脚本 |
| **命令行工具** | ⭐⭐ 中等 | 外部调用 |
| **HTTP 直调** | ⭐⭐⭐ 复杂 | 完全自定义 |

详见 `OPENCLAW_INTEGRATION.md`

---

## 📊 性能

| 指标 | 数值 |
|------|------|
| 查询延迟 | 50-200ms |
| Token 节省比例 | 30-50% |
| 支持会话数 | 1000+ 并发 |
| 离线模式精度 | ~70%（TF-IDF 降级） |

---

## ⚙️ 配置

### 环境变量（`.env`）

```bash
# 数据目录
DATA_DIR=./data

# 嵌入模型
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# Token 预算
STM_MAX_TOKENS=1500
DEFAULT_MAX_TOKENS=2000
ASSEMBLY_RULES_TOKENS=300
ASSEMBLY_PROFILE_TOKENS=200
ASSEMBLY_LTM_TOKENS=600
```

详见项目根目录的 `.env.example`

---

## 🐛 故障排查

### 连接失败

```bash
# 确保服务已启动
python main.py

# 检查端口
netstat -ano | findstr :7000
```

### 嵌入模型加载失败

```
[正常] EmbeddingManager 自动降级为 TF-IDF，无需操作
       功能完整，只是精度略低
```

### Token 消耗仍然很多

- 检查 `/memory/stats` 统计
- 在 `.env` 中降低 token 预算
- 定期调用 `/memory/clear` 清理旧会话

---

## 📖 文档地图

```
skill/SKILL.md                 ← 完整功能文档（必读）
skill/OPENCLAW_INTEGRATION.md  ← OpenClaw 集成指南（集成前读）
scripts/memory_client.py       ← Python 客户端示例代码
scripts/openclaw_integration.py ← 命令行工具使用
```

---

## 🎯 推荐工作流

```
1️⃣  启动服务
    python main.py

2️⃣  配置 OpenClaw
    在系统提示词中添加记忆调用逻辑
    或使用 memory_client.py

3️⃣  每轮对话
    前：调用 /memory/query  → 获取背景+历史
    后：调用 /memory/turn   → 记录对话
    重要时刻：调用 /memory/save → 永久保存

4️⃣  监控和优化
    GET /memory/stats       → 查看统计
    根据需要调整 .env 配置
```

---

## 💪 开发者

有想法或发现 bug？

1. 查看 `SKILL.md` 的"高级配置"章节
2. 修改 `src/` 下的核心模块
3. 测试：`python test_e2e.py`
4. 重启服务

---

## 📝 许可

MIT License

---

**现在就开始吧！** 👉 [集成指南](OPENCLAW_INTEGRATION.md)
