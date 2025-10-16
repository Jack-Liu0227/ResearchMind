"""
Configuration Management for ResearchMind Services
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ServerConfig:
    """Server configuration"""

    # WebSocket Server
    WEBSOCKET_HOST = os.getenv("RESEARCHMIND_HOST", "0.0.0.0")
    WEBSOCKET_PORT = int(os.getenv("RESEARCHMIND_WS_PORT", os.getenv("RESEARCHMIND_PORT", "50002")))

    # HTTP API Server
    HTTP_HOST = os.getenv("RESEARCHMIND_HOST", "localhost")
    HTTP_PORT = int(os.getenv("RESEARCHMIND_HTTP_PORT", os.getenv("RESEARCHMIND_PORT", "8000")))

    # Debug: Print configuration on load
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print(f"🔧 Configuration loaded:")
        print(f"   - RESEARCHMIND_HOST: {os.getenv('RESEARCHMIND_HOST')}")
        print(f"   - RESEARCHMIND_PORT: {os.getenv('RESEARCHMIND_PORT')}")
        print(f"   - RESEARCHMIND_HTTP_PORT: {os.getenv('RESEARCHMIND_HTTP_PORT')}")
        print(f"   - RESEARCHMIND_WS_PORT: {os.getenv('RESEARCHMIND_WS_PORT')}")
        print(f"   - HTTP_HOST: {cls.HTTP_HOST}")
        print(f"   - HTTP_PORT: {cls.HTTP_PORT}")
        print(f"   - WEBSOCKET_HOST: {cls.WEBSOCKET_HOST}")
        print(f"   - WEBSOCKET_PORT: {cls.WEBSOCKET_PORT}")
    
    # CORS Settings
    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # Static Files
    STATIC_FILES_ROOT = os.path.abspath(os.path.dirname(__file__) + "/..")
    PHONON_RESULTS_DIR = os.path.join(STATIC_FILES_ROOT, "mcp_servers", "simulation", "phonon_results")
    GENERATED_STRUCTURES_DIR = os.path.join(STATIC_FILES_ROOT, "mcp_servers", "simulation", "crystallm", "generated_structures")
    
    # Logging
    LOG_LEVEL = os.getenv("RESEARCHMIND_LOG_LEVEL", "INFO")
    DEBUG = os.getenv("RESEARCHMIND_DEBUG", "false").lower() == "true"


class AgentConfig:
    """Agent configuration"""

    AGENTS = {
        "research_coordinator": {
            "name": "研究协调助手",
            "icon": "🧠",
            "description": "智能协调文献、数据库和仿真任务",
        },
        "deep_research_agent": {
            "name": "文献研究助手",
            "icon": "📚",
            "description": "ArXiv + Tavily 双源搜索，智能分析",
        },
        "database_agent": {
            "name": "数据库查询助手",
            "icon": "🗄️",
            "description": "查询 MP, OQMD, COD, AFLOW 数据库",
        },
        "simulation_agent": {
            "name": "仿真计算助手",
            "icon": "🔬",
            "description": "结构生成、热导率、能量计算",
        },
    }


class MCPConfig:
    """MCP Server configuration"""

    # Use environment variables for MCP server URLs (for Docker support)
    # Default to localhost for local development
    PAPER_SEARCH_HOST = os.getenv("PAPER_SEARCH_HOST", "127.0.0.1")
    DATABASE_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
    SIMULATION_HOST = os.getenv("SIMULATION_HOST", "127.0.0.1")

    SERVERS = {
        "paper_search": {
            "name": "Paper Search MCP",
            "url": f"http://{PAPER_SEARCH_HOST}:50005/sse",
            "port": 50005,
        },
        "database": {
            "name": "Database MCP",
            "url": f"http://{DATABASE_HOST}:50003/sse",
            "port": 50003,
        },
        "simulation": {
            "name": "Simulation MCP",
            "url": f"http://{SIMULATION_HOST}:50004/sse",
            "port": 50004,
        },
    }


class DataFormatConfig:
    """Data format configuration"""
    
    # Source types
    SOURCE_TYPES = ["MP", "OQMD", "COD", "AFLOW", "Generated", "Upload"]
    
    # Image types
    IMAGE_TYPES = ["phonon_dispersion", "phonon_dos", "band_structure", "dos"]
    
    # Structure data required fields
    STRUCTURE_REQUIRED_FIELDS = [
        "id",
        "formula",
        "spaceGroup",
        "latticeParameters",
        "atoms",
    ]
    
    # Image data required fields
    IMAGE_REQUIRED_FIELDS = [
        "name",
        "type",
        "url",
    ]


# Export configuration instances
server_config = ServerConfig()
agent_config = AgentConfig()
mcp_config = MCPConfig()
data_format_config = DataFormatConfig()

