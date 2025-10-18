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
    WEBSOCKET_HOST = os.getenv("RESEARCHMIND_WS_HOST", os.getenv("RESEARCHMIND_HOST", "0.0.0.0"))
    WEBSOCKET_PORT = int(os.getenv("RESEARCHMIND_WS_PORT", "50003"))

    # HTTP API Server
    HTTP_HOST = os.getenv("RESEARCHMIND_HTTP_HOST", os.getenv("RESEARCHMIND_HOST", "0.0.0.0"))
    HTTP_PORT = int(os.getenv("RESEARCHMIND_HTTP_PORT", "50002"))

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
    
    # CORS Settings - Support dynamic configuration
    @staticmethod
    def get_cors_origins():
        """Get CORS origins from environment or use defaults"""
        cors_env = os.getenv("RESEARCHMIND_ALLOW_ORIGINS")
        if cors_env:
            try:
                import json
                return json.loads(cors_env)
            except (json.JSONDecodeError, ValueError):
                pass

        # Default CORS origins
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:50001",
            "http://localhost:50006",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:50001",
            "http://127.0.0.1:50006",
            "http://0.0.0.0:3000",
            "http://0.0.0.0:5173",
            "http://0.0.0.0:50001",
            "http://0.0.0.0:50006",
            "*",  # Allow all origins for development
        ]

    CORS_ORIGINS = get_cors_origins()
    
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
    # 注意：
    # - 服务器监听使用 *_MCP_HOST 和 *_MCP_PORT
    # - 客户端连接使用 *_HOST 和 *_MCP_URL（支持分布式部署）

    # Paper Search MCP
    PAPER_SEARCH_HOST = os.getenv("PAPER_SEARCH_HOST", "127.0.0.1")
    PAPER_SEARCH_URL = os.getenv("PAPER_SEARCH_MCP_URL", "http://127.0.0.1:50004/sse")

    # Database MCP
    DATABASE_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
    DATABASE_URL = os.getenv("DATABASE_MCP_URL", "http://127.0.0.1:50006/sse")

    # Simulation MCP
    SIMULATION_HOST = os.getenv("SIMULATION_HOST", "127.0.0.1")
    SIMULATION_URL = os.getenv("SIMULATION_MCP_URL", "http://127.0.0.1:50005/sse")

    SERVERS = {
        "paper_search": {
            "name": "Paper Search MCP",
            "url": PAPER_SEARCH_URL,
            "port": 50004,
        },
        "database": {
            "name": "Database MCP",
            "url": DATABASE_URL,
            "port": 50006,
        },
        "simulation": {
            "name": "Simulation MCP",
            "url": SIMULATION_URL,
            "port": 50005,
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

