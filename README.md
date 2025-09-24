# ResearchMind - 智能科研助手 🧠

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Google ADK](https://img.shields.io/badge/Google-ADK-4285f4.svg)](https://google.github.io/adk-docs/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

> **构建"真实问题 → 工具开发 → 收益分成"的科研智能体生态系统**

ResearchMind是一个基于Google Agent Developer Kit (ADK)开发的下一代智能科研助手，采用多智能体架构和Model Context Protocol (MCP)工具生态，为科研工作者提供从文献调研到实验设计的全流程智能化支持。

## 🌟 核心特性

### 🔬 多智能体协作架构
基于Google ADK的多智能体系统设计，每个智能体专注特定领域：

- **📚 文献调研智能体 (LiteratureAgent)**: 多源检索、智能筛选、报告生成
- **🗄️ 数据库检索智能体 (DatabaseAgent)**: 材料数据库搜索、结构检索
- **⚛️ 仿真模拟智能体 (SimulationAgent)**: MatterSim集成、多尺度建模
- **🧪 实验设计智能体 (ExperimentAgent)**: 方案设计、参数优化
- **🎯 协调器智能体 (CoordinatorAgent)**: 任务分配、流程管理

### 🛠️ MCP工具生态系统
采用Model Context Protocol标准，构建可扩展的工具生态：

- **文献检索工具**: ArXiv、Google Scholar、Web Search MCP服务器
- **材料数据库工具**: Materials Project、OQMD、NOMAD MCP接口
- **仿真计算工具**: MatterSim、CrystaLLM MCP包装器
- **分析可视化工具**: 结构分析、性质预测、数据可视化

### 🚀 智能化工作流
支持多种科研工作模式：

- **Sequential Pipeline**: 文献调研 → 数据库检索 → 仿真验证 → 实验设计
- **Parallel Processing**: 并行文献检索、同时进行多种仿真计算
- **Iterative Refinement**: 基于反馈的迭代优化和改进
- **Human-in-the-Loop**: 关键节点的人工审核和决策

## 🏗️ 系统架构

### 多智能体层次结构
```
ResearchMind (Root Coordinator)
├── LiteratureAgent (文献调研)
│   ├── ArXiv MCP Server
│   ├── Scholar MCP Server
│   └── WebSearch MCP Server
├── DatabaseAgent (数据库检索)
│   ├── MaterialsProject MCP Server
│   ├── OQMD MCP Server
│   └── NOMAD MCP Server
├── SimulationAgent (仿真模拟)
│   ├── MatterSim MCP Server
│   ├── CrystaLLM MCP Server
│   └── Analysis MCP Server
└── ExperimentAgent (实验设计)
    ├── Design MCP Server
    ├── Optimization MCP Server
    └── Risk Assessment MCP Server
```

### MCP服务器架构
每个专业领域都有对应的MCP服务器，提供标准化的工具接口：

```python
# 示例：文献检索MCP服务器
@mcp_server.list_tools()
async def list_literature_tools():
    return [
        Tool(name="search_arxiv", description="搜索ArXiv论文"),
        Tool(name="search_scholar", description="搜索Google Scholar"),
        Tool(name="analyze_paper", description="分析论文内容"),
        Tool(name="generate_report", description="生成调研报告")
    ]
```

## 🔧 核心功能模块

### 📚 智能文献调研 (LiteratureAgent)
```python
# 多源检索与智能分析
literature_agent = LlmAgent(
    name="literature_researcher",
    instruction="专业文献调研和分析专家",
    tools=[
        MCPToolset(connection_params=arxiv_mcp_server),
        MCPToolset(connection_params=scholar_mcp_server),
        MCPToolset(connection_params=web_search_mcp_server)
    ]
)
```

**核心能力**:
- 🔍 **多源检索**: ArXiv、Google Scholar、Web Search并行搜索
- 🎯 **智能筛选**: 基于相关性和影响因子的论文排序
- 📄 **报告生成**: 自动生成结构化文献调研报告
- 💡 **方案提取**: 从文献中提取可行的研究方案
- 📤 **文献上传**: 支持PDF文献上传和深度分析

### 🗄️ 数据库检索与结构生成 (DatabaseAgent)
```python
# 材料数据库集成
database_agent = LlmAgent(
    name="database_specialist",
    instruction="材料数据库检索和结构生成专家",
    tools=[
        MCPToolset(connection_params=materials_project_mcp),
        MCPToolset(connection_params=crystallm_mcp_server),
        MCPToolset(connection_params=structure_analysis_mcp)
    ]
)
```

**核心能力**:
- 🔬 **结构检索**: Materials Project、OQMD、NOMAD数据库搜索
- ⚛️ **结构生成**: CrystaLLM驱动的新结构设计
- ✅ **结构验证**: 自动验证结构合理性和稳定性
- 📊 **性质预测**: 基于结构的材料性质预测

### ⚛️ 多尺度仿真模拟 (SimulationAgent)
```python
# MatterSim集成仿真
simulation_agent = LlmAgent(
    name="simulation_expert",
    instruction="多尺度仿真建模和计算专家",
    tools=[
        MCPToolset(connection_params=mattersim_mcp_server),
        MCPToolset(connection_params=analysis_mcp_server),
        MCPToolset(connection_params=visualization_mcp_server)
    ]
)
```

**核心能力**:
- 🧮 **通用势函数**: MatterSim原子级精确计算
- 📏 **多尺度建模**: 原子→分子→材料的跨尺度仿真
- 📈 **结果分析**: 自动分析能量、结构、动力学性质
- 📊 **可视化**: 3D结构和性质分布可视化

### 🧪 实验设计优化 (ExperimentAgent)
```python
# 智能实验设计
experiment_agent = LlmAgent(
    name="experiment_designer",
    instruction="实验方案设计和优化专家",
    tools=[
        MCPToolset(connection_params=design_mcp_server),
        MCPToolset(connection_params=optimization_mcp_server),
        MCPToolset(connection_params=risk_assessment_mcp)
    ]
)
```

**核心能力**:
- 🎯 **方案设计**: 基于文献和仿真的实验方案生成
- ⚙️ **参数优化**: 贝叶斯优化和机器学习参数调优
- ⚠️ **风险评估**: 实验可行性和安全性评估
- 📋 **协议生成**: 详细实验操作协议自动生成

## 🏗️ 技术架构

### 🔄 多智能体工作流模式

#### Sequential Pipeline (顺序流水线)
```mermaid
graph LR
    A[文献调研] --> B[数据库检索] --> C[仿真验证] --> D[实验设计]
```

#### Parallel Processing (并行处理)
```mermaid
graph TD
    A[用户需求] --> B[文献调研]
    A --> C[数据库检索]
    A --> D[仿真计算]
    B --> E[结果整合]
    C --> E
    D --> E
    E --> F[实验设计]
```

#### Iterative Refinement (迭代优化)
```mermaid
graph LR
    A[初始方案] --> B[仿真验证] --> C[结果评估] --> D{是否满足要求}
    D -->|否| E[方案优化] --> B
    D -->|是| F[最终方案]
```

### 🛠️ MCP服务器生态

#### 文献检索MCP服务器
```python
# literature_mcp_server.py
@app.list_tools()
async def list_literature_tools():
    return [
        Tool(name="search_arxiv", description="ArXiv论文搜索"),
        Tool(name="search_scholar", description="Google Scholar搜索"),
        Tool(name="analyze_paper", description="论文内容分析"),
        Tool(name="extract_methods", description="提取研究方法"),
        Tool(name="generate_report", description="生成调研报告")
    ]
```

#### 材料数据库MCP服务器
```python
# materials_mcp_server.py
@app.list_tools()
async def list_materials_tools():
    return [
        Tool(name="search_structure", description="搜索晶体结构"),
        Tool(name="predict_properties", description="预测材料性质"),
        Tool(name="generate_structure", description="生成新结构"),
        Tool(name="validate_structure", description="验证结构稳定性")
    ]
```

#### 仿真计算MCP服务器
```python
# simulation_mcp_server.py
@app.list_tools()
async def list_simulation_tools():
    return [
        Tool(name="setup_calculation", description="设置计算参数"),
        Tool(name="run_mattersim", description="运行MatterSim计算"),
        Tool(name="analyze_results", description="分析计算结果"),
        Tool(name="visualize_structure", description="结构可视化")
    ]
```

### 🔧 核心技术栈

| 层级 | 技术组件 | 说明 |
|------|----------|------|
| **智能体框架** | Google ADK | 多智能体协作平台 |
| **工具协议** | Model Context Protocol | 标准化工具接口 |
| **AI模型** | Gemini 2.0 Flash, GPT-4, Claude | 多模型支持 |
| **仿真引擎** | MatterSim, CrystaLLM | 原子级精确计算 |
| **数据库** | Materials Project, OQMD, NOMAD | 材料数据源 |
| **部署平台** | Cloud Run, GKE, Vertex AI | 云原生部署 |
| **监控运维** | Cloud Monitoring, Logging | 生产级监控 |

### 📁 新项目结构 (MCP架构)
```
ResearchMind/
├── agents/                          # ADK智能体定义
│   ├── __init__.py
│   ├── coordinator_agent.py         # 主协调器智能体
│   ├── literature_agent.py          # 文献调研智能体
│   ├── database_agent.py            # 数据库检索智能体
│   ├── simulation_agent.py          # 仿真模拟智能体
│   └── experiment_agent.py          # 实验设计智能体
├── mcp_servers/                     # MCP服务器实现
│   ├── __init__.py
│   ├── literature/                  # 文献检索MCP服务器
│   │   ├── __init__.py
│   │   ├── server.py               # 主服务器文件
│   │   ├── tools/                  # 工具实现
│   │   │   ├── arxiv_search.py
│   │   │   ├── scholar_search.py
│   │   │   ├── web_search.py
│   │   │   └── paper_analysis.py
│   │   └── requirements.txt
│   ├── materials/                   # 材料数据库MCP服务器
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── tools/
│   │   │   ├── materials_project.py
│   │   │   ├── crystallm_wrapper.py
│   │   │   └── structure_analysis.py
│   │   └── requirements.txt
│   ├── simulation/                  # 仿真计算MCP服务器
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── tools/
│   │   │   ├── mattersim_wrapper.py
│   │   │   ├── calculation_setup.py
│   │   │   └── result_analysis.py
│   │   └── requirements.txt
│   └── experiment/                  # 实验设计MCP服务器
│       ├── __init__.py
│       ├── server.py
│       ├── tools/
│       │   ├── design_optimizer.py
│       │   ├── risk_assessment.py
│       │   └── protocol_generator.py
│       └── requirements.txt
├── config/                          # 配置文件
│   ├── __init__.py
│   ├── agent_config.yaml           # 智能体配置
│   ├── mcp_config.yaml             # MCP服务器配置
│   └── deployment_config.yaml      # 部署配置
├── utils/                           # 通用工具
│   ├── __init__.py
│   ├── report_generator.py         # 报告生成器
│   ├── data_processor.py           # 数据处理器
│   └── visualization.py            # 可视化工具
├── tests/                           # 测试文件
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_mcp_servers/
│   └── integration_tests/
├── docs/                            # 文档
│   ├── README.md
│   ├── architecture.md
│   ├── deployment.md
│   └── api_reference.md
├── scripts/                         # 部署和运维脚本
│   ├── deploy_mcp_servers.sh
│   ├── start_development.sh
│   └── run_tests.sh
├── pyproject.toml                   # 项目配置和依赖 (uv)
├── uv.lock                         # 依赖锁定文件 (uv)
├── .python-version                 # Python版本指定
├── Makefile                        # 常用命令快捷方式
├── main_mcp.py                     # 主程序入口
└── test_agents.py                  # 系统测试脚本
```

## 🚀 快速开始

### 环境要求
- Python 3.9+
- [uv](https://docs.astral.sh/uv/) (推荐的Python包管理器)
- Git

### 安装步骤

1. **安装uv (如果尚未安装)**
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用pip
pip install uv
```

2. **克隆项目**
```bash
git clone https://github.com/your-org/researchmind.git
cd researchmind
```

3. **安装依赖 (uv会自动管理Python版本和虚拟环境)**
```bash
# 安装基础依赖
uv sync

# 或安装开发依赖
uv sync --extra dev

# 或安装所有依赖 (包括文档、Jupyter等)
uv sync --extra all
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑.env文件，填入必要的API密钥
```

5. **验证安装**
```bash
# 快速验证安装
uv run python scripts/verify_installation.py
# 或使用Makefile
make verify

# 运行完整测试
uv run python test_agents.py
# 或使用Makefile
make test
```

### 使用方式

#### 1. 交互式模式（推荐新手）
```bash
uv run python main_mcp.py --interactive
# 或使用Makefile
make run
```

#### 2. ADK Web界面（推荐开发者）
```bash
uv run python main_mcp.py --web --port 8080
# 或使用Makefile
make web
```
然后在浏览器中访问 http://localhost:8080，选择 `research_coordinator` 智能体。

#### 3. 命令行模式
```bash
# 智能混合工作流 (推荐)
uv run python main_mcp.py --research "锂电池材料研究" --workflow hybrid

# 顺序工作流 (深度研究)
uv run python main_mcp.py --research "钙钛矿太阳能电池" --workflow sequential

# 并行工作流 (快速研究)
python main_mcp.py --research "石墨烯应用" --workflow parallel

# 专项研究工作流
python main_mcp.py --research "超导材料" --workflow specialized
```

#### 4. 专业智能体模式
```bash
# 文献调研专家
uv run python main_mcp.py --agent literature_agent --research "超导材料文献调研"

# 数据库检索专家
uv run python main_mcp.py --agent database_agent --research "钙钛矿结构搜索"

# 仿真计算专家
uv run python main_mcp.py --agent simulation_agent --research "材料性质计算"

# 实验设计专家
uv run python main_mcp.py --agent experiment_agent --research "合成工艺设计"
```

#### 5. 系统测试和演示
```bash
# 运行系统测试
uv run python test_agents.py
# 或使用Makefile
make test

# 运行智能体演示
uv run python main_mcp.py --demo
# 或使用Makefile
make demo
```

### 🛠️ 开发工具和命令

#### uv包管理器
```bash
# 安装依赖
uv sync                    # 基础依赖
uv sync --extra dev        # 开发依赖
uv sync --extra all        # 所有依赖

# 运行命令
uv run python main_mcp.py  # 运行主程序
uv run pytest             # 运行测试

# 管理依赖
uv add package-name        # 添加依赖
uv remove package-name     # 移除依赖
uv lock                    # 更新锁定文件
```

#### Makefile快捷命令
```bash
make help                  # 显示所有可用命令
make install              # 安装依赖
make dev                  # 安装开发依赖
make verify               # 验证安装
make test                 # 运行测试
make lint                 # 代码检查
make format               # 代码格式化
make run                  # 交互式运行
make demo                 # 演示模式
make web                  # Web界面
make clean                # 清理缓存
```

### 🔄 工作流模式详解

- **Hybrid** (混合模式): 🧠 智能决策，根据任务复杂度自动选择最优策略
- **Sequential** (顺序模式): 📚→🗄️→⚛️→🧪 逐步深入，适合复杂研究
- **Parallel** (并行模式): 📚🗄️⚛️🧪 同时执行，适合快速验证
- **Specialized** (专项模式): 🎯 针对特定研究类型的定制化流程

## 🏗️ MCP架构详细说明

### 🔧 完整MCP服务器生态

ResearchMind采用Model Context Protocol (MCP)标准，构建了完整的科研工具生态系统。每个MCP服务器都是独立的微服务，提供标准化的工具接口。

#### 📚 文献检索MCP服务器 (✅ 已实现)
```python
# mcp_servers/literature/server.py
@app.list_tools()
async def list_literature_tools():
    return [
        Tool(name="search_arxiv", description="搜索ArXiv论文数据库"),
        Tool(name="search_scholar", description="搜索Google Scholar"),
        Tool(name="search_web", description="网络搜索相关文献"),
        Tool(name="analyze_paper", description="分析论文内容"),
        Tool(name="generate_report", description="生成文献调研报告")
    ]
```

**核心功能**:
- 🔍 **多源检索**: ArXiv、Google Scholar、Web Search并行搜索
- 📄 **智能分析**: 自动提取论文关键信息和研究方法
- 📊 **报告生成**: 结构化文献调研报告自动生成
- 🎯 **相关性排序**: 基于研究目标的智能筛选

#### 🗄️ 材料数据库MCP服务器 (✅ 已实现)
```python
# mcp_servers/materials/server.py
@app.list_tools()
async def list_materials_tools():
    return [
        Tool(name="search_structure", description="搜索晶体结构数据库"),
        Tool(name="generate_structure", description="使用CrystaLLM生成新结构"),
        Tool(name="predict_properties", description="预测材料性质"),
        Tool(name="validate_structure", description="验证结构稳定性"),
        Tool(name="visualize_structure", description="可视化晶体结构")
    ]
```

**核心功能**:
- 🔬 **多数据库集成**: Materials Project、OQMD、NOMAD统一接口
- ⚛️ **AI结构生成**: CrystaLLM驱动的新材料结构设计
- 📊 **性质预测**: 基于机器学习的材料性质预测
- ✅ **结构验证**: 自动验证结构合理性和稳定性
- 🎨 **3D可视化**: 交互式晶体结构可视化

#### ⚛️ 仿真计算MCP服务器 (✅ 已实现)
```python
# mcp_servers/simulation/server.py
@app.list_tools()
async def list_simulation_tools():
    return [
        Tool(name="setup_calculation", description="设置计算参数"),
        Tool(name="run_mattersim", description="运行MatterSim计算"),
        Tool(name="analyze_results", description="分析仿真结果"),
        Tool(name="optimize_structure", description="结构优化"),
        Tool(name="calculate_properties", description="计算物理性质")
    ]
```

**核心功能**:
- 🧮 **MatterSim集成**: 原子级精确的通用势函数计算
- 📏 **多尺度建模**: 从原子到材料的跨尺度仿真
- ⚙️ **智能参数设置**: 基于材料特性的自动参数优化
- 📈 **结果分析**: 能量、力、应力、动力学性质全面分析
- 🎯 **结构优化**: 多种优化算法的智能选择

#### 🧪 实验设计MCP服务器 (✅ 已实现)
```python
# mcp_servers/experiment/server.py
@app.list_tools()
async def list_experiment_tools():
    return [
        Tool(name="design_experiment", description="设计实验方案"),
        Tool(name="optimize_parameters", description="优化实验参数"),
        Tool(name="assess_risk", description="评估实验风险"),
        Tool(name="generate_protocol", description="生成实验协议"),
        Tool(name="estimate_cost", description="估算实验成本")
    ]
```

**核心功能**:
- 🎯 **智能方案设计**: 基于研究目标的实验方案自动生成
- ⚙️ **参数优化**: 贝叶斯优化、遗传算法等多种优化方法
- ⚠️ **风险评估**: 化学品、设备、工艺全方位安全评估
- 📋 **协议生成**: 详细的标准化实验操作协议
- 💰 **成本估算**: 材料、设备、人工成本全面分析

### 🔄 MCP服务器通信架构

#### 标准化接口设计
```python
# 统一的MCP工具调用接口
@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[mcp_types.Content]:
    """执行工具调用的标准接口"""
    try:
        # 工具路由和执行
        result = await tool_router.execute(name, arguments)

        # 标准化响应格式
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )]
    except Exception as e:
        # 统一错误处理
        return [mcp_types.TextContent(
            type="text",
            text=json.dumps({"error": str(e)}, ensure_ascii=False)
        )]
