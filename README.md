# ResearchMind 一键启动

## 🚀 快速启动

### Linux / macOS / Git Bash
```bash
./start.sh
```

### Windows PowerShell
```powershell
bash start.sh
```

## 📋 系统要求

- Python 3.10+
- Node.js 18+
- uv (Python包管理器)

### 安装uv
```bash
# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

## 🌐 访问地址

启动后可通过以下地址访问：

- **前端界面**: `http://localhost:50001`
- **外部访问**: `http://your-ip:50001`
- **API文档**: `http://your-ip:50002/docs`
- **后端API**: `http://localhost:50002` (本地) 或 `http://your-ip:50002` (外部)

## 🔧 配置

启动脚本会在项目根目录生成 `.env` 文件，下面列出需要关注的关键项：

### API 密钥
```
GOOGLE_API_KEY=your_google_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
TAVILY_API_KEY=your_tavily_api_key
MP_API_KEY=your_materials_project_api_key
```

### 网络相关变量
```
# UI 服务监听（start_complete.* 会把 50001 转发到该端口）
VITE_FRONTEND_HOST=127.0.0.1
VITE_FRONTEND_PORT=50010

# 前端调用 API/WS 时使用的相对路径 + 对外端口
VITE_API_URL=/api
VITE_API_PORT=50001
VITE_WS_URL=/ws
VITE_WS_PORT=50001

# 后端实际监听（默认仅限本机）
RESEARCHMIND_HTTP_HOST=127.0.0.1
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=127.0.0.1
RESEARCHMIND_WS_PORT=50003

# MCP 服务
PAPER_SEARCH_MCP_HOST=127.0.0.1
PAPER_SEARCH_MCP_PORT=50004
SIMULATION_MCP_HOST=127.0.0.1
SIMULATION_MCP_PORT=50005
DATABASE_MCP_HOST=127.0.0.1
DATABASE_MCP_PORT=50006
```

> **提示**
> - 如果不使用反向代理，可将 `VITE_API_URL` 改为 `http://127.0.0.1:50002/api`、`VITE_WS_URL` 改为 `ws://127.0.0.1:50003/ws`，并同步调整 `VITE_API_PORT` 与 `VITE_WS_PORT`。
> - 对外发布时，把 `*_HOST` 设置为 `0.0.0.0`，其它保持不变即可，由代理补全域名。

## 🛑 停止服务

按 `Ctrl+C` 停止所有服务，或使用：
```bash
./stop_all.sh
```

## ✨ 完整启动脚本特性

### 🔧 自动化功能
- ✅ **环境检查** - 自动检测uv、npm、Python等依赖
- ✅ **IP地址检测** - 自动获取本机IP地址
- ✅ **端口冲突处理** - 检测并处理端口占用
- ✅ **配置文件生成** - 自动创建正确的.env配置
- ✅ **服务健康检查** - 验证服务启动状态
- ✅ **防火墙配置** - 自动添加防火墙规则（Linux）
- ✅ **服务监控** - 实时监控服务运行状态

### 🎯 智能特性
- 🔄 **强制重启** - 自动停止现有服务并重启
- 🌐 **外部访问** - 正确配置外部IP访问
- 📊 **状态显示** - 清晰显示所有服务状态和访问地址
- 🚀 **一键启动** - 无需手动配置，一键完成所有设置

## 📝 日志文件

- logs/backend.log – WebSocket/HTTP 主服务
- logs/paper_search.log – 论文检索 MCP
- logs/simulation.log – 仿真 MCP
- logs/database.log – 数据库 MCP
- logs/frontend.log – 前端构建/运行

## 🔧 故障排除

## 🛠️ 常见问题

### 1. 前端依赖加载错误 (ERR_CONTENT_LENGTH_MISMATCH)

如果在访问前端时遇到 `ERR_CONTENT_LENGTH_MISMATCH` 错误，通常是由于 Nginx 缓冲设置导致的。系统已自动配置了解决方案：

1. 确保使用了最新版本的 Nginx 配置文件
2. 重启 Nginx 服务使配置生效：
   ```bash
   # Windows
   nginx -s reload
   
   # Linux
   sudo systemctl reload nginx
   ```

### 2. 端口冲突

如果遇到端口冲突错误，可以修改 `.env` 文件中的端口配置：

```bash
# UI 服务监听（start_complete.* 会把 50001 转发到该端口）
VITE_FRONTEND_HOST=127.0.0.1
VITE_FRONTEND_PORT=50010

# 前端调用 API/WS 时使用的相对路径 + 对外端口
VITE_API_URL=/api
VITE_API_PORT=50001
VITE_WS_URL=/ws
VITE_WS_PORT=50001

# 后端实际监听（默认仅限本机）
RESEARCHMIND_HTTP_HOST=127.0.0.1
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=127.0.0.1
RESEARCHMIND_WS_PORT=50003

# MCP 服务
PAPER_SEARCH_MCP_HOST=127.0.0.1
PAPER_SEARCH_MCP_PORT=50004
SIMULATION_MCP_HOST=127.0.0.1
SIMULATION_MCP_PORT=50005
DATABASE_MCP_HOST=127.0.0.1
DATABASE_MCP_PORT=50006