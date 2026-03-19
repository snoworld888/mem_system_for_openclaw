# 🚀 立即开始 - 3 分钟快速启动

## 问题背景

你遇到了 Swagger UI 页面空白的问题（浏览器跟踪防护），但这**不影响 API 功能**。

---

## ✅ 立即解决方案

### 方案 1️⃣：Python 测试脚本（推荐 ⭐）

最快最简单，完全绕过浏览器问题。

**终端 1 - 启动服务**
```bash
cd c:\07code\mem_server
python main.py --port 9000
```

看到这行表示成功：
```
INFO:     Application startup complete.
```

**终端 2 - 运行测试**
```bash
cd c:\07code\mem_server
python test_api.py
```

这会自动测试所有 API 并显示结果 ✅

---

### 方案 2️⃣：curl 快速测试

```bash
# 测试健康检查
curl http://127.0.0.1:9000/health

# 测试查询 API
curl -X POST http://127.0.0.1:9000/memory/query \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","user_query":"test"}'
```

---

### 方案 3️⃣：浏览器查看（需修复）

如果想用浏览器查看 Swagger UI：

1. 打开浏览器设置
2. 关闭"跟踪防护" / "隐私保护"
3. 访问 `http://127.0.0.1:9000/docs`

---

## ⚡ 对接 OpenClaw

现在用新地址对接 OpenClaw：

**旧地址**：`http://127.0.0.1:7000`  
**新地址**：`http://127.0.0.1:9000`

在 OpenClaw 的系统提示词中，将所有 8765 改为 9000 即可。

参考 `skill/assets/SYSTEM_PROMPT_EXAMPLES.md`

---

## 📝 三个关键 API

```bash
# ⭐ 查询上下文（对话前）
POST /memory/query
{"session_id": "user_123", "user_query": "..."}
→ 返回 messages（直接传给 LLM）

# 记录对话（对话后）
POST /memory/turn
{"session_id": "user_123", "user_message": "...", "assistant_message": "..."}

# 保存重要信息
POST /memory/save
{"session_id": "user_123", "content": "...", "importance": "high"}
```

---

## ✅ 验证步骤

1. ✅ 启动服务
   ```bash
   python main.py --port 9000
   ```

2. ✅ 查看是否启动成功
   ```
   看到 "Application startup complete."
   ```

3. ✅ 运行测试
   ```bash
   python test_api.py
   ```

4. ✅ 看到测试通过
   ```
   ✅ 所有测试通过！记忆服务运行正常。
   ```

5. ✅ 对接 OpenClaw
   ```
   使用 http://127.0.0.1:9000
   ```

---

## 🎯 现在就试试

### 快速命令

```bash
# 一键启动
cd c:\07code\mem_server && python main.py --port 9000
```

### 在另一个窗口测试

```bash
cd c:\07code\mem_server && python test_api.py
```

### 看到输出

```
============================================================
  1️⃣ 健康检查
============================================================
状态码: 200
响应: {"status": "ok", ...}

...

📊 测试总结
通过: 8/8

✅ 所有测试通过！记忆服务运行正常。
```

**完成！** 🎉

---

## 🆘 遇到问题？

| 问题 | 解决 |
|------|------|
| 连接被拒绝 | 确保服务已启动（`python main.py --port 9000`） |
| 端口被占用 | 改用其他端口（`--port 9001`） |
| 模块缺失 | `pip install fastapi uvicorn chromadb sentence-transformers` |
| Swagger UI 空白 | 正常现象，用测试脚本或关闭浏览器跟踪防护 |

详见 `TROUBLESHOOTING.md`

---

## 📚 更多信息

- **快速参考**：`QUICKSTART.md`
- **完整文档**：`skill/SKILL.md`
- **故障排查**：`TROUBLESHOOTING.md`
- **系统提示词**：`skill/assets/SYSTEM_PROMPT_EXAMPLES.md`

---

## 💪 核心功能

✅ 四层记忆（规则/档案/长期/短期）  
✅ Token 优化（节省 30-50%）  
✅ 完全离线运行  
✅ 多用户隔离  
✅ 自动压缩  

**准备好了吗？** 👇

```bash
python main.py --port 9000
```