```

#### 智能体层次结构
```
research_coordinator (主协调器)
├── literature_agent (文献调研)
│   └── literature_mcp_server
├── database_agent (数据库检索)
│   └── materials_mcp_server
├── simulation_agent (仿真计算)
│   └── simulation_mcp_server
└── experiment_agent (实验设计)
    └── experiment_mcp_server
```

### 📁 完整MCP服务器目录结构

```
mcp_servers/
├── literature/                      # 文献检索MCP服务器 ✅
│   ├── server.py                   # 主服务器文件
│   └── tools/                      # 工具实现
│       ├── arxiv_search.py         # ArXiv搜索工具
│       ├── scholar_search.py       # Google Scholar搜索
│       ├── web_search.py           # 网络搜索工具
│       └── paper_analysis.py       # 论文分析工具
├── materials/                       # 材料数据库MCP服务器 ✅
│   ├── server.py                   # 主服务器文件
│   └── tools/                      # 工具实现
│       ├── materials_project.py    # Materials Project API
│       ├── crystallm_wrapper.py    # CrystaLLM包装器
│       └── structure_analysis.py   # 结构分析工具
├── simulation/                      # 仿真计算MCP服务器 ✅
│   ├── server.py                   # 主服务器文件
│   └── tools/                      # 工具实现
│       ├── mattersim_wrapper.py    # MatterSim包装器
│       ├── calculation_setup.py    # 计算参数设置
│       └── result_analysis.py      # 结果分析工具
└── experiment/                      # 实验设计MCP服务器 ✅
    ├── server.py                   # 主服务器文件
    └── tools/                      # 工具实现
        ├── design_optimizer.py     # 实验设计优化
        ├── risk_assessment.py      # 风险评估工具
        └── protocol_generator.py   # 协议生成工具
