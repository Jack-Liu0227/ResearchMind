"""
Message Handler

Handles WebSocket messages from clients, including chat messages, file uploads, etc.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from .config import agent_config
from .data_processor import DataProcessor

if TYPE_CHECKING:
    from .agent_coordinator import AgentCoordinator

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handle WebSocket messages"""

    def __init__(self):
        self.message_handlers = {
            "auth": self.handle_auth,  # WebSocket 认证
            "chat": self.handle_chat_message,
            "message": self.handle_chat_message,  # Alias for "chat"
            "upload_structure": self.handle_upload_structure,
            "upload_structures": self.handle_upload_structures,  # Multiple files
            "chat_with_attachments": self.handle_chat_with_attachments,
            "ping": self.handle_ping,
            "stop_response": self.handle_stop_response,  # 🆕 停止响应
            # WebSocket 统计查询
            "get_conversation_stats": self.handle_get_conversation_stats,
            "get_user_stats": self.handle_get_user_stats,
            "get_global_stats": self.handle_get_global_stats,
            "get_history": self.handle_get_history,  # 🆕 获取历史记录
            "recover_session": self.handle_recover_session,  # 🆕 重连后恢复会话状态
        }

    async def handle_message(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator",
        session_id: Optional[str] = None
    ) -> None:
        """
        Route message to appropriate handler

        Args:
            client_id: Client ID
            websocket: WebSocket connection
            data: Message data
            agent_coordinator: Agent coordinator instance
            session_id: Session ID (optional)
        """
        message_type = data.get("type")

        # Add session_id to data if not already present
        if session_id and "sessionId" not in data and "session_id" not in data:
            data["sessionId"] = session_id

        if message_type in self.message_handlers:
            handler = self.message_handlers[message_type]
            await handler(client_id, websocket, data, agent_coordinator)
        else:
            logger.warning(f"⚠️ Unknown message type: {message_type}")
            await self.send_error(websocket, f"Unknown message type: {message_type}")

    async def handle_chat_message(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        Handle chat message

        Args:
            client_id: Client ID
            websocket: WebSocket connection
            data: Message data with content, agentId, sessionId
            agent_coordinator: Agent coordinator instance
        """
        content = data.get("content", "")
        agent_id = data.get("agentId")
        session_id = data.get("sessionId")

        if not content:
            await self.send_error(websocket, "Message content cannot be empty")
            return

        if not agent_id:
            await self.send_error(websocket, "Please select an agent first")
            return

        logger.info(f"💬 [Client:{client_id}] [Agent:{agent_id}] Message: {content[:100]}...")

        # Delegate to agent coordinator
        await agent_coordinator.process_chat_message(
            client_id=client_id,
            websocket=websocket,
            content=content,
            agent_id=agent_id,
            session_id=session_id
        )

    async def handle_chat_with_attachments(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """Handle chat message that includes attachments (e.g., CIF content).

        Expects data like:
        {
          type: "chat_with_attachments",
          content: "请用这个CIF计算声子谱",
          agentId: "simulation_agent",
          sessionId: "...",
          attachments: [
            { filename: "struct.cif", content: "data_..." },
            ...
          ]
        }
        """
        content = data.get("content", "")
        agent_id = data.get("agentId")
        session_id = data.get("sessionId")
        attachments = data.get("attachments", [])

        if not content and not attachments:
            await self.send_error(websocket, "Message content or attachments required")
            return

        if not agent_id:
            await self.send_error(websocket, "Please select an agent first")
            return

        await agent_coordinator.process_chat_message(
            client_id=client_id,
            websocket=websocket,
            content=content or "",
            agent_id=agent_id,
            session_id=session_id,
            attachments=attachments
        )

    async def handle_upload_structure(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        Handle structure upload

        Args:
            client_id: Client ID
            websocket: WebSocket connection
            data: Message data with structure data
            agent_coordinator: Agent coordinator instance
        """
        structure_data = data.get("structure")

        if not structure_data:
            await self.send_error(websocket, "No structure data provided")
            return

        logger.info(f"📤 [Client:{client_id}] Uploading structure: {structure_data.get('formula', 'Unknown')}")

        # Process uploaded structure
        success = await DataProcessor.process_uploaded_structure(
            structure_data=structure_data,
            websocket=websocket,
            agent_id="upload"
        )

        if success:
            await self.send_message(websocket, "upload_success", {
                "message": "Structure uploaded successfully",
                "structureId": structure_data.get("id")
            })
        else:
            await self.send_error(websocket, "Failed to process uploaded structure")

    async def handle_upload_structures(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        Handle multiple structure uploads

        Args:
            client_id: Client ID
            websocket: WebSocket connection
            data: Message data with structures array
            agent_coordinator: Agent coordinator instance
        """
        structures = data.get("structures", [])

        if not structures:
            await self.send_error(websocket, "No structures provided")
            return

        logger.info(f"📤 [Client:{client_id}] Uploading {len(structures)} structures")

        success_count = 0
        failed_count = 0
        uploaded_ids = []

        for structure_data in structures:
            try:
                # Process each uploaded structure
                success = await DataProcessor.process_uploaded_structure(
                    structure_data=structure_data,
                    websocket=websocket,
                    agent_id="upload"
                )

                if success:
                    success_count += 1
                    uploaded_ids.append(structure_data.get("id"))
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to process structure: {e}")
                failed_count += 1

        # Send summary
        await self.send_message(websocket, "upload_complete", {
            "message": f"Uploaded {success_count} structures successfully",
            "successCount": success_count,
            "failedCount": failed_count,
            "uploadedIds": uploaded_ids
        })

    async def handle_ping(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """Handle ping message"""
        await self.send_message(websocket, "pong", {
            "timestamp": datetime.now().isoformat()
        })
    async def handle_auth(self, client_id: str, websocket, data: dict, agent_coordinator: "AgentCoordinator") -> None:
        """
        处理 WebSocket 认证请求（基于 Cookie）

        ✅ 完全基于 Cookie 认证（不使用 JWT Token）
        ✅ 数据库仅用于统计和历史记录

        前端消息格式:
        {
            "type": "auth",
            "data": {
                "timestamp": 1731140000000,
                "appAccessKey": "<from Cookie>",  // 从 Cookie 读取
                "clientName": "<from Cookie>"     // 从 Cookie 读取
            },
            "sessionId": "<required>"
        }
        """
        try:
            # 1) 提取 Cookie 凭证
            auth_data = data.get("data") or {}
            cookie_access_key = auth_data.get("appAccessKey")
            cookie_client_name = auth_data.get("clientName") or "researchmind-uuid1759932177"

            # 2) 保存到 WebSocket 会话上下文
            try:
                from .websocket_server import WebSocketServer
                ws_server = WebSocketServer.get_instance()
                if ws_server and client_id in ws_server.client_sessions:
                    # ✅ 存储 Cookie 凭证（唯一认证来源）
                    ws_server.client_sessions[client_id].update({
                        "authenticated": True,
                        "authenticated_user_id": client_id,  # 🔧 修复：设置 authenticated_user_id
                        "cookie_credentials": {
                            "access_key": cookie_access_key,
                            "client_name": cookie_client_name,
                            "sku_id": "10048",  # 默认 SKU ID
                            "source": "cookie" if cookie_access_key else "none"
                        }
                    })

                    # 记录凭证来源
                    if cookie_access_key:
                        logger.info(f"✅ 用户 {client_id} WebSocket 认证成功，凭证来源: Cookie (AK={cookie_access_key[:8]}...{cookie_access_key[-4:]})")
                    else:
                        logger.warning(f"⚠️ 用户 {client_id} WebSocket 认证成功，但未检测到 Cookie 凭证")
            except Exception as e:
                logger.warning(f"⚠️ 更新 WebSocket 会话失败: {e}")

            # 3) 返回认证成功
            await self.send_message(websocket, "auth_ok", {
                "authenticated": True,
                "credentials_source": "cookie" if cookie_access_key else "none"
            })
        except Exception as e:
            await self.send_error(websocket, f"认证处理异常: {e}")

    async def handle_stop_response(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        🆕 处理停止响应请求

        Args:
            client_id: Client ID
            websocket: WebSocket connection
            data: Message data with agentId, sessionId
            agent_coordinator: Agent coordinator instance
        """
        agent_id = data.get("agentId")
        session_id = data.get("sessionId")

        logger.info(f"🛑 [Client:{client_id}] 收到停止请求 [Agent:{agent_id}] [Session:{session_id}]")

        try:
            # 调用 agent_coordinator 停止当前任务
            agent_coordinator.stop_current_task(client_id, agent_id, session_id)

            # 发送停止确认消息
            await self.send_message(websocket, "status", {
                "status": "stopped",
                "message": "已停止响应"
            })

            logger.info(f"✅ [Client:{client_id}] 已停止任务")

        except Exception as e:
            logger.error(f"❌ 停止响应失败: {e}", exc_info=True)
            await self.send_error(websocket, f"停止响应失败: {str(e)}")

    @staticmethod
    async def send_message(websocket: Any, message_type: str, data: Dict[str, Any]):
        """
        Send message through WebSocket

        Args:
            websocket: WebSocket connection
            message_type: Message type
            data: Message data
        """
        # 检查WebSocket连接状态
        if not websocket or websocket.closed:
            logger.warning(f"⚠️ WebSocket is closed, cannot send {message_type} message")
            return

        try:
            message = {
                "type": message_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }

            # 🔒 添加超时保护，防止发送消息卡死
            import asyncio
            await asyncio.wait_for(
                websocket.send(json.dumps(message)),
                timeout=30.0  # 30 秒超时
            )
            logger.debug(f"📤 [WebSocket] Sent {message_type}, data size: {len(json.dumps(data))} bytes")
        except asyncio.TimeoutError:
            logger.error(f"❌ Timeout sending {message_type} message (30s)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to send {message_type} message: {e}")

    @staticmethod
    async def send_error(websocket: Any, error_message: str):
        """
        Send error message through WebSocket

        Args:
            websocket: WebSocket connection
            error_message: Error message
        """
        await MessageHandler.send_message(websocket, "error", {
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        })
        logger.error(f"❌ Error sent to client: {error_message}")

    @staticmethod
    async def send_agent_list(websocket: Any):
        """
        Send available agents list to client

        Args:
            websocket: WebSocket connection
        """
        agents_list = [
            {
                "id": agent_id,
                "name": config["name"],
                "icon": config["icon"],
                "description": config["description"]
            }
            for agent_id, config in agent_config.AGENTS.items()
        ]

        await MessageHandler.send_message(websocket, "agents_list", {
            "agents": agents_list
        })
        logger.info(f"📋 Sent {len(agents_list)} agents to client")

    @staticmethod
    async def send_agent_response(
        websocket: Any,
        agent_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        billing: Optional[Dict[str, Any]] = None
    ):
        """
        Send agent response to client

        Args:
            websocket: WebSocket connection
            agent_id: Agent ID
            content: Response content
            metadata: Optional metadata
            tool_calls: Optional list of tool call records
            billing: Optional billing data (tokens, photons, model_name)
        """
        # Get agent config
        from .config import agent_config
        agent_cfg = agent_config.AGENTS.get(agent_id, {})

        message_data = {
            "content": content,
            "role": "assistant",
            "agentId": agent_id,
            "agentName": agent_cfg.get("name", agent_id),
            "type": "text",
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }

        # Add billing data if provided
        if billing:
            message_data["billing"] = billing
            logger.debug(f"💎 [消息计费] 附加计费数据: tokens={billing.get('tokens')}, photons={billing.get('photons')}")

        # Add tool calls if provided
        if tool_calls:
            message_data["toolCalls"] = tool_calls

        # Send as "message" type to match frontend expectations
        await MessageHandler.send_message(websocket, "message", message_data)
        logger.info(f"📤 Sent agent response from {agent_id}: {content[:100]}...")



    async def handle_get_conversation_stats(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        🆕 通过 WebSocket 获取会话计费统计

        Args:
            client_id: 客户端 ID
            websocket: WebSocket 连接
            data: 消息数据，包含 conversationId
            agent_coordinator: Agent 协调器
        """
        conversation_id = data.get("conversationId") or data.get("sessionId")

        if not conversation_id:
            await self.send_error(websocket, "缺少 conversationId 参数")
            return

        try:
            from .user_billing_config import get_billing_context_manager

            context_manager = get_billing_context_manager()
            context = context_manager.get_context(conversation_id)

            if not context:
                # 返回空数据而不是错误
                await self.send_message(websocket, "conversation_stats", {
                    "success": False,
                    "message": f"对话 {conversation_id} 不存在",
                    "data": None
                })
                return

            snapshot = context.get_snapshot()

            await self.send_message(websocket, "conversation_stats", {
                "success": True,
                "message": "获取成功",
                "data": snapshot
            })

        except Exception as e:
            logger.error(f"❌ 获取会话计费统计失败: {e}", exc_info=True)
            await self.send_error(websocket, f"获取会话计费统计失败: {str(e)}")

    async def handle_get_user_stats(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        🆕 通过 WebSocket 获取用户计费统计

        🔒 安全机制：只返回当前登录用户的数据，忽略前端传来的 userId

        Args:
            client_id: 客户端 ID
            websocket: WebSocket 连接
            data: 消息数据（userId 参数会被忽略，使用当前登录用户）
            agent_coordinator: Agent 协调器
        """
        try:
            # 🔒 安全：从 WebSocket 会话中获取当前登录用户 ID
            from .websocket_server import WebSocketServer
            ws_server = WebSocketServer.get_instance()

            authenticated_user_id = None
            if ws_server and client_id in ws_server.client_sessions:
                authenticated_user_id = ws_server.client_sessions[client_id].get("authenticated_user_id")

            # 如果没有认证用户 ID，使用 client_id 作为回退
            user_id = str(authenticated_user_id) if authenticated_user_id else client_id

            logger.info(f"🔒 [用户隔离] 获取用户统计: authenticated_user_id={authenticated_user_id}, user_id={user_id}, client_id={client_id}")

            # 获取用户统计数据
            from .user_billing_config import get_billing_context_manager
            context_manager = get_billing_context_manager()
            user_stats = context_manager.get_user_total_usage(user_id)

            await self.send_message(websocket, "user_stats", {
                "success": True,
                "message": "获取成功",
                "data": user_stats
            })

        except Exception as e:
            logger.error(f"❌ 获取用户计费统计失败: {e}", exc_info=True)
            await self.send_error(websocket, f"获取用户计费统计失败: {str(e)}")

    async def handle_get_global_stats(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        🆕 通过 WebSocket 获取全局计费统计
        
        Args:
            client_id: 客户端 ID
            websocket: WebSocket 连接
            data: 消息数据（无需参数）
            agent_coordinator: Agent 协调器
        """
        try:
            from .user_billing_config import get_billing_context_manager
            
            context_manager = get_billing_context_manager()
            global_stats = context_manager.get_global_total_usage()
            
            await self.send_message(websocket, "global_stats", {
                "success": True,
                "message": "获取成功",
                "data": global_stats
            })

        except Exception as e:
            logger.error(f"❌ 获取全局计费统计失败: {e}", exc_info=True)
            await self.send_error(websocket, f"获取全局计费统计失败: {str(e)}")

    async def handle_get_history(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        🆕 获取会话历史记录
        """
        session_id = data.get("sessionId")
        agent_id = data.get("agentId")
        
        if not session_id:
            await self.send_error(websocket, "Session ID is required")
            return

        try:
            # Construct session key used in AgentCoordinator
            # Note: This requires knowledge of how keys are constructed. 
            # Ideally AgentCoordinator should provide a method for this.
            # But here we just need to load from SessionManager directly using the session_id pattern?
            # Wait, SessionManager saves by session_key. 
            # In AgentCoordinator: session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"
            # But SessionManager.save_history uses session_key.
            
            # We need to reconstruct the key. 
            # If agent_id is missing, we might not find it if it was saved with agent_id in the key.
            # Let's assume the frontend sends the same params.
            if agent_id:
                session_key = f"{client_id}_{agent_id}_{session_id}"
            else:
                # Fallback, might not work if multiple agents share session_id logic differently
                session_key = session_id 

            from .session_manager import SessionManager
            history = SessionManager.load_history(session_key)
            
            # Also try loading with raw session_id if key failed (backward compatibility)
            if not history:
                 history = SessionManager.load_history(session_id)

            await self.send_message(websocket, "history", {
                "sessionId": session_id,
                "history": history
            })
            logger.info(f"📜 Sent history for session {session_id} ({len(history)} messages)")

        except Exception as e:
            logger.error(f"❌ Failed to get history: {e}", exc_info=True)
            await self.send_error(websocket, f"Failed to get history: {str(e)}")

    @staticmethod
    async def send_agent_thinking(websocket: Any, agent_id: str, thinking: str):
        """
        Send agent thinking status to client

        Args:
            websocket: WebSocket connection
            agent_id: Agent ID
            thinking: Thinking message
        """
        await MessageHandler.send_message(websocket, "agent_thinking", {
            "agentId": agent_id,
            "thinking": thinking,
            "timestamp": datetime.now().isoformat()
        })

    async def handle_recover_session(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        🆕 处理会话恢复请求（重连后使用）

        当 WebSocket 重新连接后，客户端会发送此消息请求恢复会话状态。
        服务器会返回当前任务的状态，帮助前端正确显示 UI。

        Args:
            client_id: Client ID
            websocket: WebSocket connection
            data: 消息数据，包含 sessionId, clientId
            agent_coordinator: Agent 协调器
        """
        session_id = data.get("sessionId")
        logger.info(f"🔄 [Client:{client_id}] 收到会话恢复请求 [Session:{session_id}]")

        try:
            # 1) 发送认证确认
            await self.send_message(websocket, "connected", {
                "clientId": client_id,
                "message": "Reconnected to ResearchMind",
                "timestamp": datetime.now().isoformat(),
                "isReconnection": True
            })

            # 2) 发送 agents 列表
            await self.send_agent_list(websocket)

            # 3) 检查是否有正在进行的任务
            has_active_task = False
            active_task_info = None

            # 从 agent_coordinator 获取任务状态
            if hasattr(agent_coordinator, 'get_active_task_status'):
                active_task_info = agent_coordinator.get_active_task_status(client_id, session_id)
                has_active_task = active_task_info is not None

            # 4) 发送恢复状态
            await self.send_message(websocket, "session_recovered", {
                "sessionId": session_id,
                "clientId": client_id,
                "hasActiveTask": has_active_task,
                "activeTask": active_task_info,
                "timestamp": datetime.now().isoformat()
            })

            logger.info(f"✅ [Client:{client_id}] 会话恢复完成, 活跃任务: {has_active_task}")

        except Exception as e:
            logger.error(f"❌ 会话恢复失败: {e}", exc_info=True)
            await self.send_error(websocket, f"会话恢复失败: {str(e)}")
