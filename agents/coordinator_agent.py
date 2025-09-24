"""
ResearchMind协调器智能体
基于Google ADK的主协调器，管理所有子智能体和MCP工具
"""

import os
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# 导入子智能体
from .literature_agent import literature_agent, literature_workflow_agent
from .database_agent import database_agent, materials_discovery_agent
from .simulation_agent import simulation_agent, computational_workflow_agent
from .experiment_agent import experiment_agent, experimental_workflow_agent
from .workflow_agent import (
    sequential_workflow_agent,
    parallel_workflow_agent,
    hybrid_workflow_agent,
    specialized_workflow_agent
)

# 主协调器智能体 - 这是ADK Web界面会识别的根智能体
root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name='research_coordinator',
    instruction='''你是ResearchMind的主协调器智能体，专门为科研工作者提供全流程的智能化支持。

你的核心能力包括：

🔬 **科研流程管理**
- 理解用户的科研需求和目标
- 制定合适的研究策略和工作流程
- 协调各专业智能体完成具体任务
- 整合多个来源的信息和结果

📚 **文献调研支持**
- 使用ArXiv、Google Scholar等数据库搜索相关论文
- 分析论文内容，提取关键信息和研究方法
- 生成结构化的文献调研报告
- 识别研究趋势和知识空白

🗄️ **数据库检索服务**
- 搜索Materials Project、OQMD等材料数据库
- 查找和分析晶体结构数据
- 使用CrystaLLM生成新的晶体结构
- 预测材料性质和特性

⚛️ **仿真计算协调**
- 使用MatterSim进行原子级精确计算
- 设置和优化仿真参数
- 分析仿真结果和物理性质
- 提供多尺度建模支持

🧪 **实验设计优化**
- 基于文献和仿真结果设计实验方案
- 优化实验参数和条件
- 评估实验风险和可行性
- 生成详细的实验操作协议

**工作原则：**
1. 始终以用户的科研目标为导向
2. 提供基于证据的建议和分析
3. 整合多个信息源，确保结果的可靠性
4. 用清晰、专业的语言与用户交流
5. 在必要时主动询问澄清问题

**智能体协调能力：**
- 根据任务复杂度选择合适的子智能体
- 协调多个智能体的并行或顺序执行
- 整合不同智能体的结果和建议
- 管理工作流程和任务依赖关系
- 优化资源分配和执行效率

**工作流模式：**
- **顺序模式**: 适合复杂研究的逐步深入
- **并行模式**: 适合时间紧迫的快速研究
- **混合模式**: 根据情况灵活调整策略
- **专项模式**: 针对特定研究类型的定制流程

**响应格式：**
- 使用结构化的格式组织信息
- 提供具体的数据和引用
- 包含可行的下一步建议
- 标明信息来源和可信度
- 说明选择的工作流策略和原因

请根据用户的具体需求，选择最适合的智能体和工作流来完成任务。''',
    
    tools=[
        # 文献检索MCP工具集
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=[os.path.join(os.path.dirname(__file__), '..', 'mcp_servers', 'literature', 'server.py')],
                ),
            ),
            tool_filter=[
                'search_arxiv', 
                'search_scholar', 
                'search_web',
                'analyze_paper', 
                'generate_report'
            ]
        ),
        
        # 材料数据库MCP工具集
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=[os.path.join(os.path.dirname(__file__), '..', 'mcp_servers', 'materials', 'server.py')],
                    env={'MATERIALS_PROJECT_API_KEY': os.getenv('MATERIALS_PROJECT_API_KEY', '')}
                ),
            ),
            tool_filter=[
                'search_structure',
                'generate_structure',
                'predict_properties',
                'validate_structure',
                'visualize_structure'
            ]
        ),
        
        # 仿真计算MCP工具集
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=[os.path.join(os.path.dirname(__file__), '..', 'mcp_servers', 'simulation', 'server.py')],
                    env={
                        'MATTERSIM_LICENSE': os.getenv('MATTERSIM_LICENSE', ''),
                        'CUDA_VISIBLE_DEVICES': os.getenv('CUDA_VISIBLE_DEVICES', '0')
                    }
                ),
            ),
            tool_filter=[
                'setup_calculation',
                'run_mattersim',
                'analyze_results',
                'optimize_structure',
                'calculate_properties'
            ]
        ),
        
        # 实验设计MCP工具集
        MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=[os.path.join(os.path.dirname(__file__), '..', 'mcp_servers', 'experiment', 'server.py')],
                    env={
                        'SAFETY_DATABASE_PATH': os.getenv('SAFETY_DATABASE_PATH', ''),
                        'COST_DATABASE_PATH': os.getenv('COST_DATABASE_PATH', '')
                    }
                ),
            ),
            tool_filter=[
                'design_experiment',
                'optimize_parameters',
                'assess_risk',
                'generate_protocol',
                'estimate_cost'
            ]
        )
    ],

    # 子智能体 - 专业领域专家
    sub_agents=[
        literature_agent,           # 文献调研专家
        database_agent,            # 数据库检索专家
        simulation_agent,          # 仿真计算专家
        experiment_agent,          # 实验设计专家

        # 工作流协调智能体
        literature_workflow_agent,     # 文献调研工作流
        materials_discovery_agent,     # 材料发现工作流
        computational_workflow_agent,  # 计算工作流
        experimental_workflow_agent,   # 实验工作流

        # 高级工作流智能体
        sequential_workflow_agent,     # 顺序工作流
        parallel_workflow_agent,       # 并行工作流
        hybrid_workflow_agent,         # 混合工作流
        specialized_workflow_agent     # 专项工作流
    ]
)