```

### 🛠️ MCP工具详细功能矩阵

| MCP服务器 | 工具名称 | 功能描述 | 输入参数 | 输出格式 | 状态 |
|-----------|----------|----------|----------|----------|------|
| **Literature** | `search_arxiv` | ArXiv论文搜索 | query, max_results, sort_by | JSON论文列表 | ✅ |
| | `search_scholar` | Google Scholar搜索 | query, max_results, year_range | JSON论文列表 | ✅ |
| | `search_web` | 网络文献搜索 | query, max_results, site | JSON搜索结果 | ✅ |
| | `analyze_paper` | 论文内容分析 | paper_content, analysis_type | JSON分析结果 | ✅ |
| | `generate_report` | 生成调研报告 | papers, research_topic, report_type | 结构化报告 | ✅ |
| **Materials** | `search_structure` | 搜索晶体结构 | formula, elements, crystal_system | JSON结构列表 | ✅ |
| | `generate_structure` | 生成新结构 | composition, crystal_system, num_structures | CIF结构数据 | ✅ |
| | `predict_properties` | 预测材料性质 | structure, properties | JSON性质数据 | ✅ |
| | `validate_structure` | 验证结构稳定性 | structure, check_symmetry, check_bonding | 验证报告 | ✅ |
| | `visualize_structure` | 可视化结构 | structure, view_type, show_unit_cell | 图像数据 | ✅ |
| **Simulation** | `setup_calculation` | 设置计算参数 | structure, calculation_type, accuracy | 计算配置 | ✅ |
| | `run_mattersim` | 运行MatterSim | calculation_id, max_steps, use_gpu | 计算结果 | ✅ |
| | `analyze_results` | 分析仿真结果 | calculation_id, analysis_type | 分析报告 | ✅ |
| | `optimize_structure` | 结构优化 | structure, optimization_method | 优化结果 | ✅ |
| | `calculate_properties` | 计算物理性质 | structure, properties, k_point_density | 性质数据 | ✅ |
| **Experiment** | `design_experiment` | 设计实验方案 | research_objective, target_material | 实验设计 | ✅ |
| | `optimize_parameters` | 优化实验参数 | experiment_type, parameters, target_property | 优化结果 | ✅ |
| | `assess_risk` | 评估实验风险 | experiment_design, chemicals, equipment | 风险报告 | ✅ |
| | `generate_protocol` | 生成实验协议 | experiment_design, detail_level | 详细协议 | ✅ |
| | `estimate_cost` | 估算实验成本 | experiment_design, scale, location | 成本分析 | ✅ |

### ⚙️ MCP配置管理

#### 配置文件结构 (`config/mcp_config.yaml`)
```yaml
mcp_servers:
  literature:
    command: "python"
    args: ["mcp_servers/literature/server.py"]
    connection_type: "stdio"
    tools:
      - search_arxiv
      - search_scholar
      - search_web
      - analyze_paper
      - generate_report
    env:
      ARXIV_API_KEY: "${ARXIV_API_KEY}"
      SCHOLAR_API_KEY: "${SCHOLAR_API_KEY}"

  materials:
    command: "python"
    args: ["mcp_servers/materials/server.py"]
    connection_type: "stdio"
    tools:
      - search_structure
      - generate_structure
      - predict_properties
      - validate_structure
      - visualize_structure
    env:
      MATERIALS_PROJECT_API_KEY: "${MATERIALS_PROJECT_API_KEY}"
      CRYSTALLM_MODEL_PATH: "${CRYSTALLM_MODEL_PATH}"

  simulation:
    command: "python"
    args: ["mcp_servers/simulation/server.py"]
    connection_type: "stdio"
    tools:
      - setup_calculation
      - run_mattersim
      - analyze_results
      - optimize_structure
      - calculate_properties
    env:
      MATTERSIM_LICENSE: "${MATTERSIM_LICENSE}"
      CUDA_VISIBLE_DEVICES: "${CUDA_VISIBLE_DEVICES}"

  experiment:
    command: "python"
    args: ["mcp_servers/experiment/server.py"]
    connection_type: "stdio"
    tools:
      - design_experiment
      - optimize_parameters
      - assess_risk
      - generate_protocol
      - estimate_cost
    env:
      SAFETY_DATABASE_PATH: "${SAFETY_DATABASE_PATH}"
      COST_DATABASE_PATH: "${COST_DATABASE_PATH}"
