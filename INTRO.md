# ResearchMind V2

## 项目简介

**ResearchMind V2** 是一个基于 Google ADK 和 MCP (Model Context Protocol) 的智能材料科学研究助手系统。它通过协调多个专业 AI Agent 和 MCP Server，为材料科学研究人员提供从文献调研、数据库检索到仿真计算的一站式研究解决方案。

## 核心特性

### 🔬 全流程研究支持
- **文献调研**：多源检索（ArXiv + Tavily）、智能分析、报告生成
- **数据库检索**：查询多个材料数据库（Materials Project, OQMD, COD, AFLOW）
- **仿真计算**：晶体结构生成、热导率计算、能量属性预测、声子谱计算

### 🤖 智能多 Agent 协作
- **Deep Research Agent**：专注于学术文献检索和分析
- **Database Agent**：专注于材料数据库查询和结构获取
- **Simulation Agent**：专注于计算模拟和性能预测

### 🔌 模块化 MCP 架构
- **Paper Search MCP Server**：提供 14 个文献检索和分析工具
- **Database MCP Server**：提供多数据库查询和结构获取工具
- **Simulation MCP Server**：提供结构生成、弛豫、声子谱、热导率、能量计算工具

### 💾 持久化向量存储
- 支持将论文全文向量化存储到 ChromaDB
- 支持基于向量相似度的语义搜索
- 支持长期追问和知识积累

## 技术栈

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

## 系统架构

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
│  │ 14 Tools     │  │ 8 Tools      │  │ 8 Tools      │     │
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

## 核心功能

### 1. 文献研究 (Deep Research Agent)
- **多源检索**：默认使用 `search_papers_all_sources` 综合检索 ArXiv + Tavily
- **智能分析**：批量分析论文，生成中文摘要和关键信息
- **报告生成**：基于多篇论文生成综合研究报告（IEEE/Nature/ArXiv 格式）
- **向量化存储**：将论文全文向量化存储到 ChromaDB
- **语义搜索**：支持自然语言追问文献内容
- **汇总表格**：将论文列表保存为 Excel 表格

### 2. 数据库检索 (Database Agent)
- **多数据库查询**：查询 Materials Project, OQMD, COD, AFLOW
- **结构获取**：获取晶体结构（CIF 格式）
- **属性查询**：查询材料属性（能带隙、形成能、密度等）
- **自动生成**：数据库查询失败时自动调用 Simulation Agent 生成结构

### 3. 仿真计算 (Simulation Agent)
- **晶体结构生成**：使用 CrystaLLM 从化学式生成 CIF 结构
- **结构弛豫**：使用 MatterSim 优化晶体结构
- **声子谱计算**：计算声子色散和声子态密度（必须先弛豫）
- **热导率计算**：使用 AI4Kappa 计算热导率（Kappa-P/Kappa-MTP）
- **能量属性**：计算形成能、分解能、受力、应力

## 使用场景

### 场景 1：完整研究流程
```
用户："研究 GaN 的热导率"

1. Deep Research Agent: 搜索 GaN 热导率相关文献 → 生成文献综述
2. Database Agent: 查询 GaN 结构 → 获取 CIF 文件
3. Simulation Agent: 弛豫结构 → 计算热导率 → 计算能量属性
4. 整合结果: 文献背景 + 结构信息 + 计算结果
```

### 场景 2：文献调研
```
用户："搜索量子计算相关的论文并生成报告"

1. 规划搜索词
2. 综合检索（ArXiv + Tavily）
3. 批量分析论文
4. 生成研究报告
5. 向量化存储（可选）
```

### 场景 3：材料计算
```
用户："生成 GaN 结构并计算声子谱"

1. 生成 GaN 晶体结构
2. 结构弛豫（必须）
3. 计算声子谱
4. 展示声子色散图和态密度
```

## 快速开始

### 安装依赖
```bash
uv sync
```

### 启动 MCP Servers
```bash
# Paper Search MCP Server (端口 50001)
uv run python mcp_servers/paper_search/server.py --port 50001

# Database MCP Server (端口 50002)
uv run python mcp_servers/database_call/server.py --port 50002

# Simulation MCP Server (端口 5003)
uv run python mcp_servers/simulation/server.py
```

### 启动 Agents
```bash
# 启动 Deep Research Agent
uv run python agents/deep_research/agent.py

# 启动 Database Agent
uv run python agents/database_agent/agent.py

# 启动 Simulation Agent
uv run python agents/simulation_agent/agent.py
```

### 启动 UI
```bash
cd ui
npm install
npm run dev
```

## 项目结构

```
ResearchMind_V2/
├── agents/                      # AI Agents
│   ├── deep_research/          # 文献研究 Agent
│   ├── database_agent/         # 数据库检索 Agent
│   └── simulation_agent/       # 仿真计算 Agent
├── mcp_servers/                # MCP Servers
│   ├── paper_search/           # 文献检索 Server (14 tools)
│   ├── database_call/          # 数据库查询 Server (8 tools)
│   └── simulation/             # 仿真计算 Server (8 tools)
├── ui/                         # Web UI (React + TypeScript)
├── README.md                   # 项目文档
├── INTRO.md                    # 项目简介（本文件）
└── pyproject.toml              # Python 项目配置
```

## 文档

- **项目简介**: [INTRO.md](./INTRO.md)（本文件）
- **项目文档**: [README.md](./README.md)
- **Agents 文档**: [agents/README.md](./agents/README.md)
- **Deep Research Agent**: [agents/deep_research/README.md](./agents/deep_research/README.md)
- **Database Agent**: [agents/database_agent/README.md](./agents/database_agent/README.md)
- **Simulation Agent**: [agents/simulation_agent/README.md](./agents/simulation_agent/README.md)
- **Paper Search Server**: [mcp_servers/paper_search/README.md](./mcp_servers/paper_search/README.md)
- **Database Server**: [mcp_servers/database_call/README.md](./mcp_servers/database_call/README.md)
- **Simulation Server**: [mcp_servers/simulation/README.md](./mcp_servers/simulation/README.md)

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。

