# ResearchMind System Architecture

> 智能材料科学研究助手系统 - 完整架构文档

## 📖 系统概览

ResearchMind 是一个基于 Google ADK (Agent Development Kit) 和 MCP (Model Context Protocol) 的智能材料科学研究助手系统。它采用分层架构设计，通过协调多个专业 AI Agent 和 MCP Server，为材料科学研究人员提供从文献调研、数据库检索到仿真计算的一站式研究解决方案。

## 🏗️ 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Interface (UI)                         │
│                    (React + TypeScript + Vite)                      │
│                         Port: 5173                                  │
│                                                                     │
│  Features:                                                          │
│  - 晶体结构3D查看器 (Three.js)                                       │
│  - CSV/Markdown文件查看器                                           │
│  - 声子谱可视化                                                      │
│  - 拖拽调整布局                                                      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ (WebSocket + HTTP)
┌─────────────────────────────────────────────────────────────────────┐
│                         Backend Services                            │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐               │
│  │  WebSocket Server    │  │    HTTP Server       │               │
│  │  Port: 8001          │  │    Port: 8000        │               │
│  │                      │  │                      │               │
│  │  - Client管理        │  │  - REST API          │               │
│  │  - 消息路由          │  │  - 文件上传/下载      │               │
│  │  - Session管理       │  │  - 静态文件服务       │               │
│  └──────────────────────┘  └──────────────────────┘               │
│                                │                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Agent Coordinator                               │  │
│  │  - Google ADK Runner                                         │  │
│  │  - Session Service (InMemorySessionService)                  │  │
│  │  - Message Handler                                           │  │
│  │  - Data Processor                                            │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Research Coordinator Agent                        │
│                  (agents/agent.py - LlmAgent)                       │
│                                                                     │
│  Model: gemini/gemini-2.5-flash (LiteLLM)                          │
│  Prompt: RESEARCH_COORDINATOR_PROMPT                               │
│                                                                     │
│  Tools: [AgentTool(deep_research),                                 │
│          AgentTool(database),                                      │
│          AgentTool(simulation)]                                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Deep Research    │  │   Database       │  │   Simulation     │
│     Agent        │  │    Agent         │  │     Agent        │
│                  │  │                  │  │                  │
│ (Google ADK      │  │ (Google ADK      │  │ (Google ADK      │
│  Agent)          │  │  Agent)          │  │  Agent)          │
│                  │  │                  │  │                  │
│ Tools:           │  │ Tools:           │  │ Tools:           │
│ - MCPToolset     │  │ - MCPToolset     │  │ - MCPToolset     │
│   (17 tools)     │  │   (8 tools)      │  │   (8 tools)      │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                       │                       │
        ▼ (SSE)                 ▼ (SSE)                 ▼ (SSE)
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Paper Search     │  │ Materials DB     │  │  Simulation      │
│  MCP Server      │  │  MCP Server      │  │  MCP Server      │
│                  │  │                  │  │                  │
│ Port: 50001      │  │ Port: 5002       │  │ Port: 5003       │
│ Protocol: SSE    │  │ Protocol: SSE    │  │ Protocol: SSE    │
│                  │  │                  │  │                  │
│ Tools: 17        │  │ Tools: 8         │  │ Tools: 8         │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ External APIs    │  │ External APIs    │  │ ML Models        │
│                  │  │                  │  │                  │
│ - ArXiv API      │  │ - Materials      │  │ - CrystaLLM      │
│ - Tavily API     │  │   Project API    │  │ - AI4Kappa       │
│ - ChromaDB       │  │ - OQMD API       │  │ - MatterSim      │
│                  │  │ - COD API        │  │                  │
│                  │  │ - AFLOW API      │  │                  │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## 🔧 核心组件详解

### 1. Frontend (UI)

**技术栈**:

- React 18 + TypeScript
- Vite (构建工具)
- TailwindCSS (样式)
- Three.js (3D渲染)
- ReactMarkdown (Markdown渲染)

**核心功能**:

- **晶体结构查看器**: 3D可视化晶体结构（40+种元素颜色）
- **文件查看器**: CSV表格查看器、Markdown文档查看器
- **声子谱可视化**: 显示声子色散和态密度图
- **拖拽布局**: 左右侧边栏可拖拽调整大小
- **实时通信**: WebSocket连接，实时接收Agent响应

**文件结构**:

```
ui/
├── src/
│   ├── components/          # React组件
│   │   ├── ChatInterface.tsx
│   │   ├── StructureViewerThreeJS.tsx
│   │   ├── FileViewer/      # CSV/MD查看器
│   │   ├── RightPanel.tsx
│   │   └── Layout.tsx
│   ├── pages/               # 页面
│   ├── services/            # WebSocket服务
│   ├── store/               # Zustand状态管理
│   └── types/               # TypeScript类型定义
└── package.json
```