```

### 🚀 MCP使用示例

#### 1. 启动MCP服务器
```bash
# 启动所有MCP服务器
python main_mcp.py

# 启动特定MCP服务器
python mcp_servers/materials/server.py
```

#### 2. 调用MCP工具示例

**文献检索示例**:
```python
# 搜索相关论文
result = await literature_client.call_tool("search_arxiv", {
    "query": "perovskite solar cell efficiency",
    "max_results": 10,
    "sort_by": "relevance"
})

# 分析论文内容
analysis = await literature_client.call_tool("analyze_paper", {
    "paper_content": paper_text,
    "analysis_type": "methodology"
})
```

**材料数据库查询示例**:
```python
# 搜索钙钛矿结构
structures = await materials_client.call_tool("search_structure", {
    "formula": "CsPbI3",
    "crystal_system": "cubic",
    "max_results": 5
})

# 生成新结构
new_structure = await materials_client.call_tool("generate_structure", {
    "composition": "Cs Pb I",
    "crystal_system": "tetragonal",
    "num_structures": 3
})
```

**仿真计算示例**:
```python
# 设置计算参数
calc_setup = await simulation_client.call_tool("setup_calculation", {
    "structure": structure_data,
    "calculation_type": "energy_minimization",
    "accuracy": "high"
})

