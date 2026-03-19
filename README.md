# Memory Server

面向 OpenClaw / Claude Desktop 等 MCP 客户端的智能记忆服务。
通过四层记忆体系（规则/画像/长期/短期）+ Token预算管理，显著减少每次对话的 Token 消耗。

---

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                    MCP Client (OpenClaw)             │
└─────────────────────┬───────────────────────────────┘
                      │ stdio / HTTP
┌─────────────────────▼───────────────────────────────┐
│                  Memory Server                       │
│  ┌────────────┐  ┌──────────┐  ┌─────────────────┐  │
│  │  MCP Tools │  │REST API  │  │ Context Assembler│  │
│  └─────┬──────┘  └────┬─────┘  └────────┬────────┘  │
│        └──────────────┴─────────────────┘           │
│  ┌────────────────────────────────────────────────┐  │
│  │              Memory Layers                     │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────────┐  │  │
│  │  │  Rules   │ │ Profile  │ │   Long-Term    │  │  │
│  │  │ (规则层) │ │(画像层)  │ │   Memory       │  │  │
│  │  │ ChromaDB │ │ ChromaDB │ │   ChromaDB     │  │  │
│  │  └──────────┘ └──────────┘ └────────────────┘  │  │
│  │  ┌──────────────────────────────────────────┐  │  │
│  │  │        Short-Term Memory (短期记忆)       │  │  │
│  │  │        JSON文件 + 内存缓存                │  │  │
│  │  └──────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────┐  │
│  │  EmbeddingManager  (TF-IDF降级 / 本地模型)    │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 四层记忆

| 层级 | 类型 | 存储 | 生命周期 | 典型内容 |
|------|------|------|----------|----------|
| Rules | 规则层 | ChromaDB | 永久 | 行为准则、回复风格 |
| Profile | 画像层 | ChromaDB | 永久 | 用户名、偏好、背景 |
| Long-Term | 长期记忆 | ChromaDB | 永久 | 重要事实、历史决策 |
| Short-Term | 短期记忆 | JSON+内存 | 会话级 | 最近对话轮次 |

### Token控制策略

```
最大Token预算 (默认2000)
├── 规则层:    最多 300 tokens（固定优先保留）
├── 用户画像:  最多 200 tokens
├── 长期记忆:  最多 600 tokens（按相关性选择 top-k）
└── 短期对话:  剩余 tokens（自动裁剪早期轮次）
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

```bash
cp .env.example .env
# 编辑 .env，至少配置 DATA_DIR
```

### 3. 启动

**MCP模式**（供 OpenClaw 调用，通过 stdio 通信）：
```bash
python main.py --mcp
# 或
start_mcp.bat
```

**HTTP模式**（调试/HTTP客户端）：
```bash
python main.py
# 服务地址: http://127.0.0.1:7000
# API文档: http://127.0.0.1:7000/docs
```

---

## OpenClaw 配置

将以下内容添加到 OpenClaw 的 `openclaw.json` 配置文件：

```json
{
  "mcp": {
    "servers": {
      "memory": {
        "command": "python",
        "args": ["main.py", "--mcp"],
        "cwd": "c:/07code/mem_server"
      }
    }
  }
}
```

**注意：**
- 路径使用正斜杠 `/`（Windows 也支持）
- 第一级是 `"mcp"` → `"servers"`（不是 `mcpServers`）
- 配置文件保存为 `openclaw.json`
- 如需环境变量，在系统环境变量中配置即可

---

## MCP 工具列表

| 工具 | 功能 | 典型场景 |
|------|------|----------|
| `query_memory` | **主工具**：组装上下文 | 每次对话开始前调用 |
| `add_turn` | 添加对话轮次 | 每轮对话结束后调用 |
| `save_memory` | 保存到长期记忆 | 用户说"记住..." |
| `search_memory` | 语义搜索记忆 | 主动查找历史信息 |
| `add_rule` | 添加行为准则 | 配置AI行为规范 |
| `add_profile` | 添加用户信息 | 录入用户背景 |
| `compress_session` | 压缩对话历史 | 长对话节省token |
| `get_stats` | 查看统计信息 | 监控/调试 |
| `clear_session` | 清空短期记忆 | 开始新话题 |

---

## 嵌入模型

### 离线模式（默认）
无需下载任何模型，自动使用 TF-IDF 关键词向量：
- 速度极快（毫秒级）
- 支持中英文
- 适合关键词匹配场景

### 本地模型（推荐）
下载模型后配置本地路径，效果更好：

```bash
# 下载模型（约420MB）
pip install huggingface_hub
python -c "from huggingface_hub import snapshot_download; snapshot_download('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', local_dir='./models/multilingual-MiniLM')"
```

然后在 `.env` 中配置：
```
EMBEDDING_MODEL=./models/multilingual-MiniLM
```

---

## 目录结构

```
mem_server/
├── main.py                 # 主入口
├── requirements.txt        # 依赖
├── .env.example            # 配置模板
├── mcp_config.json         # OpenClaw配置示例
├── start.bat               # HTTP模式启动
├── start_mcp.bat           # MCP模式启动
├── src/
│   ├── config.py           # 配置管理
│   ├── mcp_server.py       # MCP Server（9个工具）
│   ├── memory/
│   │   ├── models.py       # 数据模型
│   │   ├── short_term.py   # 短期记忆管理
│   │   ├── long_term.py    # 长期记忆（ChromaDB）
│   │   ├── assembler.py    # 上下文组装器
│   │   └── compressor.py   # 记忆压缩器
│   ├── api/
│   │   └── routes.py       # FastAPI REST接口
│   └── utils/
│       ├── token_counter.py # Token计数
│       └── embedder.py      # 嵌入管理（自动降级）
├── test_basic.py           # 基础测试
├── test_e2e.py             # 端到端测试
└── data/                   # 数据目录（自动创建）
    ├── chromadb/           # 向量数据库
    └── stm/                # 短期记忆文件
```
# mem_system_for_openclaw
