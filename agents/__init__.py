"""
ResearchMind智能体包
包含所有专业智能体和工作流协调器
"""

# 导入主协调器智能体
from .coordinator_agent import root_agent

# 导入专业智能体
from .literature_agent import literature_agent, literature_workflow_agent
from .database_agent import database_agent, materials_discovery_agent
from .simulation_agent import simulation_agent, computational_workflow_agent
from .experiment_agent import experiment_agent, experimental_workflow_agent

# 导入工作流智能体
from .workflow_agent import (
    sequential_workflow_agent,
    parallel_workflow_agent,
    hybrid_workflow_agent,
    specialized_workflow_agent
)

# 智能体注册表
AGENT_REGISTRY = {
    # 主协调器
    'root_agent': root_agent,
    'research_coordinator': root_agent,
    
    # 专业智能体
    'literature_agent': literature_agent,
    'database_agent': database_agent,
    'simulation_agent': simulation_agent,
    'experiment_agent': experiment_agent,
    
    # 工作流智能体
    'literature_workflow': literature_workflow_agent,
    'materials_discovery': materials_discovery_agent,
    'computational_workflow': computational_workflow_agent,
    'experimental_workflow': experimental_workflow_agent,
    
    # 高级工作流
    'sequential_workflow': sequential_workflow_agent,
    'parallel_workflow': parallel_workflow_agent,
    'hybrid_workflow': hybrid_workflow_agent,
    'specialized_workflow': specialized_workflow_agent
}

# 智能体类型分类
AGENT_CATEGORIES = {
    'coordinators': ['root_agent', 'research_coordinator'],
    'specialists': ['literature_agent', 'database_agent', 'simulation_agent', 'experiment_agent'],
    'workflows': ['literature_workflow', 'materials_discovery', 'computational_workflow', 'experimental_workflow'],
    'advanced_workflows': ['sequential_workflow', 'parallel_workflow', 'hybrid_workflow', 'specialized_workflow']
}

# 智能体能力映射
AGENT_CAPABILITIES = {
    'literature_agent': ['文献检索', 'ArXiv搜索', 'Scholar搜索', '论文分析', '报告生成'],
    'database_agent': ['结构搜索', '材料数据库', 'CrystaLLM', '性质预测', '结构验证'],
    'simulation_agent': ['MatterSim计算', '结构优化', '性质计算', '仿真分析', '多尺度建模'],
    'experiment_agent': ['实验设计', '参数优化', '风险评估', '协议生成', '成本估算'],
    'sequential_workflow': ['顺序执行', '逐步验证', '风险控制', '深度研究'],
    'parallel_workflow': ['并行执行', '高效率', '快速验证', '资源密集'],
    'hybrid_workflow': ['自适应', '智能决策', '灵活调整', '资源优化'],
    'specialized_workflow': ['专项研究', '定制流程', '领域专门', '质量保证']
}

def get_agent(agent_name: str):
    """根据名称获取智能体实例"""
    return AGENT_REGISTRY.get(agent_name)

def list_agents(category: str = None):
    """列出所有智能体或指定类别的智能体"""
    if category and category in AGENT_CATEGORIES:
        return AGENT_CATEGORIES[category]
    return list(AGENT_REGISTRY.keys())

def get_agent_capabilities(agent_name: str):
    """获取智能体的能力描述"""
    return AGENT_CAPABILITIES.get(agent_name, [])

def recommend_agent(task_type: str):
    """根据任务类型推荐合适的智能体"""
    recommendations = {
        '文献调研': ['literature_agent', 'literature_workflow'],
        '材料搜索': ['database_agent', 'materials_discovery'],
        '仿真计算': ['simulation_agent', 'computational_workflow'],
        '实验设计': ['experiment_agent', 'experimental_workflow'],
        '综合研究': ['root_agent', 'hybrid_workflow'],
        '快速研究': ['parallel_workflow'],
        '深度研究': ['sequential_workflow'],
        '专项研究': ['specialized_workflow']
    }
    return recommendations.get(task_type, ['root_agent'])

# 导出所有智能体
__all__ = [
    'root_agent',
    'literature_agent', 'literature_workflow_agent',
    'database_agent', 'materials_discovery_agent', 
    'simulation_agent', 'computational_workflow_agent',
    'experiment_agent', 'experimental_workflow_agent',
    'sequential_workflow_agent', 'parallel_workflow_agent',
    'hybrid_workflow_agent', 'specialized_workflow_agent',
    'AGENT_REGISTRY', 'AGENT_CATEGORIES', 'AGENT_CAPABILITIES',
    'get_agent', 'list_agents', 'get_agent_capabilities', 'recommend_agent'
]