# 运行MatterSim计算
result = await simulation_client.call_tool("run_mattersim", {
    "calculation_id": calc_setup["calculation_id"],
    "max_steps": 1000,
    "use_gpu": True
})
```

**实验设计示例**:
```python
# 设计实验方案
experiment = await experiment_client.call_tool("design_experiment", {
    "research_objective": "提高钙钛矿太阳能电池效率",
    "target_material": "CsPbI3",
    "synthesis_method": "sol_gel",
    "budget_constraint": 50.0
})

# 生成实验协议
protocol = await experiment_client.call_tool("generate_protocol", {
    "experiment_design": experiment["experiment_design"],
    "detail_level": "comprehensive",
    "include_safety": True
})
```

## 🔧 开发指南

### 添加新的MCP工具

1. **在对应的MCP服务器中添加工具**
```python
# mcp_servers/literature/tools/new_tool.py
class NewTool:
    async def process(self, input_data):
        # 实现工具逻辑
        return result
```

2. **在服务器中注册工具**
```python
# mcp_servers/literature/server.py
@app.list_tools()
async def list_tools():
    return [
        # 现有工具...
        mcp_types.Tool(
            name="new_tool",
            description="新工具描述",
            inputSchema={...}
        )
    ]
```

3. **在智能体中启用工具**
```python
# agents/coordinator_agent.py
MCPToolset(
    connection_params=...,
    tool_filter=['existing_tools', 'new_tool']
)
```

### 部署到生产环境

#### Cloud Run部署
```bash
# 构建容器镜像
docker build -t researchmind .

# 部署到Cloud Run
gcloud run deploy researchmind \
  --image researchmind \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### 使用ADK部署命令
```bash
# 部署到Vertex AI Agent Engine
adk deploy agent_engine \
  --project=your-gcp-project \
  --region=us-central1 \
  --staging_bucket="gs://your-bucket" \
  --display_name="ResearchMind" \
  ./agents

# 部署到Cloud Run
adk deploy cloud_run \
  --project=your-gcp-project \
  --region=us-central1 \
  --service_name=researchmind \
  ./agents
```

## 🤖 智能体架构详细说明

### 🏗️ 多层次智能体体系

