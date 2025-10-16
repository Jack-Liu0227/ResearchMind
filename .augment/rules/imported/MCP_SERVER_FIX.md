---
type: "manual"
---

# ResearchMind V2 - MCP 服务器修复总结

## 🐛 问题描述

运行 MCP 服务器时出现以下错误：
```
TypeError: 'FastMCP' object is not callable
```

## 🔍 问题分析

FastMCP 对象本身不是 ASGI 应用程序，不能直接传递给 uvicorn.run()。需要使用 FastMCP 对象的特定属性来获取正确的 ASGI 应用。

## ✅ 解决方案

### 修复方式
将所有 MCP 服务器的启动代码从：
```python
# 错误的方式
uvicorn.run("server:app", ...)
```

改为：
```python
# 正确的方式
uvicorn.run(app.http_app, ...)
```

### 具体修改

#### 1. 大型服务器（详细启动配置）
- **`mcp_servers/paper_search/server.py`**
- **`mcp_servers/materials/server.py`**  
- **`mcp_servers/simulation/server.py`**

修改内容：
```python
# 修改前
uvicorn.run(
    "server:app",
    host="127.0.0.1",
    port=5001,
    log_level="info",
    reload=True
)

# 修改后
uvicorn.run(
    app.http_app,  # Use the HTTP app from FastMCP
    host="127.0.0.1",
    port=5001,
    log_level="info",
    reload=False  # Disable reload for FastMCP
)
```

#### 2. 小型服务器（简化启动配置）
- **`mcp_servers/data_analysis/server.py`**
- **`mcp_servers/experiment/server.py`**
- **`mcp_servers/rdkit/server.py`**
- **`mcp_servers/structure_generate/server.py`**

修改内容：
```python
# 修改前
uvicorn.run("server:app", host="127.0.0.1", port=5004, log_level="info", reload=True)

# 修改后
uvicorn.run(app.http_app, host="127.0.0.1", port=5004, log_level="info", reload=False)
```

## 🛠️ 技术细节

### FastMCP 应用类型
根据 FastMCP 文档和弃用警告：

1. **`app.sse_app`** - Server-Sent Events 应用（已弃用）
2. **`app.http_app`** - 现代 HTTP 应用（推荐）
3. **`app.streamable_http_app`** - 流式 HTTP 应用

### 为什么禁用 reload？
FastMCP 应用在 reload 模式下可能不稳定，因此设置 `reload=False`。

## 📊 修复状态

| 服务器 | 端口 | 状态 | 备注 |
|-------|------|------|------|
| paper_search | 5001 | ✅ 已修复 | 论文搜索服务 |
| materials | 5002 | ✅ 已修复 | 材料数据库服务 |
| simulation | 5003 | ✅ 已修复 | 模拟计算服务 |
| data_analysis | 5004 | ✅ 已修复 | 数据分析服务 |
| experiment | 5005 | ✅ 已修复 | 实验设计服务 |
| rdkit | 5006 | ✅ 已修复 | 化学工具服务 |
| structure_generate | 5007 | ✅ 已修复 | 结构生成服务 |

## 🚀 测试验证

### 单独启动服务器
```bash
# 在项目根目录下
uv run python mcp_servers/paper_search/server.py
uv run python mcp_servers/materials/server.py
uv run python mcp_servers/simulation/server.py
uv run python mcp_servers/data_analysis/server.py
uv run python mcp_servers/experiment/server.py
uv run python mcp_servers/rdkit/server.py
uv run python mcp_servers/structure_generate/server.py
```

### 预期输出
```
2025-09-29 18:25:00 [info     ] Starting [Service Name] MCP Server
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:[PORT] (Press CTRL+C to quit)
```

## ⚠️ 注意事项

### WebSocket 弃用警告
修复后可能仍会看到以下警告，这是依赖库的问题，不影响功能：
```
DeprecationWarning: websockets.legacy is deprecated
DeprecationWarning: websockets.server.WebSocketServerProtocol is deprecated
```

### 端口占用
如果出现端口占用错误：
```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 5001): 通常每个套接字地址(协议/网络地址/端口)只允许使用一次。
```

解决方案：
1. 停止已运行的服务
2. 或修改端口号
3. 或使用 `netstat -ano | findstr :5001` 查找占用进程并结束

## 🔄 与主启动脚本的集成

修复后的 MCP 服务器已经与以下启动脚本兼容：
- ✅ `run.py` - 简化启动脚本
- ✅ `start_all.py` - 完整功能启动脚本
- ✅ `start.bat` - Windows 批处理文件
- ✅ `start_all.ps1` - PowerShell 脚本

## 📝 总结

所有 MCP 服务器现在可以正常启动，主要修复包括：

1. **使用正确的 ASGI 应用**: `app.http_app` 而不是字符串引用
2. **禁用 reload**: 避免 FastMCP 在 reload 模式下的不稳定性
3. **使用现代 API**: `http_app` 而不是已弃用的 `sse_app`
4. **添加启动日志**: 更好的调试和监控

现在可以通过 Python 启动脚本安全地启动整个 ResearchMind 项目了！🎉