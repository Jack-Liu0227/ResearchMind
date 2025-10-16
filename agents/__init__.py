"""
ResearchMind Agents Package

This package contains the Google ADK-based agents for the ResearchMind system.
"""

# Handle Google ADK imports gracefully
try:
    from .agent import research_coordinator, root_agent
except ImportError as e:
    print(f"Warning: Could not import main agents (Google ADK may not be available): {e}")
    research_coordinator = None
    root_agent = None

try:
    from .config import settings, AgentConfig
except ImportError:
    settings = None
    AgentConfig = None

# Import specific sub-agents
try:
    from .deep_research_agent.agent import root_agent as deep_research_agent
except ImportError:
    deep_research_agent = None

try:
    from .database_agent.agent import root_agent as database_agent
except ImportError:
    database_agent = None
    
try:
    from .simulation_agent.agent import root_agent as simulation_agent
except ImportError:
    simulation_agent = None

def get_available_agents():
    """获取所有可用的Agent实例"""
    from .agent import Agent
    
    agents = []
    
    # 创建模拟的Agent实例用于演示
    if deep_research_agent:
        agents.append(Agent(
            id="deep_research_agent",
            name="文献研究助手",
            description="专门用于文献搜索、分析和研究的AI助手，可以帮您查找相关论文、分析研究趋势。"
        ))
    
    if database_agent:
        agents.append(Agent(
            id="database_agent", 
            name="数据库查询助手",
            description="专门用于材料数据库查询和数据检索的AI助手，可以帮您查找材料属性和实验数据。"
        ))
    
    if simulation_agent:
        agents.append(Agent(
            id="simulation_agent",
            name="仿真计算助手", 
            description="专门用于分子建模和计算仿真的AI助手，可以帮您进行分子动力学模拟和量子化学计算。"
        ))
    
    # 如果没有可用的特定Agent，创建一个通用Agent
    if not agents:
        agents.append(Agent(
            id="general_agent",
            name="通用研究助手",
            description="通用的AI研究助手，可以帮助您进行各种研究任务，包括文献调研、数据分析等。"
        ))
    
    return agents

__all__ = [
    "research_coordinator",
    "root_agent",
    "settings", 
    "AgentConfig",
    "deep_research_agent",
    "database_agent",
    "simulation_agent",
    "get_available_agents"
]