ResearchMind采用分层的多智能体架构，每个层次都有明确的职责和专业领域：

#### 1️⃣ 协调层 (Coordination Layer)
```python
# 主协调器智能体 - 系统入口点
root_agent = LlmAgent(
    name='research_coordinator',
    model='gemini-2.0-flash',
    instruction='科研流程协调和任务分配',
    sub_agents=[...],  # 管理所有子智能体
    tools=[...]       # 集成所有MCP工具
)
```

**核心职责**:
- 🎯 理解用户研究需求和目标
- 📋 制定研究策略和执行计划
- 🔄 选择最适合的工作流模式
- 🤝 协调各专业智能体协作
- 📊 整合多源信息和结果

#### 2️⃣ 专家层 (Expert Layer)
每个专家智能体都是特定领域的专业助手：

**📚 文献调研专家 (Literature Agent)**
```python
literature_agent = LlmAgent(
    name='literature_researcher',
    instruction='专业文献检索、分析和报告生成专家',
    tools=[literature_mcp_toolset]
)
```
- 🔍 多源文献检索 (ArXiv, Scholar, Web)
- 📄 智能内容分析和方法提取
- 📊 研究趋势分析和知识图谱
- 📝 结构化报告生成

**🗄️ 数据库检索专家 (Database Agent)**
```python
database_agent = LlmAgent(
    name='database_searcher',
    instruction='材料数据库搜索和结构分析专家',
    tools=[materials_mcp_toolset]
)
```
- 🔬 多数据库检索 (Materials Project, OQMD, NOMAD)
- ⚛️ AI结构生成 (CrystaLLM)
- 📊 性质预测和结构验证
- 🎨 3D结构可视化

**⚛️ 仿真计算专家 (Simulation Agent)**
```python
simulation_agent = LlmAgent(
    name='simulation_expert',
    instruction='多尺度仿真计算和结果分析专家',
    tools=[simulation_mcp_toolset]
)
```
- 🧮 MatterSim原子级精确计算
- 📏 多尺度建模 (原子→材料→器件)
- ⚙️ 智能参数设置和优化
- 📈 深度结果分析和物理解释

**🧪 实验设计专家 (Experiment Agent)**
```python
experiment_agent = LlmAgent(
    name='experiment_designer',
    instruction='实验方案设计、优化和风险评估专家',
    tools=[experiment_mcp_toolset]
)
```
- 🎯 智能实验方案设计
- ⚙️ 统计学参数优化 (DOE, 贝叶斯优化)
- ⚠️ 全方位安全风险评估
- 📋 标准化协议生成

#### 3️⃣ 工作流层 (Workflow Layer)
管理复杂的多步骤研究流程：

**🔄 顺序工作流 (Sequential Workflow)**
```python
sequential_workflow_agent = SequentialAgent(
    name='sequential_research_workflow',
    sub_agents=[literature_agent, database_agent, simulation_agent, experiment_agent]
)
```
- 📚 文献调研 → 🗄️ 数据库检索 → ⚛️ 仿真验证 → 🧪 实验设计
- 适合：复杂研究、风险控制、深度分析
- 特点：逻辑清晰、风险可控、结果可靠

**⚡ 并行工作流 (Parallel Workflow)**
```python
parallel_workflow_agent = ParallelAgent(
    name='parallel_research_workflow',
    sub_agents=[literature_agent, database_agent, simulation_agent, experiment_agent]
)
```
- 📚🗄️⚛️🧪 同时执行，结果整合
- 适合：时间紧迫、资源充足、快速验证
- 特点：效率高、时间短、信息全面

**🧠 混合工作流 (Hybrid Workflow)**
```python
hybrid_workflow_agent = LlmAgent(
    name='hybrid_research_workflow',
    instruction='根据情况智能选择顺序或并行策略',
    sub_agents=[sequential_workflow_agent, parallel_workflow_agent, ...]
)
```
- 🎯 智能决策：根据复杂度、资源、时间动态选择
- 🔄 自适应调整：根据中间结果优化后续策略
- ⚖️ 资源优化：最大化利用可用资源

#### 4️⃣ 管理层 (Management Layer)
```python
# 智能体管理器
agent_manager = AgentManager()
- 📋 任务创建和调度
- 🔄 智能体状态管理
- 📊 性能监控和统计
- ⚡ 资源优化分配
```

### 🔧 智能体协调机制

#### 任务分发策略
```python
def recommend_agent(task_type: str):
    recommendations = {
        '文献调研': ['literature_agent', 'literature_workflow'],
        '材料搜索': ['database_agent', 'materials_discovery'],
        '仿真计算': ['simulation_agent', 'computational_workflow'],
        '实验设计': ['experiment_agent', 'experimental_workflow'],
        '综合研究': ['root_agent', 'hybrid_workflow']
    }
    return recommendations.get(task_type, ['root_agent'])
```

#### 工作流选择逻辑
```python
# 决策矩阵
复杂度 | 资源 | 时间 | 风险 | 基础 | 推荐策略
-------|------|------|------|------|----------
低     | 充足 | 紧   | 低   | 好   | 并行工作流
高     | 有限 | 宽松 | 高   | 差   | 顺序工作流
中     | 中等 | 中等 | 中   | 中   | 混合工作流
专项   | 定制 | 灵活 | 可控 | 专业 | 专项工作流
```

### 📊 智能体性能监控

#### 实时状态监控
```python
# 智能体状态
agent_status = {
    'name': 'literature_agent',
    'status': 'idle',  # idle, busy, error, offline
    'current_task': None,
    'total_tasks': 156,
    'successful_tasks': 142,
    'success_rate': 0.91,
    'average_execution_time': 45.2,
    'capabilities': ['文献检索', 'ArXiv搜索', '论文分析']
}

# 系统统计
system_stats = {
    'total_agents': 13,
    'idle_agents': 8,
    'busy_agents': 3,
    'error_agents': 0,
    'total_tasks': 1247,
    'success_rate': 0.94
}
```

