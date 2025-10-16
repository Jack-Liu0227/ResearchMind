"""
ResearchMind MCP Servers

This package contains Model Context Protocol (MCP) servers that provide 
specialized tools for research tasks including paper search, materials 
databases, simulations, and data analysis.
"""

__version__ = "1.0.0"

# Available MCP servers
AVAILABLE_SERVERS = [
    "paper_search",
    "materials", 
    "simulation",
    "data_analysis",
    "experiment",
    "rdkit",
    "structure_generate"
]

# Default server ports
SERVER_PORTS = {
    "paper_search": 5001,
    "materials": 5002,
    "simulation": 5003,
    "data_analysis": 5004,
    "experiment": 5005,
    "rdkit": 5006,
    "structure_generate": 5007,
}

__all__ = ["AVAILABLE_SERVERS", "SERVER_PORTS"]