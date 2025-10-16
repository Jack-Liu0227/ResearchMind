"""
WebSocket Server

Handles WebSocket connections and client management.
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

import websockets
from websockets.server import serve

from .config import server_config
from .message_handler import MessageHandler
from .agent_coordinator import AgentCoordinator
from .session_manager import SessionManager

logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server for ResearchMind"""
    
    def __init__(self, agent_coordinator: AgentCoordinator):
        """
        Initialize WebSocket server
        
        Args:
            agent_coordinator: Agent coordinator instance
        """
        self.agent_coordinator = agent_coordinator
        self.message_handler = MessageHandler()
        self.connected_clients: Dict[str, Any] = {}
        self.client_sessions: Dict[str, Dict] = {}
    
    async def start(self):
        """Start WebSocket server"""
        logger.info("=" * 60)
        logger.info("🚀 ResearchMind WebSocket Server")
        logger.info("=" * 60)
        logger.info(f"📡 WebSocket endpoint: ws://{server_config.WEBSOCKET_HOST}:{server_config.WEBSOCKET_PORT}")
        logger.info(f"🔗 Frontend connection: ws://{server_config.WEBSOCKET_HOST}:{server_config.WEBSOCKET_PORT}/{{client_id}}")
        logger.info("")
        logger.info("🤖 Available Agents:")
        
        from .config import agent_config
        for agent_id, config in agent_config.AGENTS.items():
            logger.info(f"   {config['icon']} {config['name']} ({agent_id})")
        
        logger.info("")
        logger.info("Press Ctrl+C to stop server")
        logger.info("=" * 60)
        
        async with serve(
            self.handle_client,
            server_config.WEBSOCKET_HOST,
            server_config.WEBSOCKET_PORT
        ):
            logger.info("✅ Server started, waiting for connections...")
            import asyncio
            await asyncio.Future()  # Keep server running
    
    async def handle_client(self, websocket, path):
        """
        Handle client connection
        
        Args:
            websocket: WebSocket connection
            path: Connection path
        """
        client_id = str(uuid.uuid4())
        self.connected_clients[client_id] = websocket
        self.client_sessions[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "path": path
        }
        
        logger.info(f"✅ Client connected: {client_id}")
        logger.info(f"📊 Total clients: {len(self.connected_clients)}")
        
        try:
            # Send welcome message
            await self.message_handler.send_message(websocket, "connected", {
                "clientId": client_id,
                "message": "Connected to ResearchMind",
                "timestamp": datetime.now().isoformat()
            })
            
            # Send agents list
            await self.message_handler.send_agent_list(websocket)
            
            # Handle messages
            async for message in websocket:
                try:
                    data = json.loads(message)

                    # Extract or create session_id
                    session_id = data.get("sessionId") or data.get("session_id")

                    # If no session_id provided, create a default one for this client
                    if not session_id:
                        session_id = f"default_{client_id}"
                        logger.debug(f"No session_id provided, using default: {session_id}")

                    # Ensure session exists
                    if not SessionManager.get_session(session_id):
                        agent_id = data.get("agentId") or data.get("agent_id")
                        SessionManager.create_session(
                            session_id=session_id,
                            client_id=client_id,
                            agent_id=agent_id,
                            title=data.get("title", f"Session {session_id[:8]}")
                        )
                        logger.info(f"🆕 Auto-created session: {session_id}")

                    await self.message_handler.handle_message(
                        client_id=client_id,
                        websocket=websocket,
                        data=data,
                        agent_coordinator=self.agent_coordinator,
                        session_id=session_id  # Pass session_id
                    )
                except json.JSONDecodeError:
                    logger.error(f"❌ Invalid JSON message: {message}")
                    await self.message_handler.send_error(websocket, "Invalid message format")
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}", exc_info=True)
                    await self.message_handler.send_error(websocket, f"Error processing message: {str(e)}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 Client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"❌ Client error: {e}", exc_info=True)
        finally:
            # Cleanup
            if client_id in self.connected_clients:
                del self.connected_clients[client_id]
            if client_id in self.client_sessions:
                del self.client_sessions[client_id]
            
            # Clear agent sessions
            self.agent_coordinator.clear_all_sessions(client_id)
            
            logger.info(f"🗑️ Cleaned up client: {client_id}")
            logger.info(f"📊 Remaining clients: {len(self.connected_clients)}")
    
    def get_connected_clients_count(self) -> int:
        """Get number of connected clients"""
        return len(self.connected_clients)
    
    def get_client_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get client information"""
        if client_id in self.client_sessions:
            return {
                **self.client_sessions[client_id],
                "connected": client_id in self.connected_clients,
                "sessions": self.agent_coordinator.get_client_session_count(client_id)
            }
        return None