## 🚀 开发路线图

### Phase 1: MCP基础架构 ✅
- [x] **环境配置**: Google ADK + MCP环境搭建
- [x] **MCP服务器框架**: 创建基础MCP服务器模板
- [x] **智能体框架**: 实现多智能体协调机制
- [x] **配置管理**: 统一配置管理系统

### Phase 2: 文献调研MCP服务器 ✅
- [x] **ArXiv MCP工具**: 实现ArXiv搜索和分析工具
- [x] **Scholar MCP工具**: Google Scholar集成（模拟）
- [x] **Web搜索工具**: 通用网络搜索能力
- [x] **文献分析引擎**: 论文内容分析
- [x] **报告生成器**: 自动化报告生成
- [x] **MCP服务器框架**: 完整的stdio/sse连接支持
- [ ] **PDF解析**: 实际PDF文件处理
- [ ] **真实API集成**: 替换模拟实现

### Phase 3: 材料数据库MCP服务器 ✅
- [x] **Materials Project集成**: 材料数据库API封装
- [x] **CrystaLLM集成**: 晶体结构生成工具
- [x] **结构分析工具**: 结构验证和性质预测
- [x] **数据可视化**: 3D结构展示
- [x] **MCP服务器实现**: 完整的工具生态

### Phase 4: 仿真计算MCP服务器 ✅
- [x] **MatterSim集成**: 原子级仿真计算
- [x] **计算参数优化**: 自动参数调优
- [x] **结果分析引擎**: 仿真结果智能分析
- [x] **性能监控**: 计算资源管理
- [x] **MCP工具包装**: 标准化接口实现

### Phase 5: 实验设计MCP服务器 ✅
- [x] **设计算法**: 实验方案生成算法
- [x] **参数优化**: 贝叶斯优化集成
- [x] **风险评估**: 安全性和可行性评估
- [x] **协议生成**: 标准化实验协议
- [x] **MCP服务器架构**: 完整的实验设计工具链

### Phase 6: 系统集成与部署 ✅
- [x] **多智能体协调**: 工作流编排和管理
- [x] **智能体管理器**: 动态调度和资源管理
- [x] **工作流引擎**: 顺序、并行、混合、专项工作流
- [x] **专业智能体**: 文献、数据库、仿真、实验专家
- [x] **智能体注册表**: 自动发现和推荐系统
- [x] **任务管理系统**: 创建、调度、监控、统计
- [x] **演示和测试**: 完整的演示脚本和测试套件
- [ ] **云原生部署**: Cloud Run/GKE部署
- [ ] **监控运维**: 日志、监控、告警系统
- [ ] **文档完善**: API文档和用户指南

## 🔄 MCP服务器通信架构

### 服务器间通信模式
```python
# 协调器智能体管理所有MCP连接
coordinator_agent = LlmAgent(
    name="research_coordinator",
    instruction="协调各专业智能体完成科研任务",
    sub_agents=[
        literature_agent,    # 文献调研子智能体
        database_agent,      # 数据库检索子智能体
        simulation_agent,    # 仿真计算子智能体
        experiment_agent     # 实验设计子智能体
    ]
)
```

### 工作流编排示例
```python
# Sequential Pipeline 示例
sequential_workflow = SequentialAgent(
    name="research_pipeline",
    agents=[
        literature_agent,    # 步骤1: 文献调研
        database_agent,      # 步骤2: 数据库检索
        simulation_agent,    # 步骤3: 仿真验证
        experiment_agent     # 步骤4: 实验设计
    ]
)

# Parallel Processing 示例
parallel_workflow = ParallelAgent(
    name="parallel_research",
    agents=[literature_agent, database_agent, simulation_agent],
    gather_agent=experiment_agent  # 汇总结果
)
```

### MCP连接配置
```yaml
# mcp_config.yaml
mcp_servers:
  literature:
    connection_type: "stdio"
    command: "python"
    args: ["mcp_servers/literature/server.py"]
    timeout: 30

  materials:
    connection_type: "sse"
    url: "https://materials-mcp.research-mind.com/sse"
    headers:
      Authorization: "Bearer ${MATERIALS_API_KEY}"

  simulation:
    connection_type: "stdio"
    command: "python"
    args: ["mcp_servers/simulation/server.py"]
    env:
      MATTERSIM_LICENSE: "${MATTERSIM_LICENSE}"

  experiment:
    connection_type: "stdio"
    command: "python"
    args: ["mcp_servers/experiment/server.py"]
```

## 💰 商业模式与收益分成

### 🎯 多层次收益模式

#### 1. SaaS订阅服务
```
基础版 (免费)
├── 文献调研: 5次/月
├── 数据库检索: 10次/月
├── 基础仿真: 2次/月
└── 社区支持

专业版 ($49/月)
├── 无限文献调研
├── 高级数据库访问
├── 标准仿真计算
├── 实验设计工具
└── 邮件支持

企业版 ($299/月)
├── 所有专业版功能
├── 大规模仿真计算
├── 定制化工具开发
├── 私有化部署选项
└── 专属技术支持
```

#### 2. MCP工具生态分成
```python
# 第三方MCP服务器接入分成模式
class MCPEcosystem:
    def __init__(self):
        self.revenue_share = {
            "tool_provider": 0.30,    # 工具提供商30%
            "platform": 0.50,        # 平台50%
            "infrastructure": 0.20    # 基础设施20%
        }

    def register_mcp_server(self, provider, server_config):
        """注册第三方MCP服务器"""
        return {
            "server_id": generate_id(),
            "revenue_model": "usage_based",
            "pricing": server_config.pricing,
            "revenue_share": self.revenue_share
        }
```

#### 3. 计算资源分成
- **云计算合作**: 与AWS、GCP、Azure分成
- **HPC资源**: 与超算中心合作提供大规模计算
- **专业软件**: 与MatterSim、CrystaLLM等软件厂商合作

