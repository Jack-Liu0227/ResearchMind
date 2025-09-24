# Get Started

ResearchMind is an intelligent research assistant powered by Google Agent Development Kit (ADK) and Model Context Protocol (MCP). It provides a comprehensive multi-agent system for scientific research, from literature review to experimental design.

## What is ResearchMind?

ResearchMind helps researchers:
- 🔍 **Conduct comprehensive literature reviews** using ArXiv, Google Scholar, and web search
- 🗄️ **Search materials databases** including Materials Project, OQMD, and NOMAD
- ⚛️ **Run multi-scale simulations** with MatterSim integration
- 🧪 **Design optimized experiments** using DOE and risk assessment
- 🤖 **Orchestrate complex workflows** through agent coordination

## Core Features

### 🏗️ Multi-Agent Architecture
- **Coordinator Agent**: Orchestrates research workflows and manages sub-agents
- **Literature Agent**: Specializes in academic paper search and analysis
- **Database Agent**: Expert in materials database queries and structure generation
- **Simulation Agent**: Handles computational modeling and property prediction
- **Experiment Agent**: Designs experiments and assesses risks

### 🔄 Intelligent Workflows
- **Hybrid Mode**: Automatically selects optimal strategy based on task complexity
- **Sequential Mode**: Step-by-step deep research (Literature→Database→Simulation→Experiment)
- **Parallel Mode**: Concurrent execution for rapid validation
- **Specialized Mode**: Domain-specific optimized workflows

### 🛠️ MCP Tool Ecosystem
- **Standardized Integration**: All tools follow Model Context Protocol standards
- **Modular Design**: Easy to extend with new tools and capabilities
- **Real-time Processing**: Asynchronous execution with live progress tracking
- **Error Handling**: Robust error recovery and fallback mechanisms

## Quick Navigation

| Section | Description | Time to Complete |
|---------|-------------|------------------|
| [Installation](#installation) | Set up ResearchMind environment | 5 minutes |
| [Quickstart](#quickstart) | Create your first research workflow | 10 minutes |
| [Agent Tutorial](#agent-tutorial) | Learn multi-agent coordination | 20 minutes |
| [MCP Tools](#mcp-tools) | Explore available research tools | 15 minutes |
| [Deployment](#deployment) | Deploy to production | 30 minutes |

## Installation

### Prerequisites
- Python 3.9 or higher
- Google ADK installed
- Git for version control

### Install ResearchMind

```bash
# Clone the repository
git clone https://github.com/your-org/researchmind.git
cd researchmind

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
export GOOGLE_API_KEY="your_google_api_key"
export MATERIALS_PROJECT_API_KEY="your_mp_api_key"  # Optional
export MATTERSIM_LICENSE="your_mattersim_license"   # Optional
```

### Verify Installation

```bash
# Run system tests
python test_agents.py

# Expected output:
# ✅ All tests passed! ResearchMind is ready!
```

## Quickstart

### 1. Interactive Mode (Recommended for beginners)

```bash
python main_mcp.py --interactive
```

Try these example queries:
- "Research lithium battery materials"
- "Find perovskite solar cell structures"
- "Design graphene synthesis experiment"

### 2. Direct Research Mode

```bash
# Hybrid workflow (recommended)
python main_mcp.py --research "superconducting materials" --workflow hybrid

# Sequential workflow for deep research
python main_mcp.py --research "quantum dots" --workflow sequential

# Parallel workflow for rapid exploration
python main_mcp.py --research "2D materials" --workflow parallel
```

### 3. Specialized Agent Mode

```bash
# Literature research expert
python main_mcp.py --agent literature_agent --research "machine learning in materials science"

# Database search expert
python main_mcp.py --agent database_agent --research "high entropy alloys"

# Simulation expert
python main_mcp.py --agent simulation_agent --research "electronic properties"

# Experiment design expert
python main_mcp.py --agent experiment_agent --research "catalyst synthesis"
```

### 4. Web Interface Mode

```bash
# Launch ADK web interface
python main_mcp.py --web --port 8080
```

Then open http://localhost:8080 in your browser and select the `research_coordinator` agent.

## Agent Tutorial

### Understanding Agent Hierarchy

ResearchMind uses a hierarchical multi-agent system:

```
Root Coordinator
├── Literature Agent (+ Literature Workflow)
├── Database Agent (+ Materials Discovery Workflow)
├── Simulation Agent (+ Computational Workflow)
├── Experiment Agent (+ Experimental Workflow)
└── Workflow Orchestrator
    ├── Sequential Workflow
    ├── Parallel Workflow
    ├── Hybrid Workflow
    └── Specialized Workflow
```

### Creating Custom Workflows

```python
from agents import literature_agent, database_agent, simulation_agent
from google.adk.agents.workflow_agents import SequentialAgent

# Create custom research pipeline
custom_workflow = SequentialAgent(
    name="materials_discovery_pipeline",
    instruction="Discover new materials through systematic research",
    agents=[literature_agent, database_agent, simulation_agent]
)
```

### Agent Communication

Agents communicate through:
- **Task Delegation**: Parent agents assign tasks to sub-agents
- **Result Aggregation**: Workflow agents collect and synthesize results
- **Context Sharing**: Shared memory and state management
- **Error Propagation**: Robust error handling across agent boundaries

## MCP Tools

### Literature Research Tools
- `search_arxiv`: Search ArXiv papers with advanced filtering
- `search_scholar`: Google Scholar integration with citation analysis
- `search_web`: Web search for broader research context
- `analyze_paper`: Extract methodologies and key findings
- `generate_report`: Create structured literature reviews

### Materials Database Tools
- `search_structure`: Query Materials Project, OQMD, NOMAD databases
- `generate_structure`: AI-driven structure generation using CrystaLLM
- `predict_properties`: Property prediction using ML models
- `validate_structure`: Stability and feasibility analysis
- `visualize_structure`: 3D structure visualization

### Simulation Tools
- `setup_calculation`: Configure computational parameters
- `run_mattersim`: Execute MatterSim calculations
- `analyze_results`: Process and interpret simulation data
- `optimize_structure`: Structure optimization workflows
- `calculate_properties`: Electronic, mechanical, thermal properties

### Experiment Design Tools
- `design_experiment`: Create experimental protocols
- `optimize_parameters`: Statistical optimization (DOE, Bayesian)
- `assess_risk`: Safety and feasibility assessment
- `generate_protocol`: Detailed experimental procedures
- `estimate_cost`: Resource and time estimation

## Next Steps

### Learn More
- [Agent Configuration](agent-config.md) - Customize agent behavior
- [MCP Integration](mcp-integration.md) - Add new tools and capabilities
- [Workflow Patterns](workflow-patterns.md) - Advanced orchestration techniques
- [Deployment Guide](deployment.md) - Production deployment strategies

### Sample Projects
- [Battery Materials Research](samples/battery-materials.md)
- [Catalyst Discovery](samples/catalyst-discovery.md)
- [2D Materials Exploration](samples/2d-materials.md)
- [Drug Discovery Pipeline](samples/drug-discovery.md)

### Community
- [GitHub Repository](https://github.com/your-org/researchmind)
- [Discussion Forum](https://github.com/your-org/researchmind/discussions)
- [Issue Tracker](https://github.com/your-org/researchmind/issues)
- [Contributing Guide](contributing.md)

---

Ready to accelerate your research? Start with the [Quickstart](#quickstart) or explore our [Sample Projects](samples/) to see ResearchMind in action!
