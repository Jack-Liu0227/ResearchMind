---
type: "manual"
---

# ResearchMind 前后端通信 Quick Start

本指南帮助你在本地快速跑通 React 前端与 FastAPI 后端（含 WebSocket）的通信，并提供一键启动脚本的使用说明。

## 1. 环境准备（Windows + PowerShell）
- Python 3.10+
- Node.js 16+（含 npm）
- UV 包管理器（推荐）

安装 UV（如未安装）：
```powershell
# 安装 UV（PowerShell）
iwr -Uri https://astral.sh/uv/install.ps1 | iex
```

安装后端依赖（在项目根目录执行）：
```powershell
uv sync
```

安装前端依赖：
```powershell
cd ui
npm install
cd ..
```

配置环境变量：
```powershell
# 复制示例环境文件（如 .env 不存在）
if (-not (Test-Path .env) -and (Test-Path .env.example)) { Copy-Item .env.example .env }
# 打开 .env 按需填写（如 GOOGLE_API_KEY 等）
```

## 2. 一键启动脚本
项目根目录已提供 start_all.ps1 脚本，用于一次性启动后端（FastAPI + WebSocket）与前端（Vite）。

运行方式：
```powershell
# 如果执行策略限制脚本运行，先执行下行（可选）：
# Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 启动（默认会自动安装依赖、打开浏览器）
./start_all.ps1

# 可选参数：
# 跳过依赖安装步骤（更快启动）
./start_all.ps1 -SkipInstall
# 不自动打开浏览器
./start_all.ps1 -OpenBrowser:$false
```

脚本功能摘要：
- 检查 uv、node、npm 是否可用并提示缺失项
- 如 .env 缺失则从 .env.example 自动复制一份
- 可选执行依赖安装：`uv sync` 与 `npm install`（在 ui/ 下）
- 并行启动：
  - 后端：`uv run python communication/api_server.py`
  - 前端：在 `ui/` 目录执行 `npm run dev`
- 健康检查与浏览器自动打开（http://localhost:5173）
- 日志输出到 `logs/backend.*.log` 与 `logs/frontend.*.log`

## 3. 前后端通信说明
- REST 接口：
  - 健康检查：`GET http://localhost:8000/api/health`
  - 列出智能体：`GET http://localhost:8000/api/agents`
  - 提交任务：`POST http://localhost:8000/api/task`
  - 获取结果：`GET http://localhost:8000/api/results/{task_id}`
- WebSocket：`ws://localhost:8000/ws/{client_id}`
  - 消息格式示例：
    ```json
    {
      "type": "query",
      "agent": "literature_agent",
      "task": "search_papers",
      "params": { "query": "quantum computing", "limit": 10 }
    }
    ```

确保后端允许前端跨域（若需要）：在 `communication/api_server.py` 中启用 CORS，允许 `http://localhost:5173`。

## 4. 验证步骤
1) 执行 `./start_all.ps1`
2) 浏览器打开 http://localhost:5173（脚本会自动打开，可手动访问）
3) 打开 http://localhost:8000/docs 验证后端 API 正常
4) 打开 `logs/` 目录观察后端与前端日志文件

## 5. 常见问题
- 端口被占用：
  - 后端 8000，前端 5173
  - 查询占用：`netstat -ano | findstr :8000`
- CORS 报错：
  - 确保后端启用了 `CORSMiddleware` 并允许 `http://localhost:5173`
- WebSocket 连接失败：
  - 确认后端已启动、URL 与 `client_id` 正确
- 执行策略限制：
  - 运行 `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- 依赖安装缓慢：
  - 使用 `uv`（更快），或切换国内镜像

## 6. 关闭服务
- 通过任务管理器结束 `python` 与 `node` 进程，或在 PowerShell 中执行：
```powershell
Get-Process -Name python,node -ErrorAction SilentlyContinue | Stop-Process -Force
```

祝你开发顺利！如果需要，我可以进一步提供前端 WebSocket/REST 的最小调用示例组件。