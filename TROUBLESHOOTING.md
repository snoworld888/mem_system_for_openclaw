# 快速诊断和测试指南

## 问题诊断

### ❌ 浏览器显示空页面 / localStorage 错误

这是**浏览器跟踪防护**阻止了 Swagger UI 的 localStorage，但 **API 本身完全正常**。

解决方案：
1. **关闭浏览器跟踪防护**（推荐快速方式）
2. **直接测试 API**（无需 UI）
3. **使用 API 测试脚本**（推荐）

---

## ✅ 解决方案 1：关闭浏览器跟踪防护

### Firefox
1. 地址栏输入：`about:config`
2. 搜索：`privacy.trackingprotection.enabled`
3. 改为 `false`
4. 刷新 `http://127.0.0.1:7000/docs`

### Chrome/Edge
1. 设置 → 隐私和安全 → 跟踪防护
2. 改为"无"或"基本"
3. 刷新页面

### Safari
1. 设置 → 隐私
2. 取消勾选 "防止跨网站追踪"

---

## ✅ 解决方案 2：直接用 curl 测试 API

```bash
# 1. 测试健康检查
curl http://localhost:9000/health

# 2. 查询记忆
curl -X POST http://localhost:9000/memory/query \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_user",
    "user_query": "test query"
  }'

# 3. 记录对话
curl -X POST http://localhost:9000/memory/turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_user",
    "user_message": "Hello",
    "assistant_message": "Hi there"
  }'
```

---

## ✅ 解决方案 3：使用 Python 测试脚本（推荐）

### 启动服务

```bash
cd c:\07code\mem_server
python main.py --host 127.0.0.1 --port 9000
```

### 在另一个终端运行测试

```bash
cd c:\07code\mem_server
python test_api.py
```

这个脚本会：
- ✅ 自动连接检查
- ✅ 测试所有 8 个 API
- ✅ 详细显示结果
- ✅ 最后总结

---

## 🔧 常见问题

### 问题：port already in use

**原因**：8765 或 9000 端口被占用

**解决**：
```bash
# 使用其他端口
python main.py --port 9001

# 或者查找并杀死占用进程
netstat -ano | findstr :8765
taskkill /PID <PID> /F
```

### 问题：连接被拒绝

**原因**：服务未启动或网络问题

**解决**：
```bash
# 1. 确保服务启动
cd c:\07code\mem_server
python main.py

# 2. 检查端口
netstat -ano | findstr :9000

# 3. 尝试本地连接
curl http://127.0.0.1:9000/health
```

### 问题：模块导入错误

**原因**：依赖未装或环境问题

**解决**：
```bash
pip install fastapi uvicorn pydantic chromadb sentence-transformers tiktoken python-dotenv
python main.py
```

---

## 📋 完整启动流程

### 方式 A：快速测试（推荐）

```bash
# 终端 1
cd c:\07code\mem_server
python main.py --port 9000

# 终端 2
cd c:\07code\mem_server
python test_api.py
```

### 方式 B：浏览器查看（需关闭跟踪防护）

```bash
# 启动服务
python main.py --port 9000

# 浏览器打开
http://127.0.0.1:9000/docs
```

### 方式 C：integr with OpenClaw

```
使用 http://127.0.0.1:9000 替代 127.0.0.1:7000
其他所有配置保持不变
```

---

## ✅ 验证清单

- [ ] 服务启动：`python main.py --port 9000`
- [ ] 健康检查：`curl http://127.0.0.1:9000/health`
- [ ] API 测试：`python test_api.py`
- [ ] 对接 OpenClaw：使用 `http://127.0.0.1:9000` 地址

---

## 📞 快速参考

| 任务 | 命令 |
|------|------|
| 启动服务 | `python main.py --port 9000` |
| 测试服务 | `python test_api.py` |
| 查看文档 | `http://127.0.0.1:9000/docs` |
| 健康检查 | `curl http://127.0.0.1:9000/health` |
| 查询上下文 | `curl -X POST http://127.0.0.1:9000/memory/query ...` |

---

## 💡 推荐方案

**最简单**：使用 Python 测试脚本
```bash
python test_api.py
```

**最直接**：用 curl 测试
```bash
curl http://127.0.0.1:9000/health
```

**最可视化**：修复浏览器后查看 Swagger UI
```
http://127.0.0.1:9000/docs
```

