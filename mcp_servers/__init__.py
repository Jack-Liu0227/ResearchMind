"""
ResearchMind MCP Servers

This package contains Model Context Protocol (MCP) servers that provide 
specialized tools for research tasks including paper search, materials 
databases, simulations, and data analysis.
"""

__version__ = "1.0.0"

# Available MCP servers (实际已实现的服务器)
AVAILABLE_SERVERS = [
    "paper_search",      # 文献搜索与分析
    "database_call",     # 材料数据库查询
    "simulation",        # 仿真计算
]

# Default server ports
SERVER_PORTS = {
    "paper_search": 50002,
    "database_call": 50010,
    "simulation": 50003,
}

__all__ = ["AVAILABLE_SERVERS", "SERVER_PORTS"]