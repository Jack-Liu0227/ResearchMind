<div align="center">

# ResearchMind · 智能科研助手
**Your AI Partner in Materials Science**

</div>

---

**[English](#english-version) | [中文版](#中文版)**

---

## 📖 概述 (Overview)

**ResearchMind** 是一款基于**多智能体架构**的AI研究助手，专为材料科学研究领域深度定制。应用集成了四大核心功能模块，为研究人员提供从文献调研、数据查询、仿真计算到实验规划的**一站式科研解决方案**。

**ResearchMind** is an AI research assistant built on a **multi-agent architecture**, specifically tailored for the field of materials science. It integrates four core functional modules to provide researchers with a **one-stop solution** for everything from literature review and data queries to simulation and experimental planning.

---

## ✨ 核心优势 (Core Advantages)

- 🧠 **深度智能 (Deep Intelligence)**: 结合深度学习与大型语言模型，能够理解复杂的科研问题，并提供精准的分析与解答。
- 🧩 **模块化设计 (Modular Design)**: 灵活的多智能体架构，可根据研究需求调用最合适的智能体，精准满足不同研究场景。
- ⚡ **高效执行 (Efficient Execution)**: 自动规划并并行执行复杂的科研任务，从文献检索到数据分析，大幅提升科研效率。
- 🌐 **多源整合 (Multi-Source Integration)**: 无缝对接多个权威学术数据库和计算平台，打破信息孤岛，提供全面的数据支持。

---

- 🧠 **Deep Intelligence**: Combines deep learning and large language models to understand complex scientific problems, providing precise analysis and answers.
- 🧩 **Modular Design**: A flexible multi-agent architecture that invokes the most suitable agent for your research needs, perfectly fitting various scenarios.
- ⚡ **Efficient Execution**: Automatically plans and executes complex research tasks in parallel, from literature searches to data analysis, dramatically boosting your research efficiency.
- 🌐 **Multi-Source Integration**: Seamlessly connects with multiple authoritative academic databases and computing platforms, breaking down information silos to provide comprehensive data support.

---

## 🚀 系统架构 (System Architecture)

### 核心功能模块 (Core Functional Modules)

| 智能体 (Agent)                               | 功能特色 (Key Features)                                                                                                                            | 数据源 / 能力 (Data Sources / Capabilities)                                                                                             |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 📚 **文献研究 (Literature Research)**        | 智能论文搜索、多源信息整合、深度内容分析、生成综合报告。                                                                                             | **数据源**: ArXiv, Tavily, Semantic Scholar, etc.                                                                                        |
| 📊 **数据库查询 (Database Query)**           | 跨库智能检索、结构与性质查询、数据比对分析。                                                                                                       | **数据库**: Materials Project, OQMD, COD, AFLOW                                                                                          |
| 🔬 **仿真计算 (Simulation & Calculation)** | 上传结构文件进行计算、支持多种物理性质分析、提供专业的可视化。                                                                                       | **计算能力**: 热导率 (Thermal Conductivity), 能量属性 (Energy Properties), 声子谱 (Phonon Spectrum)                                        |
| 🧪 **实验规划 (Experiment Planning)**        | 综合多源信息，制定科学严谨的实验方案与验证路径。                                                                                                     | **能力**: 方案生成, 风险评估, 多智能体协同 (Plan Generation, Risk Assessment, Synergy)                                                    |

<br>

| Agent                                        | Key Features                                                                                                                                       | Data Sources / Capabilities                                                                                                              |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 📚 **Literature Research**                   | Smart paper search, multi-source information integration, deep content analysis, and comprehensive report generation.                                | **Data Sources**: ArXiv, Tavily, Semantic Scholar, etc.                                                                                  |
| 📊 **Database Query**                        | Cross-database smart retrieval, structure and property queries, and comparative data analysis.                                                     | **Databases**: Materials Project, OQMD, COD, AFLOW                                                                                       |
| 🔬 **Simulation & Calculation**              | Upload structure files for calculation, supports various physical property analyses, and provides professional visualizations.                       | **Capabilities**: Thermal Conductivity, Energy Properties, Phonon Spectrum                                                               |
| 🧪 **Experiment Planning**                   | Synthesizes multi-source info to create rigorous experimental plans and verification paths.                                                          | **Capabilities**: Plan Generation, Risk Assessment, Multi-Agent Collaboration                                                            |

---

## 📖 最佳实践指南 (Best Practices Guide)

#### 🔬 **示例1：材料热导率研究 (Example 1: Researching Thermal Conductivity)**

- **选择功能**: **仿真计算助手 (Simulation & Calculation Agent)**
- **操作流程**:
  1. 在左侧功能区选择“仿真计算助手”。
  2. 上传您的 `CIF` 晶体结构文件。
  3. 在输入框中输入指令:
    > "计算这个结构的热导率和声子谱"
- **预期输出**:
  - ✅ **精确计算**: 获得材料的热导率精确计算结果。
  - ✅ **专业图像**: 生成声子谱图像，并附带专业分析。
  - ✅ **实时可视化**: 在右侧展示区实时查看晶体结构与生成的声子谱图。

---

- **Select Agent**: **Simulation & Calculation Agent**
- **Workflow**:
  1. Choose "Simulation & Calculation Agent" from the left-hand function panel.
  2. Upload your `CIF` crystal structure file.
  3. Enter the command in the input box:
    > "Calculate the thermal conductivity and phonon spectrum for this structure"
- **Expected Output**:
  - ✅ **Precise Calculation**: Get accurate thermal conductivity results for your material.
  - ✅ **Professional Graphics**: Generate a phonon spectrum image with expert analysis.
  - ✅ **Live Visualization**: View the crystal structure and the generated phonon spectrum in real-time in the right-side display area.

---

#### ⚗️ **示例2：晶体结构查询 (Example 2: Querying Crystal Structures)**

- **选择功能**: **数据库查询助手 (Database Query Agent)**
- **操作流程**:
  1. 选择“数据库查询助手”。
  2. 输入您想查询的材料，例如:
    > "查询NaCl的晶体结构"
- **预期输出**:
  - ✅ **智能检索**: 智能体将自动轮询所有可用数据库 (Materials Project, OQMD, COD, AFLOW)。
  - ✅ **快速响应**: 返回首个成功命中的查询结果，并展示其详细信息和3D结构。

---

- **Select Agent**: **Database Query Agent**
- **Workflow**:
  1. Choose "Database Query Agent".
  2. Enter the material you want to query, for example:
    > "Find the crystal structure of NaCl"
- **Expected Output**:
  - ✅ **Smart Retrieval**: The agent will automatically query all available databases (Materials Project, OQMD, COD, AFLOW).
  - ✅ **Fast Response**: It will return the first successful match, displaying its detailed information and 3D structure.

---

#### 📜 **示例3：学术论文调研 (Example 3: Conducting a Literature Review)**

- **选择功能**: **文献研究助手 (Literature Research Agent)**
- **操作流程**:
  1. 选择“文献研究助手”。
  2. 输入您的研究主题，例如:
    > "生成一份关于大语言模型在材料科学中应用的详细报告"
- **预期输出**:
  - ✅ **并行检索**: 同时从 ArXiv, Tavily 等多个来源检索相关文献。
  - ✅ **深度分析**: 对每篇关键论文进行深度剖析，提取核心观点和方法。
  - ✅ **综合报告**: 生成一份结构清晰、内容详实的综合报告。
  - ✅ **数据文件**: 提供一个包含所有引用文献、摘要和链接的 `CSV` 文件，方便您进一步分析。

---

- **Select Agent**: **Literature Research Agent**
- **Workflow**:
  1. Choose "Literature Research Agent".
  2. Enter your research topic, for example:
    > "Generate a detailed report on the application of large language models in materials science"
- **Expected Output**:
  - ✅ **Parallel Search**: Simultaneously retrieves literature from multiple sources like ArXiv and Tavily.
  - ✅ **In-depth Analysis**: Conducts a deep analysis of each key paper, extracting core ideas and methodologies.
  - ✅ **Comprehensive Report**: Generates a well-structured and detailed summary report.
  - ✅ **Data File**: Provides a `CSV` file containing all cited literature, abstracts, and links for your further analysis.

---

#### 🧪 **示例4：实验方案规划 (Example 4: Experimental Plan Planning)**

- **选择功能**: **实验规划智能体 (Experiment Plan Agent)**
- **操作流程**:
  1. 选择“实验规划智能体”。
  2. 输入您的研究目标，例如:
    > "设计一个提高石墨烯/环氧树脂复合材料热导率的实验方案"
- **预期输出**:
  1. ✅ **综合调研**: 自动调用文献和数据库智能体获取背景信息。
  2. ✅ **方案生成**: 输出包含材料制备、表征测试、数据记录的完整实验流程。
  3. ✅ **风险评估**: 提示潜在的实验风险并给出应对策略。

---

- **Select Agent**: **Experiment Plan Agent**
- **Workflow**:
  1. Choose "Experiment Plan Agent".
  2. Enter your research goal, for example:
    > "Design an experimental plan to improve the thermal conductivity of graphene/epoxy composites"
- **Expected Output**:
  1. ✅ **Comprehensive Survey**: Automatically calls literature and database agents for background info.
  2. ✅ **Plan Generation**: Outputs a complete experimental flow covering preparation, characterization, and data recording.
  3. ✅ **Risk Assessment**: Highlights potential risks and suggests mitigation strategies.

---

## 💰 收费标准 (Billing)

**透明计费，无隐藏费用 (Transparent and Fair Billing)**
- **按工具调用计费**: 只有当智能体在执行任务时调用外部API或进行复杂计算时才会产生费用。
- **详细说明**: 进入应用后，将有关于各项工具收费的详细说明。

---

**Pay-per-use, no hidden fees.**
- **Tool-Call Based**: Charges only apply when an agent calls external APIs or performs complex calculations to complete a task.
- **Detailed Pricing**: Detailed information about the cost of each tool is available within the application.

---

## 🎓 学术引用 (Academic Citation)

如果您在研究中使用了本应用的热导率计算功能，请引用以下论文。

If you use the thermal conductivity calculation feature of this application in your research, please cite the following paper.

**BibTeX 格式:**
```bibtex
@article{Liu2025PINK,
  author  = {Liu, Yujie and Wang, Xiaoying and Gao, Zhibin},
  title   = {{PINK: physical-informed machine learning for lattice thermal conductivity}},
  journal = {Journal of Materials Informatics},
  year    = {2025},
  volume  = {5},
  pages   = {12},
  doi     = {10.20517/jmi.2024.86}
}
```

**BibTeX 格式:**
```bibtex
@article{Liu2025PINK,
  author  = {Liu, Yujie and Wang, Xiaoying and Gao, Zhibin},
  title   = {{PINK: physical-informed machine learning for lattice thermal conductivity}},
  journal = {Journal of Materials Informatics},
  year    = {2025},
  volume  = {5},
  pages   = {12},
  doi     = {10.20517/jmi.2024.86}
}
```

---
---

# <a name="developer-guide"></a> 👨‍💻 开发者指南 (Developer Guide)

## 🚀 快速启动 (Quick Start)

### Linux / macOS / Git Bash
```bash
./start_linux.sh
```

### Windows PowerShell
```powershell
bash start_linux.sh
```

## 📋 系统要求 (System Requirements)

- Python 3.10+
- Node.js 18+
- uv (Python package manager)

### 安装uv (Install uv)
```bash
# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
irm https://astral.sh/uv/install.ps1 | iex
```

## 🌐 访问地址 (Access URLs)

启动后可通过以下地址访问：

- **前端界面 (Frontend UI)**: `http://localhost:50001`
- **外部访问 (External Access)**: `http://your-ip:50001`
- **API文档 (API Docs)**: `http://your-ip:50002/docs`
- **后端API (Backend API)**: `http://localhost:50002` (local) or `http://your-ip:50002` (external)

## 🔧 配置 (Configuration)

启动脚本会在项目根目录生成 `.env` 文件，下面列出需要关注的关键项：

### API 密钥 (API Keys)
```
GOOGLE_API_KEY=your_google_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
TAVILY_API_KEY=your_tavily_api_key
MP_API_KEY=your_materials_project_api_key
```

### 网络相关变量 (Network Variables)
```
# UI 服务监听（start_complete.* 会把 50001 转发到该端口）
VITE_FRONTEND_HOST=127.0.0.1
VITE_FRONTEND_PORT=50010

# 前端调用 API/WS 时使用的相对路径 + 对外端口
VITE_API_URL=/api
VITE_API_PORT=50001
VITE_WS_URL=/ws
VITE_WS_PORT=50001

# 后端实际监听（默认仅限本机）
RESEARCHMIND_HTTP_HOST=127.0.0.1
RESEARCHMIND_HTTP_PORT=50002
RESEARCHMIND_WS_HOST=127.0.0.1
RESEARCHMIND_WS_PORT=50003

# MCP 服务
PAPER_SEARCH_MCP_HOST=127.0.0.1
PAPER_SEARCH_MCP_PORT=50004
SIMULATION_MCP_HOST=127.0.0.1
SIMULATION_MCP_PORT=50005
DATABASE_MCP_HOST=127.0.0.1
DATABASE_MCP_PORT=50006
```

> **提示 (Tip)**
> - 如果不使用反向代理，可将 `VITE_API_URL` 改为 `http://127.0.0.1:50002/api`、`VITE_WS_URL` 改为 `ws://127.0.0.1:50003/ws`，并同步调整 `VITE_API_PORT` 与 `VITE_WS_PORT`。
> - 对外发布时，把 `*_HOST` 设置为 `0.0.0.0`，其它保持不变即可，由代理补全域名。

## 🛑 停止服务 (Stop Services)

按 `Ctrl+C` 停止所有服务，或使用：
```bash
./stop_linux.sh
```

## ✨ 启动脚本特性 (Start Script Features)

### 🔧 自动化功能 (Automation)
- ✅ **环境检查 (Environment Check)** - 自动检测uv、npm、Python等依赖
- ✅ **IP地址检测 (IP Detection)** - 自动获取本机IP地址
- ✅ **端口冲突处理 (Port Conflict Handling)** - 检测并处理端口占用
- ✅ **配置文件生成 (Config Generation)** - 自动创建正确的.env配置
- ✅ **服务健康检查 (Health Check)** - 验证服务启动状态
- ✅ **防火墙配置 (Firewall Config)** - 自动添加防火墙规则（Linux）
- ✅ **服务监控 (Service Monitoring)** - 实时监控服务运行状态

### 🎯 智能特性 (Smart Features)
- 🔄 **强制重启 (Force Restart)** - 自动停止现有服务并重启
- 🌐 **外部访问 (External Access)** - 正确配置外部IP访问
- 📊 **状态显示 (Status Display)** - 清晰显示所有服务状态和访问地址
- 🚀 **一键启动 (One-Click Start)** - 无需手动配置，一键完成所有设置

## 📝 日志文件 (Log Files)

- `logs/backend.log` – WebSocket/HTTP 主服务
- `logs/paper_search.log` – 论文检索 MCP
- `logs/simulation.log` – 仿真 MCP
- `logs/database.log` – 数据库 MCP
- `logs/frontend.log` – 前端构建/运行

## 🛠️ 故障排除 (Troubleshooting)

### 1. 前端依赖加载错误 (ERR_CONTENT_LENGTH_MISMATCH)

如果在访问前端时遇到 `ERR_CONTENT_LENGTH_MISMATCH` 错误，通常是由于 Nginx 缓冲设置导致的。系统已自动配置了解决方案：

1. 确保使用了最新版本的 Nginx 配置文件
2. 重启 Nginx 服务使配置生效：
   ```bash
   # Windows
   nginx -s reload
   
   # Linux
   sudo systemctl reload nginx
   ```

### 2. 端口冲突 (Port Conflict)

如果遇到端口冲突错误，可以修改 `.env` 文件中的端口配置。