### 2. Backend Services

**技术栈**:

- Python 3.11+
- FastAPI (HTTP Server)
- WebSockets (实时通信)
- Google ADK (Agent框架)

**核心服务**:

#### 2.1 WebSocket Server (`services/websocket_server.py`)

- **端口**: 8002
- **功能**:
  - 管理客户端连接
  - 路由消息到Agent Coordinator
  - 维护Session状态
  - 实时推送Agent响应

#### 2.2 HTTP Server (`services/http_server.py`)

- **端口**: 8000
- **功能**:
  - REST API端点
  - 文件上传/下载
  - 静态文件服务（图片、CSV、MD）
  - CIF文件解析

#### 2.3 Agent Coordinator (`services/agent_coordinator.py`)

- **功能**:
  - 协调Google ADK Agents
  - 管理Session Service
  - 运行Google ADK Runner
  - 处理Agent事件流

#### 2.4 Message Handler (`services/message_handler.py`)

- **功能**:
  - 处理WebSocket消息
  - 路由到不同的Agent
  - 处理文件上传
  - 发送响应消息

#### 2.5 Data Processor (`services/data_processor.py`)

- **功能**:
  - 处理Agent响应数据
  - 提取文件链接
  - 转换数据格式
  - 发送文件元数据

### 3. Google ADK Agents

#### 3.1 Research Coordinator Agent (`agents/agent.py`)

- **类型**: `LlmAgent`
- **模型**: `gemini/gemini-2.5-flash`
- **职责**:
  - 接收用户请求
  - 智能分析请求类型
  - 决策调用哪个子Agent
  - 协调多个子Agent完成复杂任务
  - 整合结果并返回

**工具**:

```python
tools=[
    AgentTool(agent=literature_agent),
    AgentTool(agent=database_agent),
    AgentTool(agent=simulation_agent),
]
```

#### 3.2 Deep Research Agent (`agents/deep_research/agent.py`)

- **类型**: `Agent`
- **模型**: `gemini/gemini-2.5-flash`
- **职责**:
  - 文献检索（ArXiv + Tavily）
  - 论文分析和总结
  - 生成研究报告
  - 向量化存储和语义搜索

**工具**: MCPToolset (17个工具)

- 规划: `generate_research_plan`
- 检索: `search_papers`, `search_arxiv_papers`, `tavily_search`等
- 分析: `batch_paper_analysis`
- 报告: `generate_research_report`
- 向量化: `ingest_papers_to_vector_store`, `semantic_search_papers`

#### 3.3 Database Agent (`agents/database_agent/agent.py`)

- **类型**: `Agent`
- **模型**: `gemini/gemini-2.5-flash`
- **职责**:
  - 查询多个材料数据库
  - 获取晶体结构和材料属性
  - 自动结构生成（数据库查询失败时）

**工具**: MCPToolset (8个工具)

- `materials_project_query_tool`
- `get_oqmd_phases`
- `search_cod_by_formula`
- `get_aflow_data`
- `batch_database_search`
- 等

#### 3.4 Simulation Agent (`agents/simulation_agent/agent.py`)

- **类型**: `Agent`
- **模型**: `gemini/gemini-2.5-flash`
- **职责**:
  - 晶体结构生成（CrystaLLM）
  - 结构弛豫（MatterSim）
  - 声子谱计算（MatterSim）
  - 热导率计算（AI4Kappa）
  - 能量属性预测（MatterSim）

**工具**: MCPToolset (8个工具)

- `generate_crystal_structure`
- `relax_structure`
- `calculate_phonon`
- `calculate_kappa_from_cif`
- `calculate_energy_from_cif`
- 等

### 4. MCP Servers

#### 4.1 Paper Search MCP Server (`mcp_servers/paper_search/server.py`)

- **端口**: 50001
- **协议**: SSE (Server-Sent Events)
- **工具数量**: 17个

**工具分类**:

1. **规划** (1个): `generate_research_plan`
2. **检索** (8个): ArXiv搜索、Tavily搜索、综合搜索
3. **内容获取** (2个): 获取论文全文
4. **分析** (2个): 批量分析、生成报告
5. **导出** (1个): 保存为CSV
6. **向量化** (2个): 向量存储、语义搜索
7. **健康检查** (1个): `health_check`

#### 4.2 Materials Database MCP Server (`mcp_servers/database_call/server.py`)

- **端口**: 5002
- **协议**: SSE
- **工具数量**: 8个

**支持的数据库**:

