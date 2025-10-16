---
type: "manual"
---

# ResearchMind V2 Python 启动脚本使用指南

本项目提供了两个Python启动脚本，让您可以用Python一键运行整个ResearchMind项目。

## 📁 脚本文件

### 1. `run.py` - 简化版快速启动脚本（推荐）
- ✨ 界面简洁，操作简单
- 🚀 快速启动，适合日常开发和测试
- 💬 交互式选择是否安装依赖
- 🎯 专注核心功能

### 2. `start_all.py` - 完整功能启动脚本
- 🔧 功能完整，支持所有配置选项
- 📊 详细的健康检查和状态监控
- 🎨 彩色输出和美观界面
- ⚙️ 支持命令行参数配置

## 🚀 快速开始

### 使用 `run.py`（推荐新手）

```bash
# 直接运行（最简单的方式）
python run.py

# 或者
python3 run.py
```

脚本会自动：
1. 检查Python版本和必需工具（uv, node, npm）
2. 设置项目环境（创建.env文件和日志目录）
3. 询问是否安装依赖
4. 启动后端（FastAPI）和前端（React）服务
5. 自动打开浏览器访问 http://localhost:5173
6. 监控服务状态，按Ctrl+C停止所有服务

### 使用 `start_all.py`（功能更强大）

```bash
# 基本使用
python start_all.py

# 跳过依赖安装（如果已经安装过）
python start_all.py --skip-install

# 不自动打开浏览器
python start_all.py --no-browser

# 自定义端口
python start_all.py --backend-port 8080 --frontend-port 3000

# 自定义日志目录
python start_all.py --log-dir my_logs

# 查看所有选项
python start_all.py --help
```

## 📋 环境要求

### 必需环境
- **Python**: 3.10 或更高版本
- **UV**: Python包管理器 
- **Node.js**: 16+ 版本
- **npm**: Node包管理器

### 安装UV（如果还没安装）

**Windows PowerShell:**
```powershell
iwr -Uri https://astral.sh/uv/install.ps1 | iex
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安装Node.js
访问 https://nodejs.org/ 下载安装最新LTS版本

## 🔧 脚本功能对比

| 功能 | run.py | start_all.py |
|------|--------|--------------|
| 环境检查 | ✅ 基础检查 | ✅ 详细检查 |
| 依赖安装 | ✅ 交互式选择 | ✅ 可选参数控制 |
| 服务启动 | ✅ 基本启动 | ✅ 高级启动 |
| 健康检查 | ❌ | ✅ HTTP健康检查 |
| 日志管理 | ✅ 基本日志 | ✅ 详细日志管理 |
| 彩色输出 | ✅ 基础彩色 | ✅ 丰富彩色界面 |
| 命令行参数 | ❌ | ✅ 完整参数支持 |
| 端口检查 | ❌ | ✅ 端口占用检查 |
| 进程监控 | ✅ 基本监控 | ✅ 高级监控 |

## 📊 服务信息

启动成功后，您可以访问：

- **前端界面**: http://localhost:5173
- **后端API**: http://localhost:8000  
- **API文档**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws/{client_id}

## 📝 日志文件

脚本会在 `logs/` 目录下创建日志文件：
- 后端日志: `backend_YYYYMMDD_HHMMSS.log`
- 前端日志: `frontend_YYYYMMDD_HHMMSS.log`
- 安装日志: `install.log`, `npm-install.log`

## 🛠️ 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # Windows查看端口占用
   netstat -ano | findstr :8000
   netstat -ano | findstr :5173
   
   # 结束占用端口的进程
   taskkill /PID <进程ID> /F
   ```

2. **UV命令不存在**
   ```bash
   # 重新安装UV
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # 或在PowerShell中
   iwr -Uri https://astral.sh/uv/install.ps1 | iex
   ```

3. **Node.js/npm不存在**
   - 访问 https://nodejs.org/ 安装Node.js
   - npm会随Node.js一起安装

4. **权限问题**
   ```bash
   # 确保脚本有执行权限（Linux/Mac）
   chmod +x run.py
   chmod +x start_all.py
   ```

5. **依赖安装失败**
   ```bash
   # 手动安装后端依赖
   uv sync
   
   # 手动安装前端依赖
   cd ui
   npm install
   cd ..
   ```

### 调试模式

如果遇到问题，可以查看详细日志：

```bash
# 查看后端日志
tail -f logs/backend_*.log

# 查看前端日志  
tail -f logs/frontend_*.log

# Windows使用
type logs\backend_*.log
type logs\frontend_*.log
```

## 💡 使用技巧

1. **首次运行**: 建议选择安装依赖，后续运行可以跳过
2. **开发环境**: 使用 `run.py` 更方便快捷
3. **生产环境**: 使用 `start_all.py` 获得更多控制
4. **自定义配置**: 编辑 `.env` 文件配置API密钥等
5. **快速重启**: Ctrl+C 停止后可以立即重新运行脚本

## 🔄 与PowerShell脚本的对比

| 特性 | Python脚本 | PowerShell脚本 |
|------|-----------|----------------|
| 跨平台支持 | ✅ 全平台 | ❌ 仅Windows |
| 易于修改 | ✅ Python语法简洁 | ⚠️ PowerShell语法复杂 |
| 功能完整性 | ✅ 功能完整 | ✅ 功能完整 |
| 颜色支持 | ✅ 跨平台颜色 | ✅ Windows颜色 |
| 依赖要求 | Python 3.10+ | PowerShell 5.0+ |

## 📧 获取帮助

如果遇到问题或有建议，请：

1. 检查日志文件中的错误信息
2. 确认环境要求是否满足
3. 查看项目的GitHub Issues
4. 联系开发团队

---

🎉 现在您可以使用Python脚本快速启动ResearchMind项目了！建议先试用 `run.py`，熟悉后可以使用功能更强大的 `start_all.py`。