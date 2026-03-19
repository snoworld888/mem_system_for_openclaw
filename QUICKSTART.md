# 🚀 Memory Service Skill - 快速指引

## 5 分钟快速启动

### 1️⃣ 启动服务（30 秒）
```bash
cd c:\07code\mem_server
python main.py
```
✅ 看到 `Application startup complete` 表示成功

### 2️⃣ 验证服务（1 分钟）
打开浏览器：**http://127.0.0.1:7000/docs**
✅ 看到 Swagger API 文档

### 3️⃣ 在 OpenClaw 中配置（3 分钟）

**选项 A：系统提示词（最简单）**
```
打开 skill/assets/SYSTEM_PROMPT_EXAMPLES.md
复制"基础版"内容到 OpenClaw 系统提示词
完成！
```

**选项 B：Python 脚本**
```python
import requests

# 查询
ctx = requests.post("http://127.0.0.1:7000/memory/query", 
  json={"session_id": "user_123", "user_query": "..."}).json()

# 使用返回的 ctx["messages"]
```

### 4️⃣ 测试（1 分钟）
在 OpenClaw 中开始聊天，服务会自动记录对话！

---

## 📂 关键文件位置

| 文件 | 用途 |
|------|------|
| `skill/SKILL.md` | 📖 完整文档 |
| `skill/README.md` | 🚀 快速参考 |
| `skill/assets/SYSTEM_PROMPT_EXAMPLES.md` | 💬 提示词模板 |
| `skill/scripts/memory_client.py` | 🐍 Python 客户端 |
| `http://127.0.0.1:7000/docs` | 📚 API 文档 |

---

## ⭐ 核心概念（30 秒理解）

```
四层记忆（按优先级）：
  
  规则（Rules）
    ↓ 系统准则，最重要
  档案（Profile）
    ↓ 用户背景信息
  长期记忆（LTM）
    ↓ 历史重要信息
  短期记忆（STM）
    ↓ 最近对话，自动压缩

Token 节省 30-50% ⚡
```

---

## 🎯 三个 API（只需要这三个！）

```bash
# ⭐ 对话前：查询上下文
POST /memory/query
Request:  {"session_id": "user_123", "user_query": "用户问题"}
Response: {"messages": [...], "rules": "...", "profile": "..."}

# ⭐ 对话后：记录对话
POST /memory/turn
Request:  {"session_id": "user_123", "user_message": "...", "assistant_message": "..."}

# ⭐ 重要信息：保存记忆
POST /memory/save
Request:  {"session_id": "user_123", "content": "...", "importance": "high"}
```

---

## 💡 最佳实践

1. ✅ **每次对话前调用 `/memory/query`** - 这最重要！
2. ✅ **每次对话后调用 `/memory/turn`** - 自动记录
3. ✅ **重要信息时调用 `/memory/save`** - 永久保存
4. ✅ **定期检查 `/memory/stats`** - 监控状态

---

## 🧪 快速测试

### 使用网页测试（最简单）
1. 打开 http://127.0.0.1:7000/docs
2. 展开 `POST /memory/query`
3. 点击 "Try it out"
4. 输入示例数据
5. 点击 "Execute"

### 使用 curl 测试
```bash
curl -X POST http://127.0.0.1:7000/memory/query \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","user_query":"test"}'
```

### 使用 Python 测试
```bash
python skill/scripts/memory_client.py
```

---

## ⚙️ 常见配置

修改 `.env` 文件，重启服务后生效：

```bash
# 要返回更多信息？
DEFAULT_MAX_TOKENS=3000

# 要更快的反应速度？
STM_MAX_TOKENS=1000
ASSEMBLY_LTM_TOKENS=400

# 要用更好的模型？
EMBEDDING_MODEL=sentence-transformers/multilingual-e5-large
```

---

## 🆘 遇到问题？

| 问题 | 解决方案 |
|------|----------|
| 无法连接 127.0.0.1:7000 | 检查服务是否启动（`python main.py`） |
| 模型下载失败 | ✅ 正常，自动降级为 TF-IDF 离线模式 |
| Token 消耗太多 | 调整 `.env` 中的 token 预算 |
| 记忆没有保存 | 确保调用了 `/memory/turn` |

完整问题列表：见 `skill/SKILL.md`

---

## 📚 下一步

1. **了解更多**：阅读 `skill/SKILL.md`
2. **查看示例**：打开 `skill/assets/SYSTEM_PROMPT_EXAMPLES.md`
3. **集成到 OpenClaw**：按照上面第 3 步配置
4. **监控运行**：定期检查 `/memory/stats`

---

## 🎓 重点总结

✅ **启动**：`python main.py`  
✅ **验证**：http://127.0.0.1:7000/docs  
✅ **集成**：复制提示词或使用客户端  
✅ **三个 API**：`/query` → `/turn` → `/save`  
✅ **自动优化**：Token 减少 30-50%  

**就这么简单！** 🚀