- Materials Project (MP)
- Open Quantum Materials Database (OQMD)
- Crystallography Open Database (COD)
- AFLOW

**工具列表**:

- `materials_project_query_tool`
- `get_oqmd_phases`
- `search_cod_by_formula`
- `get_aflow_data`
- `batch_database_search`
- `generate_and_compare_structures`
- `get_structure_recommendations`
- `health_check`

#### 4.3 Simulation MCP Server (`mcp_servers/simulation/server.py`)

- **端口**: 5003
- **协议**: SSE
- **工具数量**: 8个

**支持的模型**:

- CrystaLLM (结构生成)
- MatterSim (弛豫、声子谱、能量)
- AI4Kappa (热导率)

**工具列表**:

- `generate_crystal_structure`
- `extract_and_validate_cif`
- `relax_structure`
- `calculate_phonon`
- `calculate_kappa_from_cif`
- `calculate_energy_from_cif`
- `detect_file_upload`
- `health_check`

## 🔄 数据流

### 1. 用户请求流程

```
用户输入
  ↓
UI (React)
  ↓ WebSocket
WebSocket Server (Port 8002)
  ↓
Message Handler
  ↓
Agent Coordinator
  ↓
Research Coordinator Agent
  ↓ AgentTool
Sub-Agent (Deep Research / Database / Simulation)
  ↓ MCPToolset (SSE)
MCP Server (Paper Search / Database / Simulation)
  ↓
External API / ML Model
  ↓
返回结果
  ↓
Agent Coordinator
  ↓
WebSocket Server
  ↓ WebSocket
UI (React)
  ↓
显示结果
```

### 2. 文件处理流程

```
Agent生成文件 (CSV/MD/PNG)
  ↓
保存到本地 (mcp_servers/*/papers/ 或 mcp_servers/simulation/*)
  ↓
返回文件路径
  ↓
Data Processor提取文件链接
  ↓
发送file_metadata消息到前端
  ↓
前端自动展示文件 (CSV Viewer / MD Viewer / Image)
  ↓
用户可下载文件 (HTTP Server /api/download/)
```

## 📦 技术栈总结

### Frontend

- React 18
- TypeScript
- Vite
- TailwindCSS
- Three.js
- ReactMarkdown
- Zustand

### Backend

- Python 3.11+
- FastAPI
- WebSockets
- Google ADK
- LiteLLM

### MCP Servers

- FastMCP
- SSE (Server-Sent Events)
- Uvicorn

### External Services

- ArXiv API
- Tavily API
- Materials Project API
- OQMD API
- COD API
- AFLOW API
- ChromaDB

### ML Models

- CrystaLLM (结构生成)
- MatterSim (弛豫、声子谱、能量)
- AI4Kappa (热导率)

## 🚀 部署架构

### 开发环境

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Vite Dev Server)                                 │
│  http://localhost:5173                                      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend Services                                           │
│  - WebSocket Server: ws://localhost:8001                    │
│  - HTTP Server: http://localhost:8000                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  MCP Servers                                                │
│  - Paper Search: http://localhost:50001/sse                 │
│  - Database: http://localhost:5002/sse                      │
│  - Simulation: http://localhost:5003/sse                    │
└─────────────────────────────────────────────────────────────┘
```

### 启动顺序

1. **启动MCP Servers** (3个)

   ```bash
   # Terminal 1
   uv run python mcp_servers/paper_search/server.py

   # Terminal 2
   uv run python mcp_servers/database_call/server.py

   # Terminal 3
   uv run python mcp_servers/simulation/server.py
   ```
2. **启动Backend Services**

   ```bash
   # Terminal 4
   uv run python main.py
   ```
3. **启动Frontend**

   ```bash
   # Terminal 5
   cd ui
   npm run dev
   ```

## 📚 相关文档

- [README.md](./README.md) - 项目主文档
- [agents/ARCHITECTURE.md](./agents/ARCHITECTURE.md) - Agent架构文档
- [services/ARCHITECTURE.md](./services/ARCHITECTURE.md) - Services架构文档
- [ui/ARCHITECTURE.md](./ui/ARCHITECTURE.md) - UI架构文档
- [mcp_servers/paper_search/ARCHITECTURE.md](./mcp_servers/paper_search/ARCHITECTURE.md) - Paper Search MCP架构
- [mcp_servers/database_call/ARCHITECTURE.md](./mcp_servers/database_call/ARCHITECTURE.md) - Database MCP架构
- [mcp_servers/simulation/ARCHITECTURE.md](./mcp_servers/simulation/ARCHITECTURE.md) - Simulation MCP架构

## 📄 许可证

MIT License
