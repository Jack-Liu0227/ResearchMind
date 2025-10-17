# ResearchMind 一键启动

## 🚀 快速启动

### 完整启动脚本（推荐）

#### Windows PowerShell
```powershell
# 基本启动
.\start_complete.ps1

# 指定IP地址
.\start_complete.ps1 -IP "192.168.1.100"

# 强制重启服务
.\start_complete.ps1 -Force
```

#### Linux/Mac
```bash
# 基本启动
./start_complete.sh

# 指定IP地址
./start_complete.sh --ip "192.168.1.100"

# 强制重启服务
./start_complete.sh --force
```

#### Windows Git Bash（推荐）
```bash
# 基本启动
./start_windows.sh

# 指定IP地址
./start_windows.sh --ip "192.168.1.100"

# 强制重启服务
./start_windows.sh --force
```

### 简单启动脚本

#### Linux/Mac/Git Bash
```bash
./start.sh
```

#### Windows PowerShell
```powershell
.\start.ps1
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

## 🔧 配置

脚本会自动创建基本的 `.env` 配置文件，包含正确的网络配置：

### 重要的网络配置
- **前端UI**: 必须使用 `0.0.0.0` 才能支持外部访问
- **后端API**: 使用 `0.0.0.0` 支持外部访问  
- **MCP服务**: 使用 `localhost` 作为内部服务

### API密钥配置
请在 `.env` 文件中填写您的API密钥：
```env
GOOGLE_API_KEY=your_google_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
TAVILY_API_KEY=your_tavily_api_key
MP_API_KEY=your_materials_project_api_key
```

### 自动生成的配置示例
```env
# 前端配置 - UI必须使用 0.0.0.0 才能外部访问
VITE_FRONTEND_HOST=0.0.0.0
VITE_API_URL=http://your-ip:50002
VITE_WS_URL=ws://your-ip:50003/ws

# 后端服务 - 需要外部访问
RESEARCHMIND_HOST=0.0.0.0

# MCP 服务器配置 - 内部服务使用 localhost
PAPER_SEARCH_HOST=localhost
DATABASE_HOST=localhost  
SIMULATION_HOST=localhost
```

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

- `logs/backend.log` - 后端服务日志
- `logs/database.log` - 数据库服务日志
- `logs/paper_search.log` - 论文搜索服务日志
- `logs/simulation.log` - 仿真服务日志
- `logs/frontend.log` - 前端服务日志

## 🔧 故障排除

### 端口被占用
```powershell
# Windows
.\start_complete.ps1 -Force

# Linux/Mac
./start_complete.sh --force
```

### IP地址配置错误
```powershell
# 修复环境配置
.\fix_env.ps1
```

### 服务启动失败
检查对应的日志文件，查看具体错误信息。