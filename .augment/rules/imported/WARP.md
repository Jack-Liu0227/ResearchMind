---
type: "manual"
---

# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

ResearchMind is a multi-agent AI research assistant system built on Google's Agent Development Kit (ADK). It uses a **decentralized agent architecture** where specialized agents (literature, database, simulation) communicate directly with the frontend through a FastAPI communication layer. The system leverages DeepSeek-Chat as the default LLM and implements the Model Context Protocol (MCP) for tool integration.

## Commands

### Setup and Environment
```powershell
# Install dependencies (recommended package manager: uv)
uv sync

# Install with development dependencies
uv sync --extra dev

# Frontend dependencies (Node.js 16+)
cd ui && npm install && cd ..

# Environment setup
Copy-Item .env.example .env  # Windows PowerShell
# Edit .env with API keys (GOOGLE_API_KEY, DEEPSEEK_API_KEY)
```

### Development Commands
```powershell
# Start backend server (FastAPI + WebSocket) - use conda Python for Google ADK
python communication/api_server.py

# Start frontend development server
cd ui && npm run dev

# Run enhanced MCP servers (optional)
python mcp_servers/paper_search/server.py  # Enhanced with PDF extraction
python mcp_servers/materials/server.py
python mcp_servers/simulation/server.py
```

### Testing and Code Quality
```powershell
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=researchmind --cov=agents --cov=mcp_servers --cov=communication

# Code formatting
uv run black . && uv run isort .

# Type checking
uv run mypy .

# Linting
uv run flake8

# Frontend linting and type checking
cd ui && npm run lint && npm run type-check
```

### Single Test Execution
```powershell
# Run specific test file
uv run pytest tests/test_agents.py

# Run specific test function
uv run pytest tests/test_agents.py::test_literature_agent

# Run with verbose output
uv run pytest -v tests/test_specific.py
```

## Architecture Overview

### Multi-Agent System (Decentralized)
- **Root Agent**: Research coordinator that delegates to specialized agents
- **Deep Research Agent**: **ENHANCED** 4-stage literature research workflow:
  - 🔍 **Stage 1**: Classification Agent - analyzes research requests and determines approach
  - 📋 **Stage 2**: Planning Agent - creates structured research plans with search strategy
  - 🔬 **Stage 3**: Research Agent - executes literature search with advanced MCP tools
  - 📊 **Stage 4**: Analysis Agent - synthesizes findings and generates insights
- **Database Agent**: Materials database queries (Materials Project, OQMD, JARVIS)
- **Simulation Agent**: Computational simulation setup (VASP, Gaussian, LAMMPS)

Each agent operates independently using Google ADK framework with DeepSeek-Chat as the LLM.

### Communication Layer
- **FastAPI Server** (`communication/api_server.py`): REST API and WebSocket endpoints
- **WebSocket Server** (`communication/websocket_server.py`): Real-time bidirectional communication
- **Frontend**: React + TypeScript with Vite build system

### Tool Integration (MCP)
The system uses Model Context Protocol servers in `mcp_servers/`:
- `paper_search/`: **ENHANCED** ArXiv and academic paper search tools:
  - 🔍 `search_arxiv_direct`: Fast direct API search with feedparser
  - 📄 `get_arxiv_paper_content`: Full PDF text extraction and analysis
  - 📊 `analyze_paper_content`: Content analysis (summary, keywords, methodology)
  - 🔄 `batch_paper_analysis`: Bulk processing of multiple papers
  - 💾 `search_papers_by_author`: Author-based paper discovery
- `materials/`: Materials database integration tools  
- `simulation/`: Simulation engine interfaces
- `data_analysis/`, `rdkit/`, `structure_generate/`: Additional specialized tools

### Frontend Architecture
- **React 18** with TypeScript and Tailwind CSS
- **Vite** for development and build tooling
- **WebSocket client** for real-time agent communication
- **Component structure**: Dashboard, Chat interface, Agent-specific views

## Key Integration Points

### Agent-Tool Communication
Agents communicate with MCP servers using the standardized MCP protocol. Each agent has specific tools registered via `AgentTool(agent=...)` in the main coordinator.

### Frontend-Backend Communication
- REST endpoints at `/api/*` for CRUD operations
- WebSocket at `/ws/{client_id}` for real-time messaging
- CORS configured for `localhost:5173` (frontend dev server)

### Configuration Management
- `pyproject.toml`: Python dependencies and project metadata
- `.env`: Environment variables (API keys, model configurations)
- `communication/config.py`: Server configuration settings
- `ui/vite.config.ts`: Frontend build and proxy configuration

## Important File Locations

### Core Agent Files
- `agents/agent.py`: Main research coordinator agent
- `agents/deep_research/agent.py`: Literature research agent
- `agents/database_agent/agent.py`: Database search agent
- `agents/simulation_agent/agent.py`: Simulation management agent

### API and Communication
- `communication/api_server.py`: Main FastAPI application with REST endpoints
- `communication/websocket_server.py`: WebSocket connection management
- `communication/config.py`: Server configuration and settings

### Frontend Components
- `ui/src/App.tsx`: Main React application with routing
- `ui/src/services/websocket.tsx`: WebSocket service provider
- `ui/src/components/`: React components (Dashboard, Chat, etc.)

## Development Notes

### Model Configuration
The system defaults to DeepSeek-Chat but supports multiple LLM providers. Model selection is controlled via the `MODEL_USE` environment variable in the format `provider/model-name`.

### MCP Server Development
When adding new tools, create MCP servers following the pattern:
```python
from fastmcp import FastMCP
app = FastMCP("server-name")

@app.tool
def tool_function(param: str) -> str:
    return f"Result: {param}"
```

### Agent Extension
New agents should extend the Google ADK `LlmAgent` class and register tools via `AgentTool` instances.

### Environment Requirements
- Python 3.10+
- Node.js 16+
- **Google ADK**: Available in conda environment (`pip install google-adk>=1.15.0`)
- **UV package manager**: For frontend dependencies and non-ADK components
- **Conda/Miniconda**: Recommended for Google ADK and backend development
- API keys for: Google (ADK), DeepSeek (default LLM), optional: OpenAI, Anthropic

## Smart User Experience 

### 🤖 智能意图识别
- **直接响应**：不再需要繁琐的确认流程
- **智能分类**：自动识别用户意图类型：
  - `simple_greeting`: 友好欢迎信息和功能介绍
  - `research_request`: 直接开始文献研究（无需确认）
  - `general_conversation`: 礼貌引导到研究话题
  - `negative_response`: 优雅告别

### ⚙️ 流程优化
- **去除确认步骤**：用户说“我想研究”时立即开始
- **上下文识别**：根据对话历史进行智能判断
- **自然交互**：更像真人助手，少像机器人

### 🇨🇳 中文支持
- **所有回复都使用中文**，提供友好的中文交互体验
- 所有代理和子系统都使用中文进行沟通
- 修复了 ADK Session.messages 属性错误

### 📊 Enhanced Capabilities
- **4-stage research workflow** with progress tracking
- **Advanced PDF processing** capabilities  
- **Direct ArXiv API integration** for faster searches
- **Content analysis** and batch processing
- **Enhanced error handling** and logging

## Service URLs
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws/{client_id}
