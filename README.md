# ResearchMind

> 智能材料科学研究助手系统 - 基于 Google ADK 和 MCP 的多 Agent 协作平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285F4.svg)](https://github.com/google/adk)
[![FastMCP](https://img.shields.io/badge/FastMCP-MCP-green.svg)](https://github.com/jlowin/fastmcp)

## 📖 项目简介

**ResearchMind** 是一个基于 Google ADK 和 MCP (Model Context Protocol) 的智能材料科学研究助手系统。它通过协调多个专业 AI Agent 和 MCP Server，为材料科学研究人员提供从文献调研、数据库检索到仿真计算的一站式研究解决方案。

**详细介绍**: [INTRO.md](./INTRO.md)

## ✨ 核心特性

### 🔬 全流程研究支持
- **文献调研**：多源检索（ArXiv + Tavily）、智能分析、报告生成
- **数据库检索**：查询多个材料数据库（Materials Project, OQMD, COD, AFLOW）
- **仿真计算**：晶体结构生成、热导率计算、能量属性预测、声子谱计算

### 🤖 智能多 Agent 协作
- **Deep Research Agent**：专注于学术文献检索和分析（17 个工具）
- **Database Agent**：专注于材料数据库查询和结构获取（8 个工具）
- **Simulation Agent**：专注于计算模拟和性能预测（8 个工具）

### 🔌 模块化 MCP 架构
- **Paper Search MCP Server**：提供文献检索和分析工具
- **Database MCP Server**：提供多数据库查询和结构获取工具
- **Simulation MCP Server**：提供结构生成、弛豫、声子谱、热导率、能量计算工具

### 💾 持久化向量存储
- 支持将论文全文向量化存储到 ChromaDB
- 支持基于向量相似度的语义搜索
- 支持长期追问和知识积累

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface (UI)                      │
│                  (React + TypeScript + Vite)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Google ADK Agents                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Deep Research │  │   Database   │  │  Simulation  │     │
│  │    Agent     │  │    Agent     │  │    Agent     │     │
│  │  (17 tools)  │  │  (8 tools)   │  │  (8 tools)   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (SSE Transport)
┌─────────────────────────────────────────────────────────────┐
│                    MCP Servers (FastMCP)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │Paper Search  │  │Materials DB  │  │  Simulation  │     │
│  │ MCP Server   │  │  MCP Server  │  │  MCP Server  │     │
│  │              │  │              │  │              │     │
│  │Port: 50001   │  │Port: 5002    │  │Port: 5003    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              External Services & Models                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ArXiv + Tavily│  │MP+OQMD+COD   │  │CrystaLLM     │     │
│  │              │  │+AFLOW        │  │+AI4Kappa     │     │
│  │              │  │              │  │+MatterSim    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 方式一: Docker 部署 (推荐用于生产环境)

**前置要求:**
- Docker 20.10+ 和 Docker Compose 2.0+
- Google API Key (必需)

**一键启动:**

```bash
# Linux/Mac
chmod +x docker-start.sh
./docker-start.sh

# Windows PowerShell
.\docker-start.ps1
```

**手动启动:**

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥

# 2. 启动所有服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f
```

**访问地址:**
- 前端 UI: http://localhost
- API 文档: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

**详细文档:** 查看 [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md)

---

### 方式二: 本地开发部署

**前置要求:**
- Python 3.11+
- UV (Python 包管理工具)
- Node.js 18+ (用于 UI)
- Google API Key (用于 Gemini 2.0 Flash)
- Tavily API Key (可选，用于网页搜索)

**安装依赖:**

```bash
# 安装 Python 依赖
uv sync

# 安装 UI 依赖
cd ui
npm install
cd ..
```

**配置环境变量:**

创建 `.env` 文件：

```bash
# Google API Key
GOOGLE_API_KEY=your_google_api_key_here

# Tavily API Key (可选)
TAVILY_API_KEY=your_tavily_api_key_here

# Materials Project API Key (可选)
MP_API_KEY=your_mp_api_key_here
```

**🎯 一键启动 (推荐):**

**Windows PowerShell:**
```powershell
# 启动所有服务器 (MCP + 统一服务器)
.\start_all.ps1

# 停止所有服务器
.\stop_all.ps1
```

**手动启动 (需要 4 个终端):**

**重要**: 必须先启动所有 MCP Servers，否则主服务器会报连接错误！

```bash
# 终端 1: Paper Search MCP Server (端口 50001)
uv run python mcp_servers/paper_search/server.py

# 终端 2: Database MCP Server (端口 5002)
uv run python mcp_servers/database_call/server.py

# 终端 3: Simulation MCP Server (端口 5003)
uv run python mcp_servers/simulation/server.py
```

等待所有服务器显示 "Starting ... MCP Server in SSE mode" 后再继续！

**启动统一服务器 (WebSocket + HTTP):**

```bash
# 终端 4: 统一服务器 (端口 8000)
uv run python main.py
```

**服务端点:**
- WebSocket: `ws://localhost:8000`
- HTTP API: `http://localhost:8000`
- API 文档: `http://localhost:8000/docs`

**启动前端 UI:**

```bash
# 新终端
cd ui
npm run dev
```

访问 `http://localhost:5173` 即可使用。

## 📚 使用示例

### 示例 1：完整研究流程

```
用户："研究 GaN 的热导率"

1. Deep Research Agent: 搜索 GaN 热导率相关文献 → 生成文献综述
2. Database Agent: 查询 GaN 结构 → 获取 CIF 文件
3. Simulation Agent: 弛豫结构 → 计算热导率 → 计算能量属性
4. 整合结果: 文献背景 + 结构信息 + 计算结果
```

### 示例 2：文献调研

```
用户："搜索量子计算相关的论文并生成报告"

1. 规划搜索词
2. 综合检索（ArXiv + Tavily）
3. 批量分析论文
4. 生成研究报告
5. 向量化存储（可选）
```

### 示例 3：材料计算

```
用户："生成 GaN 结构并计算声子谱"

1. 生成 GaN 晶体结构
2. 结构弛豫（必须）
3. 计算声子谱
4. 展示声子色散图和态密度
```

## 📁 项目结构

```
ResearchMind/
├── agents/                      # AI Agents
│   ├── deep_research/          # 文献研究 Agent
│   │   ├── agent.py            # Agent 实现
│   │   ├── prompts.py          # 提示词
│   │   ├── README.md           # 文档
│   │   └── ARCHITECTURE.md     # 架构说明
│   ├── database_agent/         # 数据库检索 Agent
│   │   ├── agent.py
│   │   ├── README.md
│   │   └── ARCHITECTURE.md
│   └── simulation_agent/       # 仿真计算 Agent
│       ├── agent.py
│       ├── prompts.py
│       ├── README.md
│       └── ARCHITECTURE.md
├── mcp_servers/                # MCP Servers
│   ├── paper_search/           # 文献检索 Server (14 tools)
│   │   ├── server.py
│   │   ├── modules/            # 功能模块
│   │   ├── README.md
│   │   └── ARCHITECTURE.md
│   ├── database_call/          # 数据库查询 Server (8 tools)
│   │   ├── server.py
│   │   ├── README.md
│   │   └── ARCHITECTURE.md
│   └── simulation/             # 仿真计算 Server (8 tools)
│       ├── server.py
│       ├── modules/            # 功能模块
│       ├── crystallm/          # CrystaLLM 模块
│       ├── kappa_lib/          # AI4Kappa 模块
│       ├── README.md
│       └── ARCHITECTURE.md
├── ui/                         # Web UI (React + TypeScript)
│   ├── src/
│   ├── package.json
│   └── README.md
├── README.md                   # 项目文档（本文件）
├── INTRO.md                    # 项目简介
└── pyproject.toml              # Python 项目配置
```

## 🛠️ 技术栈

### 核心框架
- **Google ADK (Agent Development Kit)**: AI Agent 开发框架
- **FastMCP**: MCP Server 开发框架
- **SSE (Server-Sent Events)**: Agent 与 Server 通信协议

### AI 模型
- **Gemini 2.0 Flash**: Google 最新的多模态大语言模型
- **CrystaLLM**: 晶体结构生成模型
- **AI4Kappa**: 热导率计算模型（Kappa-P/Kappa-MTP）
- **MatterSim**: 能量属性和声子谱计算模型

### 数据库
- **ChromaDB**: 向量数据库，用于论文全文存储和语义搜索
- **Materials Project**: 材料数据库
- **OQMD**: 开放量子材料数据库
- **COD**: 晶体学开放数据库
- **AFLOW**: 自动流程材料数据库

### 搜索引擎
- **ArXiv API**: 学术预印本搜索
- **Tavily API**: 学术和网页搜索

### 开发工具
- **UV**: Python 包管理工具
- **Structlog**: 结构化日志
- **Uvicorn**: ASGI 服务器
- **React + TypeScript**: UI 开发
- **Vite**: 前端构建工具

## 📖 文档

### 架构文档
- **系统架构**: [ARCHITECTURE.md](./ARCHITECTURE.md) - 完整系统架构详解
- **Agents 架构**: [agents/ARCHITECTURE.md](./agents/ARCHITECTURE.md)
- **Services 架构**: [services/ARCHITECTURE.md](./services/ARCHITECTURE.md)
- **UI 架构**: [ui/ARCHITECTURE.md](./ui/ARCHITECTURE.md)

### 使用文档
- **项目简介**: [INTRO.md](./INTRO.md)
- **Agents 文档**: [agents/README.md](./agents/README.md)
- **Services 文档**: [services/README.md](./services/README.md)
- **UI 文档**: [ui/README.md](./ui/README.md)

### Agent 文档
- **Deep Research Agent**: [agents/deep_research/README.md](./agents/deep_research/README.md)
- **Database Agent**: [agents/database_agent/README.md](./agents/database_agent/README.md)
- **Simulation Agent**: [agents/simulation_agent/README.md](./agents/simulation_agent/README.md)

### MCP Server 文档
- **Paper Search Server**: [mcp_servers/paper_search/README.md](./mcp_servers/paper_search/README.md)
- **Database Server**: [mcp_servers/database_call/README.md](./mcp_servers/database_call/README.md)
- **Simulation Server**: [mcp_servers/simulation/README.md](./mcp_servers/simulation/README.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。
