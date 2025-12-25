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
from .error_monitor import get_error_monitor

logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server for ResearchMind"""

    # 全局实例（用于从HTTP端点访问WebSocket连接）
    _instance: Optional['WebSocketServer'] = None

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

        # 设置全局实例
        WebSocketServer._instance = self

    @classmethod
    def get_instance(cls) -> Optional['WebSocketServer']:
        """
        获取全局WebSocket服务器实例

        Returns:
            WebSocket服务器实例，如果未初始化则返回None
        """
        return cls._instance
    
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
            server_config.WEBSOCKET_PORT,
            max_size=50 * 1024 * 1024,  # 50MB - 支持大文件上传（base64 编码后会增大约 33%）
            ping_interval=25,  # 每 25 秒发送 ping (保持连接活跃)
            ping_timeout=300,  # 300 秒 (5分钟) 内未收到 pong 才断开，大幅容忍网络延迟或客户端卡顿
        ):
            logger.info("✅ Server started, waiting for connections...")
            logger.info(f"📦 Max message size: 50MB (supports ~37MB original files after base64 encoding)")
            logger.info(f"💓 Heartbeat: ping every 25s, timeout 300s")
            import asyncio
            await asyncio.Future()  # Keep server running
    
    async def handle_client(self, websocket, path):
        """
        Handle client connection

        Args:
            websocket: WebSocket connection
            path: Connection path (e.g., /ws/client_xxx)
        """
        # Extract client_id from path (e.g., /ws/client_xxx -> client_xxx)
        # If not provided, generate a new one
        client_id = None
        if path:
            # Path format: /ws/client_xxx or /client_xxx
            parts = path.strip('/').split('/')
            if len(parts) >= 2 and parts[0] == 'ws':
                client_id = parts[1]
            elif len(parts) == 1 and parts[0] != 'ws':
                client_id = parts[0]

        if not client_id or client_id == 'ws':
            client_id = str(uuid.uuid4())
            logger.info(f"🆕 Generated new client_id: {client_id}")
        else:
            logger.info(f"📦 Using client_id from URL: {client_id}")

        self.connected_clients[client_id] = websocket
        self.client_sessions[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "path": path,
            "authenticated": False,
            "authenticated_user_id": None,
            "user": None
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
                    # 🔒 添加消息大小检查，防止解析超大消息导致内存溢出
                    if len(message) > 50 * 1024 * 1024:  # 50MB
                        logger.error(f"❌ Message too large from client {client_id}: {len(message)} bytes")
                        await self.message_handler.send_error(websocket, "消息过大，请减小文件大小")
                        continue

                    data = json.loads(message)

                    # Extract or create session_id
                    session_id = data.get("sessionId") or data.get("session_id")

                    # If no session_id provided, generate a proper session_id (not default_xxx)
                    if not session_id:
                        # 🔧 修复：生成正确格式的 session_id，不使用 default 前缀
                        import time
                        import random
                        import string
                        timestamp = int(time.time() * 1000)
                        random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                        session_id = f"session_{timestamp}_{random_id}"
                        logger.info(f"🆕 Generated new session_id: {session_id}")

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

                    # 🔒 使用 asyncio.wait_for 添加超时保护，防止消息处理卡死
                    import asyncio
                    try:
                        await asyncio.wait_for(
                            self.message_handler.handle_message(
                                client_id=client_id,
                                websocket=websocket,
                                data=data,
                                agent_coordinator=self.agent_coordinator,
                                session_id=session_id  # Pass session_id
                            ),
                            timeout=600.0  # 10 分钟超时（适应长时间计算任务）
                        )
                    except asyncio.TimeoutError:
                        logger.error(f"❌ Message handling timeout for client {client_id}, session {session_id}")
                        await self.message_handler.send_error(
                            websocket,
                            "处理超时（10分钟），请稍后重试或减小任务规模"
                        )
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON message from client {client_id}: {e}")
                    # 🔒 记录错误到监控器
                    get_error_monitor().record_error(
                        error_type="json_decode_error",
                        error_message=str(e),
                        is_fatal=False,
                        context={'client_id': client_id}
                    )
                    try:
                        await self.message_handler.send_error(websocket, "消息格式错误，请检查 JSON 格式")
                    except Exception:
                        pass  # 忽略发送错误消息时的异常
                except Exception as e:
                    logger.error(f"❌ Error processing message from client {client_id}: {e}", exc_info=True)
                    # 🔒 记录错误到监控器
                    get_error_monitor().record_error(
                        error_type="message_processing_error",
                        error_message=str(e),
                        is_fatal=False,
                        context={'client_id': client_id}
                    )
                    try:
                        await self.message_handler.send_error(websocket, f"处理失败: {str(e)}")
                    except Exception:
                        pass  # 忽略发送错误消息时的异常
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"🔌 Client disconnected: {client_id} (code: {e.code}, reason: {e.reason})")
        except websockets.exceptions.PayloadTooBig as e:
            logger.error(f"❌ Message too large from client {client_id}: {e}")
            try:
                await self.message_handler.send_error(
                    websocket,
                    "文件过大，请上传小于 37MB 的文件（base64 编码后不超过 50MB）"
                )
            except:
                pass
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

