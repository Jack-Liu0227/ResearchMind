---
type: "manual"
---

# 🧠 ResearchMind - AI-Powered Research Assistant

> A multi-agent research support system based on Google Agent Development Kit (ADK)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285f4.svg)](https://github.com/google/generative-ai-docs)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB.svg)](https://react.dev/)

ResearchMind is an intelligent research assistant system that leverages Google's Agent Development Kit (ADK) to provide comprehensive AI-powered support for researchers, including literature review, database search, simulation, and experimental design.

## ✨ Key Features

### 🤖 Multi-Agent System
- **📚 Literature Agent**: Literature research and analysis with paper search capabilities
- **🗜️ Database Agent**: Materials database search and data retrieval
- **⚛️ Simulation Agent**: Computational simulation and molecular modeling


### 🏗️ Technical Architecture
- **Backend**: Google ADK agents with FastAPI integration
- **Frontend**: React + TypeScript + Tailwind CSS for modern UI
- **Communication**: WebSocket-based real-time communication layer
- **MCP Servers**: Modular tool servers for specialized functionalities
  - Paper search and literature tools
  - Materials database integration
  - Simulation engines
  - Data analysis tools

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Node.js 16+ (for frontend)
- UV package manager (recommended) or pip

### Installation

#### 1. Clone the repository
```bash
git clone https://github.com/your-username/ResearchMind.git
cd ResearchMind
```

#### 2. Install UV (Python package manager)
```bash
# Windows PowerShell:
iwr -Uri https://astral.sh/uv/install.ps1 | iex

# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 3. Set up Python environment
```bash
# Install Python dependencies
uv sync

# Or with development dependencies
uv sync --extra dev
```

#### 4. Set up frontend (optional for UI)
```bash
cd ui
npm install
cd ..
```

#### 5. Configure environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys and configuration
# Required: GOOGLE_API_KEY for ADK agents
```

### Running the System

#### 🚀 一键启动（推荐）

**方式1: Python脚本启动（推荐，跨平台）**
```bash
# 简化版快速启动
python run.py

# 完整功能启动（支持更多选项）
python start_all.py

# 查看帮助
python start_all.py --help
```

**方式2: Windows批处理文件**
```bash
# Windows用户可以直接双击运行
start.bat
```

**方式3: PowerShell脚本（Windows）**
```powershell
# Windows PowerShell
.\start_all.ps1

# 跳过依赖安装
.\start_all.ps1 -SkipInstall
```

#### 🔧 手动启动

**1. Backend Communication Server**
```bash
# Start the main FastAPI server
uv run python communication/api_server.py
```

**2. MCP Tool Servers (Optional)**
```bash
# Start specific MCP servers as needed
uv run python mcp_servers/paper_search/server.py
uv run python mcp_servers/materials/server.py
uv run python mcp_servers/simulation/server.py
```

**3. Frontend (React UI)**
```bash
cd ui
npm install
npm run dev
```

#### 🌐 Access Points
- **Frontend UI**: http://localhost:5173
- **Communication API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **WebSocket**: ws://localhost:8000/ws/{client_id}

## 📁 Project Structure

```
ResearchMind/
├── agents/                   # 🤖 Google ADK Agents
│   ├── literature_agent/    # Literature research agent
│   ├── database_agent/      # Database search agent
│   ├── simulation_agent/    # Simulation and modeling agent
│   ├── agent.py    
│   ├── __init__.py            # Base agent class
│   └── config.py           # Agent configuration
├── mcp_servers/             # 🔧 MCP Tool Servers
│   ├── paper_search/        # ArXiv and literature search
│   ├── materials/           # Materials database server
│   ├── simulation/          # Simulation tools
│   ├── data_analysis/       # Data analysis tools
│   ├── experiment/          # Experiment design tools
│   ├── rdkit/              # Chemistry toolkit
│   └── structure_generate/  # Structure generation
├── ui/                      # 🎨 React Frontend
│   ├── src/                 # Source code
│   ├── package.json        # Dependencies
│   └── vite.config.ts      # Build configuration
├── communication/           # 📡 Communication Layer
│   ├── api_server.py       # FastAPI server
│   ├── websocket_server.py # WebSocket handler
│   ├── client.py           # Client utilities
│   ├── server.py           # Server utilities
│   └── config.py           # Configuration
├── docs/                    # 📚 Documentation
│   ├── en/                  # English docs
│   └── zh/                  # Chinese docs
├── .env.example             # Environment variables template
├── pyproject.toml           # Python project configuration
├── ARCHITECTURE.md          # System architecture
└── README.md                # This file
```

## 🎯 System Capabilities

### Research Tasks
- **Literature Review**: Automated paper search, analysis, and summarization
- **Database Search**: Query materials databases for properties and structures
- **Simulation Setup**: Configure and run molecular dynamics and DFT calculations
- **Data Analysis**: Process experimental data with ML models
- **Report Generation**: Create structured research reports

### Supported Databases & Tools
- **Literature**: ArXiv, Google Scholar, PubMed
- **Materials**: Materials Project, OQMD, JARVIS
- **Simulation**: VASP, Gaussian, LAMMPS interfaces
- **Chemistry**: RDKit for molecular analysis

## ��️ Development

### Agent Development

Agents are built using Google's ADK framework. To create a new agent:

```python
# agents/your_agent/agent.py
from typing import List
from google_adk import Agent, Tool

class YourAgent(Agent):
    """Your custom agent implementation"""
    
    def __init__(self):
        super().__init__(name="your_agent")
        self.tools = self.load_tools()
    
    def load_tools(self) -> List[Tool]:
        # Define your agent's tools
        pass
```

### MCP Server Development

MCP servers provide specialized tools. Create a new server:

```python
# mcp_servers/your_server/server.py
from fastmcp import FastMCP

app = FastMCP("your-server")

@app.tool
def your_tool(param: str) -> str:
    """Your tool implementation"""
    return f"Result: {param}"
```

### Frontend Components

The UI is built with React and TypeScript:

```typescript
// ui/src/components/YourComponent.tsx
import React from 'react';

export const YourComponent: React.FC = () => {
    return <div>Your Component</div>;
};
```

## 🔍 API Documentation

### WebSocket API

Connect to `ws://localhost:8000/ws/{client_id}` for real-time communication.

**Message Format:**
```json
{
  "type": "query",
  "agent": "literature_agent",
  "task": "search_papers",
  "params": {
    "query": "quantum computing",
    "limit": 10
  }
}
```

### REST API Endpoints

- `GET /api/health` - System health check
- `GET /api/agents` - List available agents
- `POST /api/task` - Submit a research task
- `GET /api/results/{task_id}` - Get task results

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Python: Black formatter, isort for imports
- TypeScript: Prettier with ESLint
- Commit messages: Conventional Commits

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

Developed by the ResearchMind Team.

## 🙏 Acknowledgments

- Google for the Agent Development Kit
- The MCP community for protocol standards
- All contributors and users of ResearchMind

## 💬 Contact

- GitHub Issues: [Report bugs or request features](https://github.com/your-username/ResearchMind/issues)
- Email: contact@researchmind.ai

---

<p align="center">
  Made with ❤️ for the research community
</p>

# 启动服务
uv run python simple_server.py

# 或指定主机和端口
HOST=0.0.0.0 PORT=8000 uv run python simple_server.py
```

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 🙏 致谢

- Google ADK团队提供的智能体框架
- Model Context Protocol标准
- 开源社区的贡献和支持

