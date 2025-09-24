# 快速入门

ResearchMind是一个基于Google Agent Development Kit (ADK) 和 Model Context Protocol (MCP) 的智能科研助手。它提供了一个全面的多智能体系统，用于科学研究，从文献综述到实验设计。

> 🇺🇸 **English Users**: [Click here for English version](../get-started.md) | **英文用户**: [点击这里查看英文版本](../get-started.md)

## 什么是ResearchMind？

ResearchMind帮助研究人员：
- 🔍 **进行全面的文献综述** 使用ArXiv、Google Scholar和网络搜索
- 🗄️ **搜索材料数据库** 包括Materials Project、OQMD和NOMAD
- ⚛️ **运行多尺度仿真** 集成MatterSim
- 🧪 **设计优化实验** 使用DOE和风险评估
- 🤖 **编排复杂工作流** 通过智能体协调

## 核心特性

### 🏗️ 多智能体架构
- **协调器智能体**: 编排研究工作流并管理子智能体
- **文献智能体**: 专门从事学术论文搜索和分析
- **数据库智能体**: 材料数据库查询和结构生成专家
- **仿真智能体**: 处理计算建模和性质预测
- **实验智能体**: 设计实验并评估风险

### 🔄 智能工作流
- **混合模式**: 根据任务复杂度自动选择最优策略
- **顺序模式**: 逐步深度研究（文献→数据库→仿真→实验）
- **并行模式**: 并发执行以快速验证
- **专项模式**: 领域特定的优化工作流

### 🛠️ MCP工具生态系统
- **标准化集成**: 所有工具都遵循Model Context Protocol标准
- **模块化设计**: 易于扩展新工具和功能
- **实时处理**: 异步执行和实时进度跟踪
- **错误处理**: 强大的错误恢复和回退机制

## 快速导航

| 部分 | 描述 | 完成时间 |
|------|------|----------|
| [安装](#安装) | 设置ResearchMind环境 | 5分钟 |
| [快速教程](#快速教程) | 创建您的第一个研究工作流 | 10分钟 |
| [智能体教程](#智能体教程) | 学习多智能体协调 | 20分钟 |
| [MCP工具](#mcp工具) | 探索可用的研究工具 | 15分钟 |
| [部署](#部署) | 部署到生产环境 | 30分钟 |

## 安装

### 先决条件
- Python 3.9或更高版本
- 已安装Google ADK
- Git用于版本控制

### 安装ResearchMind

```bash
# 克隆仓库
git clone https://github.com/your-org/researchmind.git
cd researchmind

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置环境

```bash
# 复制环境模板
cp .env.example .env

# 编辑.env文件，填入您的API密钥
export GOOGLE_API_KEY="your_google_api_key"
export MATERIALS_PROJECT_API_KEY="your_mp_api_key"  # 可选
export MATTERSIM_LICENSE="your_mattersim_license"   # 可选
```

### 验证安装

```bash
# 运行系统测试
python test_agents.py

# 预期输出：
# ✅ 所有测试通过！ResearchMind已就绪！
```

## 快速教程

### 1. 交互模式（推荐初学者）

```bash
python main_mcp.py --interactive
```

尝试这些示例查询：
- "研究锂电池材料"
- "寻找钙钛矿太阳能电池结构"
- "设计石墨烯合成实验"

### 2. 直接研究模式

```bash
# 混合工作流（推荐）
python main_mcp.py --research "超导材料" --workflow hybrid

# 顺序工作流用于深度研究
python main_mcp.py --research "量子点" --workflow sequential

# 并行工作流用于快速探索
python main_mcp.py --research "二维材料" --workflow parallel
```

### 3. 专业智能体模式

```bash
# 文献研究专家
python main_mcp.py --agent literature_agent --research "材料科学中的机器学习"

# 数据库搜索专家
python main_mcp.py --agent database_agent --research "高熵合金"

# 仿真专家
python main_mcp.py --agent simulation_agent --research "电子性质"

# 实验设计专家
python main_mcp.py --agent experiment_agent --research "催化剂合成"
```

### 4. Web界面模式

```bash
# 启动ADK web界面
python main_mcp.py --web --port 8080
```

然后在浏览器中打开 http://localhost:8080 并选择 `research_coordinator` 智能体。

## 智能体教程

### 理解智能体层次结构

ResearchMind使用分层多智能体系统：

```
根协调器
├── 文献智能体（+ 文献工作流）
├── 数据库智能体（+ 材料发现工作流）
├── 仿真智能体（+ 计算工作流）
├── 实验智能体（+ 实验工作流）
└── 工作流编排器
    ├── 顺序工作流
    ├── 并行工作流
    ├── 混合工作流
    └── 专项工作流
```

### 创建自定义工作流

```python
from agents import literature_agent, database_agent, simulation_agent
from google.adk.agents.workflow_agents import SequentialAgent

# 创建自定义研究流水线
custom_workflow = SequentialAgent(
    name="materials_discovery_pipeline",
    instruction="通过系统研究发现新材料",
    agents=[literature_agent, database_agent, simulation_agent]
)
```

### 智能体通信

智能体通过以下方式通信：
- **任务委派**: 父智能体向子智能体分配任务
- **结果聚合**: 工作流智能体收集和综合结果
- **上下文共享**: 共享内存和状态管理
- **错误传播**: 跨智能体边界的强大错误处理

## MCP工具

### 文献研究工具
- `search_arxiv`: 使用高级过滤搜索ArXiv论文
- `search_scholar`: Google Scholar集成和引用分析
- `search_web`: 网络搜索获取更广泛的研究背景
- `analyze_paper`: 提取方法论和关键发现
- `generate_report`: 创建结构化文献综述

### 材料数据库工具
- `search_structure`: 查询Materials Project、OQMD、NOMAD数据库
- `generate_structure`: 使用CrystaLLM进行AI驱动的结构生成
- `predict_properties`: 使用ML模型进行性质预测
- `validate_structure`: 稳定性和可行性分析
- `visualize_structure`: 3D结构可视化

### 仿真工具
- `setup_calculation`: 配置计算参数
- `run_mattersim`: 执行MatterSim计算
- `analyze_results`: 处理和解释仿真数据
- `optimize_structure`: 结构优化工作流
- `calculate_properties`: 电子、机械、热性质

### 实验设计工具
- `design_experiment`: 创建实验协议
- `optimize_parameters`: 统计优化（DOE、贝叶斯）
- `assess_risk`: 安全性和可行性评估
- `generate_protocol`: 详细实验程序
- `estimate_cost`: 资源和时间估算

## 下一步

### 了解更多
- [智能体配置](agent-config.md) - 自定义智能体行为
- [MCP集成](mcp-integration.md) - 添加新工具和功能
- [工作流模式](workflow-patterns.md) - 高级编排技术
- [部署指南](deployment.md) - 生产部署策略

### 示例项目
- [电池材料研究](samples/battery-materials.md)
- [催化剂发现](samples/catalyst-discovery.md)
- [二维材料探索](samples/2d-materials.md)
- [药物发现流水线](samples/drug-discovery.md)

### 社区
- [GitHub仓库](https://github.com/your-org/researchmind)
- [讨论论坛](https://github.com/your-org/researchmind/discussions)
- [问题跟踪](https://github.com/your-org/researchmind/issues)
- [贡献指南](contributing.md)

---

准备好加速您的研究了吗？从[快速教程](#快速教程)开始，或探索我们的[示例项目](samples/)来看看ResearchMind的实际应用！


