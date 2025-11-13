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
            # Bohrium 计费相关
            "charge_session": self.handle_charge_session,
            "get_billing_summary": self.handle_get_billing_summary,
            "set_user_billing_config": self.handle_set_user_billing_config,
            # 🆕 新的 WebSocket 计费统计查询
            "get_conversation_stats": self.handle_get_conversation_stats,
            "get_user_stats": self.handle_get_user_stats,
            "get_global_stats": self.handle_get_global_stats,
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

    async def handle_charge_session(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        处理会话扣费请求

        Args:
            client_id: 客户端 ID
            websocket: WebSocket 连接
            data: 消息数据，包含 sessionId
            agent_coordinator: Agent 协调器
        """
        session_id = data.get("sessionId")

        if not session_id:
            await self.send_error(websocket, "缺少 sessionId 参数")
            return

        logger.info(f"💳 [Client:{client_id}] 请求对会话 {session_id[:8]}... 进行扣费")

        try:
            from .session_manager import SessionManager

            # 执行扣费
            result = SessionManager.charge_session(session_id)

            # 发送结果
            await self.send_message(websocket, "charge_result", {
                "sessionId": session_id,
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "photons": result.get("photons", 0),
                "bizNo": result.get("bizNo"),
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"❌ 扣费失败: {e}", exc_info=True)
            await self.send_error(websocket, f"扣费失败: {str(e)}")

    async def handle_get_billing_summary(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        获取会话的计费摘要

        Args:
            client_id: 客户端 ID
            websocket: WebSocket 连接
            data: 消息数据，包含 sessionId
            agent_coordinator: Agent 协调器
        """
        session_id = data.get("sessionId")

        if not session_id:
            await self.send_error(websocket, "缺少 sessionId 参数")
            return

        try:
            from .session_manager import SessionManager

            # 获取计费摘要
            summary = SessionManager.get_billing_summary(session_id)

            if summary:
                await self.send_message(websocket, "billing_summary", summary)
            else:
                await self.send_error(websocket, "会话不存在")

        except Exception as e:
            logger.error(f"❌ 获取计费摘要失败: {e}", exc_info=True)
            await self.send_error(websocket, f"获取计费摘要失败: {str(e)}")

    async def handle_set_user_billing_config(
        self,
        client_id: str,
        websocket: Any,
        data: dict,
        agent_coordinator: "AgentCoordinator"
    ) -> None:
        """
        ⚠️ 已废弃：设置用户的计费配置（从 Cookie 中获取）

        此方法已被 HTTP 端点 /api/billing/config/save-from-cookie 替代
        配置现在直接存储在数据库中，不再使用文件系统

        Args:
            client_id: 客户端 ID
            websocket: WebSocket 连接
            data: 消息数据，包含 sessionId, accessKey, skuId, clientName
            agent_coordinator: Agent 协调器
        """
        logger.warning("⚠️ handle_set_user_billing_config 已废弃，请使用 HTTP 端点 /api/billing/config/save-from-cookie")

        # 返回错误提示
        await self.send_error(
            websocket,
            "此功能已废弃，请使用 HTTP 端点 /api/billing/config/save-from-cookie 或通过登录页面配置"
        )

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

        Args:
            client_id: 客户端 ID
            websocket: WebSocket 连接
            data: 消息数据，包含 userId
            agent_coordinator: Agent 协调器
        """
        user_id = data.get("userId")

        if not user_id:
            await self.send_error(websocket, "缺少 userId 参数")
            return

        try:
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