### 🎯 目标市场与应用场景

#### 🎓 学术研究市场 (TAM: $2B)
```
博士生/博后 (50万用户)
├── 文献调研加速
├── 实验方案设计
├── 数据分析辅助
└── 论文写作支持

科研团队 (10万团队)
├── 项目申请支持
├── 多学科协作
├── 资源共享平台
└── 成果转化辅助
```

#### 🏭 工业研发市场 (TAM: $5B)
```
材料企业 (1万家)
├── 新材料开发
├── 性能优化
├── 成本控制
└── 上市时间缩短

制药公司 (5千家)
├── 分子设计
├── 药物筛选
├── 临床试验设计
└── 监管合规
```

#### 📚 教育培训市场 (TAM: $1B)
```
高等院校 (3千所)
├── 科研方法教学
├── 实验设计培训
├── 学术写作指导
└── 创新能力培养
```

## 🏆 核心竞争优势

### 1. 🔬 技术护城河
- **多智能体协作**: 业界首个科研领域多智能体系统
- **MCP生态**: 标准化工具接口，可扩展性强
- **深度集成**: MatterSim、CrystaLLM等专业工具深度集成
- **全流程覆盖**: 从文献到实验的完整科研闭环

### 2. 📊 数据护城河
- **科研知识图谱**: 构建领域专业知识图谱
- **实验数据库**: 积累大量实验设计和结果数据
- **用户行为**: 科研工作流程和偏好数据
- **模型优化**: 基于用户反馈持续优化AI模型

### 3. 🤝 生态护城河
- **开放平台**: 第三方工具和服务商接入
- **学术合作**: 与顶级高校和研究所深度合作
- **产业联盟**: 与材料、制药等行业龙头企业合作
- **开发者社区**: 活跃的MCP工具开发者生态

### 4. 💡 创新护城河
- **持续研发**: 20%收入投入R&D
- **专利布局**: 核心算法和架构专利保护
- **人才团队**: 顶级AI和材料科学专家团队
- **技术前瞻**: 紧跟AI和科研工具发展趋势
3. **智能化程度高**: 基于先进的LLM和专业工具
4. **可扩展性强**: 模块化设计，易于扩展新功能
5. **用户体验优**: 简洁直观的交互界面

## 风险评估

### 技术风险
- **模型准确性**: 仿真结果的可靠性
- **数据质量**: 文献和数据库数据的质量
- **计算资源**: 大规模仿真的计算需求

### 商业风险
- **市场接受度**: 用户对AI科研工具的接受程度
- **竞争压力**: 同类产品的竞争
- **法律合规**: 数据使用的合规性

### 应对策略
- **技术验证**: 与专家合作验证结果准确性
- **用户反馈**: 持续收集用户反馈优化产品
- **合规保障**: 严格遵守数据使用规范

## 下一步行动

1. **立即开始**: 搭建基础开发环境
2. **团队组建**: 招募相关技术人员
3. **资源准备**: 申请必要的API和计算资源
4. **原型开发**: 快速开发MVP版本
5. **用户测试**: 邀请目标用户参与测试

---

## ✅ Agent部分完成总结

### 🎯 **完成的智能体生态系统**

ResearchMind的Agent部分已全面完成，构建了一个完整的多智能体科研协作系统：

#### 🏗️ **分层智能体架构**
- ✅ **协调层**: 主协调器智能体，统筹全局
- ✅ **专家层**: 4个专业智能体（文献、数据库、仿真、实验）
- ✅ **工作流层**: 4种工作流模式（顺序、并行、混合、专项）
- ✅ **管理层**: 智能体管理器，动态调度和监控

#### 🤖 **核心智能体组件**
1. **主协调器** (`root_agent`) - 总指挥，智能决策
2. **文献专家** (`literature_agent`) - ArXiv、Scholar、Web搜索
3. **数据库专家** (`database_agent`) - Materials Project、CrystaLLM集成
4. **仿真专家** (`simulation_agent`) - MatterSim多尺度计算
5. **实验专家** (`experiment_agent`) - DOE设计、风险评估

#### 🔄 **智能工作流引擎**
- ✅ **顺序工作流**: 深度研究，逐步推进
- ✅ **并行工作流**: 高效执行，快速验证
- ✅ **混合工作流**: 智能决策，自适应策略
- ✅ **专项工作流**: 定制化，针对特定研究类型

#### 📊 **智能体管理系统**
- ✅ **任务管理**: 创建、调度、执行、监控
- ✅ **智能体注册**: 自动发现、能力匹配、推荐
- ✅ **性能监控**: 实时状态、统计分析、优化建议
- ✅ **资源调度**: 负载均衡、错误处理、故障恢复

#### 🛠️ **开发工具和测试**
- ✅ **演示系统**: 完整的使用演示 (`examples/agent_demo.py`)
- ✅ **测试套件**: 全面的系统测试 (`test_agents.py`)
- ✅ **CLI工具**: 丰富的命令行选项和模式
- ✅ **配置管理**: 灵活的配置和环境变量

### 🚀 **即可使用的功能**

```bash
# 🧪 系统测试
python test_agents.py

# 🎭 智能体演示
python main_mcp.py --demo

# 🧠 智能混合模式 (推荐)
python main_mcp.py --research "新能源材料" --workflow hybrid

# 👨‍🔬 专业智能体模式
python main_mcp.py --agent literature_agent --research "文献调研"

# 🌐 Web界面模式
python main_mcp.py --web --port 8080
```

### 🎉 **Agent部分完全实现！**

ResearchMind现在拥有了完整的多智能体科研协作系统，能够：
- 🎯 智能理解研究需求
- 🔄 自动选择最优工作流
- 🤝 协调多个专业智能体
- 📊 实时监控和优化性能
- 🚀 提供多种使用模式

这个强大的Agent生态系统为科研工作者提供了从文献调研到实验设计的全流程智能化支持！

---

*ResearchMind - 让科研更智能，让创新更高效*
