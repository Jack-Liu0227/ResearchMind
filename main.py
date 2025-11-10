#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ResearchMind Main Entry Point

Unified server that runs both WebSocket and HTTP services.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Setup UTF-8 encoding for Windows
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env (override OS env if provided)
try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    logger.info("✅ Loaded environment variables from .env")
except Exception as _e:
    logger.warning(f"⚠️ Could not load .env automatically: {_e}")

# Import services
from services.config import server_config
from services.websocket_server import WebSocketServer
from services.http_server import HTTPServer
from services.agent_coordinator import AgentCoordinator
from services.image_handler import ImageHandler
from services.json_repair_patch import apply_json_repair_patch
from services.database import init_db

# Apply JSON repair patch for DeepSeek compatibility
apply_json_repair_patch()
logger.info("✅ JSON repair patch applied for LLM tool calls")

# Initialize database
try:
    init_db()
    logger.info("✅ Database initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize database: {e}")
    sys.exit(1)

# Import agents
try:
    from agents.deep_research_agent.agent import root_agent as deep_research_agent
    from agents.database_agent.agent import root_agent as database_agent
    from agents.simulation_agent.agent import root_agent as simulation_agent
    from agents.agent import research_coordinator
    logger.info("✅ Agents imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import agents: {e}")
    logger.error("Please ensure all dependencies are installed: uv sync")
    sys.exit(1)


async def start_http_server(http_server: HTTPServer):
    """Start HTTP server"""
    import uvicorn

    config = uvicorn.Config(
        http_server.get_app(),
        host=server_config.HTTP_HOST,
        port=server_config.HTTP_PORT,
        log_level="info",
        timeout_keep_alive=300,  # 5 分钟 keep-alive，适应长时间计算任务
        timeout_graceful_shutdown=30,  # 优雅关闭超时 30 秒
        limit_concurrency=100,  # 最大并发连接数
        backlog=2048  # TCP backlog 队列大小
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("🚀 ResearchMind Unified Server")
    logger.info("=" * 60)
    logger.info("")

    # Initialize agents
    agents = {
        "research_coordinator": research_coordinator,
        "deep_research_agent": deep_research_agent,
        "database_agent": database_agent,
        "simulation_agent": simulation_agent,
    }

    # Initialize agent coordinator
    agent_coordinator = AgentCoordinator(agents)
    logger.info(f"✅ Agent coordinator initialized with {len(agents)} agents")

    # Initialize HTTP server
    http_server = HTTPServer()
    logger.info("✅ HTTP server initialized")

    # Set base URL for image handler
    # 使用 RESEARCHMIND_HTTP_HOST + RESEARCHMIND_HTTP_PORT
    import os
    api_host = os.getenv("RESEARCHMIND_HTTP_HOST", server_config.HTTP_HOST)
    api_port = os.getenv("RESEARCHMIND_HTTP_PORT", "50002")  # Changed from 50006 to 50002
    ImageHandler.set_base_url(api_host, int(api_port))
    logger.info(f"✅ Image handler configured: {ImageHandler.BASE_URL}")

    # Initialize WebSocket server
    websocket_server = WebSocketServer(agent_coordinator)
    logger.info("✅ WebSocket server initialized")

    logger.info("")
    logger.info("📡 Services:")
    logger.info(f"   - WebSocket: ws://{server_config.WEBSOCKET_HOST}:{server_config.WEBSOCKET_PORT}")
    logger.info(f"   - HTTP API:  http://{server_config.HTTP_HOST}:{server_config.HTTP_PORT}")
    logger.info(f"   - API Docs:  http://{server_config.HTTP_HOST}:{server_config.HTTP_PORT}/docs")
    logger.info("")
    logger.info("Press Ctrl+C to stop all servers")
    logger.info("=" * 60)
    logger.info("")

    # Run both servers concurrently with proper error handling
    try:
        # Create tasks for both servers
        http_task = asyncio.create_task(start_http_server(http_server))
        ws_task = asyncio.create_task(websocket_server.start())

        # Wait for both tasks
        await asyncio.gather(http_task, ws_task)
    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 60)
        logger.info("👋 Shutting down servers...")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Server stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

