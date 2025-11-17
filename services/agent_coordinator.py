"""
Agent Coordinator

Coordinates Google ADK agents and manages their sessions.
"""

import os
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .config import agent_config
from .data_processor import DataProcessor
from .message_handler import MessageHandler
from .photon_billing import get_billing_service
from .pricing_service import PricingService

logger = logging.getLogger(__name__)

# 会话管理配置
MAX_CONTEXT_MESSAGES = 20  # 最多保留20条消息（10轮对话）
CONTEXT_SUMMARY_THRESHOLD = 15  # 超过15条消息时开始总结

# 🆕 工具名称到功能类型的映射（用于按功能扣费）
TOOL_FEATURE_MAPPING = {
    # 数据库查询工具（1 光子/次）
    'materials_project_query_tool': 'database',     # 1 光子
    'get_oqmd_phases': 'database',                  # 1 光子
    'search_cod_by_formula': 'database',            # 1 光子
    'get_aflow_data': 'database',                   # 1 光子
    'batch_database_search': 'database',            # 1 光子（批量查询按单次计费）
    'get_structure_recommendations': 'database',    # 1 光子

    # 文献搜索工具（1 光子/次）
    'search_papers': 'search',                      # 1 光子
    # 结构生成与弛豫
    'generate_crystal_structure': 'structure_gen',  # 10 光子
    'relax_structure': 'relaxation',                # 5 光子

    # 声子谱与热导率计算
    'calculate_phonon': 'phonon',                   # 5 光子
    'calculate_phonon_from_directory': 'batch_phonon', # 4 光子（批量优惠）
    'calculate_kappa_from_cif': 'kappa',            # 5 光子
    'calculate_kappa_from_directory': 'batch_kappa', # 4 光子（批量优惠）
    'batch_calculate_kappa': 'batch_kappa',         # 4 光子（批量优惠）

    # 文献报告生成
    'generate_research_report': 'report',           # 30 光子
    'generate_research_report_with_data_collection': 'report',  # 30 光子

    # 文献分析
    'analyze_paper_content': 'analysis',            # 15 光子
    'batch_paper_analysis': 'analysis',             # 15 光子

    # 免费工具（不在映射中的工具默认免费）
    # 'get_paper_info': 0,                          # 获取论文信息（免费）
    # 'get_paper_content': 0,                       # 获取论文内容（免费）
    # 'download_paper': 0,                          # 下载论文（免费）
    # 'save_papers_to_csv': 0,                      # 保存到CSV（免费）
    # 'ingest_papers_to_vector_store': 0,           # 向量化存储（免费）
    # 'semantic_search_papers': 0,                  # 语义搜索（免费）
    # 'generate_research_plan': 0,                  # 生成研究计划（免费）
    # 'extract_and_validate_cif': 0,                # CIF验证（免费）
    # 'calculate_energy_from_cif': 0,               # 能量计算（免费）
    # 'health_check': 0,                            # 健康检查（免费）
}


class AgentCoordinator:
    """Coordinate Google ADK agents"""

    def __init__(self, agents: Dict[str, Any]):
        """
        Initialize agent coordinator

        Args:
            agents: Dict of agent_id -> agent instance
        """
        self.agents = agents
        self.session_services: Dict[str, InMemorySessionService] = {}
        self.runners: Dict[str, Runner] = {}
        self.adk_sessions: Dict[str, Any] = {}
        self.session_message_counts: Dict[str, int] = {}  # 跟踪每个会话的消息数量
        self.current_tool_calls: Dict[str, List[Dict[str, Any]]] = {}  # 跟踪当前消息的工具调用
        self.message_billing_data: Dict[str, Dict[str, Any]] = {}  # 跟踪每条消息的计费数据 (session_key -> billing_data)
        self.message_start_billing: Dict[str, Dict[str, Any]] = {}  # 记录消息开始时的计费状态
        self.stop_flags: Dict[str, bool] = {}  # 🆕 停止标志 (session_key -> should_stop)

    async def process_chat_message(
        self,
        client_id: str,
        websocket: Any,
        content: str,
        agent_id: str,
        session_id: Optional[str] = None,
        retry_count: int = 0,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Process chat message with specified agent

        Args:
            client_id: Client ID
            websocket: WebSocket connection
            content: Message content
            agent_id: Agent ID to use
            session_id: Optional session ID
            retry_count: Number of retries attempted
        """
        max_retries = 1  # 最多重试1次

        try:
            # Get agent instance
            adk_agent = self.agents.get(agent_id)
            if not adk_agent:
                await MessageHandler.send_error(websocket, f"Unknown agent: {agent_id}")
                return

            # Create session key
            session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

            # 🆕 清除停止标志（开始新的处理）
            self.clear_stop_flag(session_key)

            # Create or get session
            if session_key not in self.session_services:
                await self._create_session(session_key, client_id, adk_agent, session_id)

            session = self.adk_sessions[session_key]
            runner = self.runners[session_key]

            # 检查会话消息数量
            message_count = self.session_message_counts.get(session_key, 0)

            # 如果超过最大消息数，截断历史
            if message_count >= MAX_CONTEXT_MESSAGES:
                logger.warning(f"⚠️ Session {session_key} has {message_count} messages. Truncating history...")
                await self._truncate_session_history(session_key, websocket)
                message_count = self.session_message_counts.get(session_key, 0)

            # 如果接近上下文限制，发送警告
            elif message_count >= CONTEXT_SUMMARY_THRESHOLD:
                logger.warning(f"⚠️ Session {session_key} has {message_count} messages. Approaching context limit.")
                await MessageHandler.send_message(
                    websocket,
                    f"💡 提示：对话历史较长（{message_count}条消息），如遇到上下文超限错误，请使用清除会话功能。",
                    agent_id=agent_id,
                    message_type="warning"
                )

            # 增加消息计数
            self.session_message_counts[session_key] = message_count + 1

            # 记录消息开始时的统计状态（用于计算本条消息的增量）
            from services.user_billing_config import get_billing_context_manager
            context_manager = get_billing_context_manager()
            # 优先使用已认证的用户 ID；否则回退到 session_id
            conversation_id = session_id or 'unknown'
            try:
                from .websocket_server import WebSocketServer
                ws = WebSocketServer.get_instance()
                authed_user_id = None
                if ws and client_id in ws.client_sessions:
                    authed_user_id = ws.client_sessions[client_id].get("authenticated_user_id")
                user_id = str(authed_user_id) if authed_user_id else (session_id or 'unknown')
                logger.info(f"🔍 [统计] authed_user_id={authed_user_id}, user_id={user_id}, session_id={session_id}, client_id={client_id}")
            except Exception as e:
                logger.warning(f"⚠️ 获取认证用户 ID 失败: {e}")
                user_id = session_id or 'unknown'

            context = context_manager.get_or_create_context(conversation_id, user_id)
            start_snapshot = context.get_snapshot()

            self.message_start_billing[session_key] = {
                'total_tokens': start_snapshot.get('total_tokens', 0),
                'conversation_id': conversation_id,
                'user_id': user_id,
                'client_id': client_id
            }
            logger.info(f"📊 [消息统计] 消息开始时统计状态:")
            logger.info(f"  session_key={session_key}")
            logger.info(f"  conversation_id={conversation_id}")
            logger.info(f"  start_snapshot={start_snapshot}")
            logger.info(f"  message_start_billing[{session_key}]={self.message_start_billing[session_key]}")

            # Run agent
            logger.info(f"🤖 Running agent: {agent_id} (message #{self.session_message_counts[session_key]})")

            # 创建用户消息 - 需要使用 types.Content 包装 types.Part
            parts = []

            # 🔧 对于 deep_research_agent，在消息开头添加 session_id 信息
            # 这样 Agent 可以在所有操作中使用相同的 session_id
            if agent_id == 'deep_research_agent' and session_id:
                session_info = f"[系统信息] 当前会话 session_id=\"{session_id}\"，所有工具调用必须使用此 session_id\n\n"
                parts.append(types.Part(text=session_info))

            parts.append(types.Part(text=content))

            # Attach optional file/text parts (e.g., CIF content) so agents can parse them
            if attachments:
                # 对于 deep_research_agent 和 simulation_agent，保存文件到磁盘
                # 支持两种格式：
                # 1. base64 编码的文件（encoding='base64'）
                # 2. 纯文本文件（如 CIF 文件，直接包含 content 字符串）
                if agent_id in ['deep_research_agent', 'simulation_agent']:
                    import json
                    import base64
                    from pathlib import Path

                    # 确保 session_id 存在（如果为 None，生成一个唯一的）
                    actual_session_id = session_id
                    if not actual_session_id:
                        # 统一使用 session_{timestamp}_{random_id} 格式
                        import time
                        import random
                        import string

                        timestamp = int(time.time() * 1000)  # 毫秒级时间戳
                        random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                        actual_session_id = f"session_{timestamp}_{random_id}"
                        logger.info(f"📝 Generated session_id for file upload: {actual_session_id}")

                    # 根据 agent 类型选择不同的上传目录 - 使用统一存储
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_servers"))
                    from shared.storage_manager import get_session_storage_path

                    if agent_id == 'deep_research_agent':
                        # 文献研究 agent 使用 papers 目录
                        upload_dir = get_session_storage_path(
                            session_id=actual_session_id,
                            data_type="papers",
                            create=True,
                            session_type="upload",
                            created_by="user",
                            topic=None  # 上传时通常没有明确的 topic
                        ) / "uploads"
                    elif agent_id == 'simulation_agent':
                        # 模拟 agent 使用 cif 目录
                        upload_dir = get_session_storage_path(
                            session_id=actual_session_id,
                            data_type="cif",
                            create=True,
                            session_type="upload",
                            created_by="user",
                            topic=None
                        )
                    else:
                        # 默认使用 papers 目录
                        upload_dir = get_session_storage_path(
                            session_id=actual_session_id,
                            data_type="papers",
                            create=True,
                            session_type="upload",
                            created_by="user",
                            topic=None
                        ) / "uploads"

                    upload_dir.mkdir(parents=True, exist_ok=True)

                    # 🆕 导入文件名清理函数，确保与 MCP 工具使用相同的文件名
                    import re

                    def _sanitize_filename(filename: str) -> str:
                        """清理文件名，与 uploaded_documents.py 保持一致"""
                        sanitized = re.sub(r'[<>:"/\\|?*]+', "_", filename)
                        sanitized = re.sub(r'[\s_]+', "_", sanitized)
                        sanitized = sanitized.strip("_")
                        if not sanitized:
                            sanitized = "uploaded_document"
                        if len(sanitized) > 200:
                            sanitized = sanitized[:200]
                        return sanitized

                    saved_files = []
                    for att in attachments:
                        original_filename = att.get('filename', 'document.txt')
                        # 🆕 使用清理后的文件名，避免与 MCP 工具重复保存
                        filename = _sanitize_filename(original_filename)

                        # 处理 base64 编码的文件
                        if att.get('encoding') == 'base64':
                            content_b64 = att.get('content', '')
                            try:
                                file_bytes = base64.b64decode(content_b64)
                                file_path = upload_dir / filename

                                # 🔧 修复：如果文件已存在，使用时间戳避免覆盖，保持原始文件名结构
                                if file_path.exists():
                                    from datetime import datetime
                                    base_name = file_path.stem
                                    suffix = file_path.suffix
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    file_path = upload_dir / f"{base_name}_{timestamp}{suffix}"
                                    logger.info(f"File already exists, using timestamped name: {file_path.name}")

                                file_path.write_bytes(file_bytes)

                                saved_files.append({
                                    'filename': original_filename,  # 保留原始文件名用于显示
                                    'saved_filename': file_path.name,  # 🔧 修复：使用实际保存的文件名
                                    'path': str(file_path),
                                    'size': len(file_bytes),
                                    'mime_type': att.get('mime_type', 'application/octet-stream')
                                })
                                logger.info(f"💾 Saved base64 file: {original_filename} -> {file_path.name} ({len(file_bytes)} bytes)")
                            except Exception as e:
                                logger.error(f"❌ Failed to save base64 file {original_filename}: {e}")
                                continue

                        # 处理纯文本文件（如 CIF 文件）
                        else:
                            text_content = att.get('content', '')
                            if text_content:
                                try:
                                    file_path = upload_dir / filename

                                    # 🔧 修复：如果文件已存在，使用时间戳避免覆盖，保持原始文件名结构
                                    if file_path.exists():
                                        from datetime import datetime
                                        base_name = file_path.stem
                                        suffix = file_path.suffix
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        file_path = upload_dir / f"{base_name}_{timestamp}{suffix}"
                                        logger.info(f"File already exists, using timestamped name: {file_path.name}")

                                    file_path.write_text(text_content, encoding='utf-8')

                                    saved_files.append({
                                        'filename': original_filename,  # 保留原始文件名用于显示
                                        'saved_filename': file_path.name,  # 🔧 修复：使用实际保存的文件名
                                        'path': str(file_path),
                                        'size': len(text_content.encode('utf-8')),
                                        'mime_type': att.get('mime_type', 'text/plain')
                                    })
                                    logger.info(f"💾 Saved text file: {original_filename} -> {file_path.name} ({len(text_content)} chars)")
                                except Exception as e:
                                    logger.error(f"❌ Failed to save text file {original_filename}: {e}")
                                    continue

                    if saved_files:
                        # 只传递文件元数据（不包含内容），引导 agent 使用工具
                        file_info = f"\n\n用户上传了 {len(saved_files)} 个文件：\n"
                        for f in saved_files:
                            size_kb = f['size'] / 1024
                            file_info += f"- {f['filename']} ({size_kb:.2f}KB, {f['mime_type']})\n"
                        file_info += f"\n文件已保存到：{upload_dir}\n"

                        # 根据 agent 类型提供不同的工具调用提示
                        if agent_id == 'deep_research_agent':
                            file_info += f"\n⚠️ 请立即调用工具：ingest_uploaded_papers(session_id=\"{actual_session_id}\")"
                            file_info += f"\n注意：session_id 必须使用引号中的值：\"{actual_session_id}\""
                        elif agent_id == 'simulation_agent':
                            # 检查是否有 CIF 文件
                            cif_files = [f for f in saved_files if f['filename'].lower().endswith('.cif')]
                            if cif_files:
                                file_info += f"\n⚠️ 检测到 CIF 文件，请调用工具：extract_and_validate_cif(session_id=\"{actual_session_id}\")"
                                file_info += f"\n注意：session_id 必须使用引号中的值：\"{actual_session_id}\""

                        parts.append(types.Part(text=file_info))
                else:
                    # 其他 agent 或纯文本附件：直接附加文本内容
                    for att in attachments:
                        fname = att.get('filename') or 'attachment.txt'
                        text = att.get('content') or ''
                        # Prefix to help agent tools detect attachment context
                        att_text = f"[附件: {fname}]\n{text}"
                        parts.append(types.Part(text=att_text))
            user_message = types.Content(role='user', parts=parts)

            # 设置线程本地存储的 session 上下文，供 callbacks 使用
            # 🔴 修复：使用 session_id 作为 user_id，而不是 client_id
            # session_id 是用户的真实标识（与计费配置关联），client_id 只是 WebSocket 连接标识
            # 🔧 同时传递 client_id 作为回退查找配置的依据
            from agents.callbacks import set_current_session_context
            set_current_session_context(session_id or 'unknown', user_id, client_id)
            logger.info(f"🔍 [AGENT_COORDINATOR] 设置 session 上下文: session_id={session_id}, user_id={user_id}, client_id={client_id}")

            # Google ADK API: run_async() 需要 user_id, session_id 和 new_message 参数
            # 🔒 添加超时保护，防止 LLM 调用卡死
            import asyncio
            event_count = 0

            try:
                # 使用 asyncio.wait_for 为整个事件流添加超时（15 分钟）
                async def process_events():
                    nonlocal event_count
                    async for event in runner.run_async(
                        user_id=client_id,
                        session_id=session.id,
                        new_message=user_message
                    ):
                        # 🆕 检查停止标志
                        if self.should_stop(session_key):
                            logger.info(f"🛑 检测到停止标志，中断处理: {session_key}")
                            self.clear_stop_flag(session_key)
                            await MessageHandler.send_message(
                                websocket,
                                "status",
                                {
                                    "status": "stopped",
                                    "message": "已停止响应"
                                }
                            )
                            return

                        event_count += 1
                        logger.info(f"🔍 [Event {event_count}] Type: {type(event).__name__}")
                        logger.info(f"🔍 [Event {event_count}] Attributes: {[attr for attr in dir(event) if not attr.startswith('_')]}")

                        # 🔒 为每个事件处理添加超时保护（5 分钟）
                        try:
                            await asyncio.wait_for(
                                self._handle_agent_event(event, agent_id, websocket, client_id, session_id),
                                timeout=300.0  # 5 分钟
                            )
                        except asyncio.TimeoutError:
                            logger.error(f"❌ Event handling timeout for event {event_count}")
                            await MessageHandler.send_error(
                                websocket,
                                f"事件处理超时（事件 {event_count}），继续处理下一个事件..."
                            )

                await asyncio.wait_for(process_events(), timeout=900.0)  # 15 分钟总超时

            except asyncio.TimeoutError:
                logger.error(f"❌ Agent processing timeout after {event_count} events")
                await MessageHandler.send_error(
                    websocket,
                    "Agent 处理超时（15分钟），请稍后重试或减小任务规模"
                )
                return

            logger.info(f"✅ Agent {agent_id} completed - processed {event_count} events")

            # 获取会话的统计数据（使用隔离上下文）
            from .user_billing_config import get_billing_context_manager
            context_manager = get_billing_context_manager()

            # 使用 session_id 获取隔离的统计上下文
            billing_session_key = session_id or 'unknown'
            context = context_manager.get_context(billing_session_key)

            # 从 ConversationBillingContext 获取统计信息
            session_usage = {
                'total_tokens': 0,
                'total_photons_charged': 0,
                'requests_count': 0,
                'feature_charges': []
            }

            if context:
                # 从隔离上下文获取统计数据
                snapshot = context.get_snapshot()
                session_usage = {
                    'total_tokens': snapshot['total_tokens'],
                    'total_photons_charged': snapshot['total_photons_charged'],
                    'requests_count': snapshot['request_count'],
                    'feature_charges': snapshot.get('feature_charges', [])
                }

            logger.info(f"📊 [统计] 会话累计: {session_usage.get('total_tokens', 0)} tokens (仅供参考) | 已扣费: {session_usage.get('total_photons_charged', 0)} 光子 | 请求次数: {session_usage.get('requests_count', 0)}")

            # 发送完成状态（包含统计信息）
            billing_data = {
                "session_total_tokens": session_usage.get('total_tokens', 0),  # Token 统计（仅供参考）
                "session_total_photons": session_usage.get('total_photons_charged', 0),  # 🔧 修复：字段名改为 session_total_photons（前端期望的字段名）
                "requests_count": session_usage.get('requests_count', 0),
                "model_name": os.getenv('MODEL_USE', 'qwen-plus'),
                "feature_charges": session_usage.get('feature_charges', []),  # 功能扣费明细
                "charged": session_usage.get('total_photons_charged', 0) > 0,  # 🆕 是否已扣费（光子数 > 0）
                "billing_source": "Cookie"  # 🆕 计费来源
            }
            logger.info(f"📤 [WebSocket] 准备发送 complete 状态，统计数据: {billing_data}")

            await MessageHandler.send_message(websocket, "status", {
                "status": "complete",
                "message": "处理完成",
                "billing": billing_data
            })

            logger.info(f"✅ [WebSocket] 已发送 complete 状态")
            logger.info(f"✅ Agent {agent_id} completed")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Agent processing error: {error_msg}", exc_info=True)

            # Check for JSON parsing errors from LLM tool calls
            if "JSONDecodeError" in error_msg or "Expecting ',' delimiter" in error_msg:
                logger.error(f"❌ JSON parsing error in LLM tool call - this may be a DeepSeek formatting issue")
                await MessageHandler.send_error(
                    websocket,
                    "❌ LLM 返回了格式错误的工具调用。这可能是模型的问题，请重试或切换到 Gemini 模型。"
                )
                return

            # 检查是否是上下文窗口超限错误
            if "ContextWindowExceededError" in error_msg or "context length" in error_msg.lower():
                logger.warning(f"⚠️ Context window exceeded, truncating session: {session_key}")

                # 截断历史
                await self._truncate_session_history(session_key, websocket)

                # 提示用户
                await MessageHandler.send_error(
                    websocket,
                    "❌ 上下文窗口超限！已自动清理旧消息。请重新发送您的问题，或使用清除会话功能开始新对话。"
                )
                return

            # 检查是否是MCP连接错误
            if "Connection closed" in error_msg or "ReadTimeout" in error_msg:
                # MCP连接错误，清理session
                logger.warning(f"🔄 MCP connection error detected, clearing session: {session_key}")
                self.clear_session(client_id, agent_id, session_id)

                # 如果还没有重试过，自动重试一次
                if retry_count < max_retries:
                    logger.info(f"🔄 Retrying request (attempt {retry_count + 1}/{max_retries})...")
                    await MessageHandler.send_message(
                        websocket,
                        "status",
                        {
                            "status": "retrying",
                            "message": "连接超时，正在自动重试...",
                            "agent_id": agent_id
                        }
                    )

                    # 等待1秒后重试
                    import asyncio
                    await asyncio.sleep(1)

                    # 递归调用，增加retry_count
                    await self.process_chat_message(
                        client_id=client_id,
                        websocket=websocket,
                        content=content,
                        agent_id=agent_id,
                        session_id=session_id,
                        retry_count=retry_count + 1
                    )
                else:
                    # 已经重试过，发送错误消息
                    await MessageHandler.send_error(
                        websocket,
                        "数据库连接超时，请稍后重试。如果问题持续，请尝试使用其他数据库或减少查询范围。"
                    )
            else:
                # 其他错误
                await MessageHandler.send_error(websocket, f"处理失败: {error_msg}")

    async def _truncate_session_history(
        self,
        session_key: str,
        websocket: Any
    ) -> None:
        """
        Truncate session history to keep only recent messages

        Args:
            session_key: Session key
            websocket: WebSocket connection for notifications
        """
        try:
            session = self.adk_sessions.get(session_key)
            if not session:
                return

            # Get current history
            history = session.history if hasattr(session, 'history') else []
            current_count = len(history)

            if current_count > MAX_CONTEXT_MESSAGES:
                # Keep only the most recent MAX_CONTEXT_MESSAGES messages
                # Keep system message (first) + recent messages
                keep_count = MAX_CONTEXT_MESSAGES - 1  # -1 for system message

                if len(history) > 0 and hasattr(history[0], 'role') and history[0].role == 'system':
                    # Keep system message + recent messages
                    session.history = [history[0]] + history[-keep_count:]
                else:
                    # Just keep recent messages
                    session.history = history[-MAX_CONTEXT_MESSAGES:]

                removed_count = current_count - len(session.history)
                logger.info(f"✂️ Truncated session {session_key}: removed {removed_count} old messages, kept {len(session.history)}")

                # Update message count
                self.session_message_counts[session_key] = len(session.history)

                # Notify user
                await MessageHandler.send_message(
                    websocket,
                    f"📝 已自动清理 {removed_count} 条旧消息，保留最近 {len(session.history)} 条消息以避免上下文超限。",
                    message_type="info"
                )

        except Exception as e:
            logger.error(f"❌ Failed to truncate session history: {e}", exc_info=True)

    async def _create_session(
        self,
        session_key: str,
        client_id: str,
        adk_agent: Any,
        session_id: Optional[str] = None
    ) -> None:
        """Create new session for agent"""
        logger.info(f"🆕 Creating new session: {session_key}")

        session_service = InMemorySessionService()
        self.session_services[session_key] = session_service

        # 🔧 修复：在 state 中传递变量，供 Google ADK 的 instruction 模板使用
        # Google ADK 的 instructions_utils.inject_session_state() 会查找 state 中的变量
        # 并替换 instruction 中的 {+variable_name+} 模板
        initial_state = {
            # 提供常用的上下文变量，避免 KeyError
            'composition': '',  # 化学式（simulation_agent 可能用到）
            'topic': '',  # 研究主题（deep_research_agent 可能用到）
            'query': '',  # 查询关键词
            'generation_id': '',  # 结构生成 ID（simulation_agent 可能用到）
        }
        if session_id:
            initial_state['session_id'] = session_id
            logger.info(f"🔍 [SESSION_STATE] 设置 session_id={session_id} 到 ADK session state")

        # Create ADK Session
        session = await session_service.create_session(
            app_name="ResearchMind",
            user_id=client_id,
            session_id=f"session_{session_key}",
            state=initial_state
        )
        self.adk_sessions[session_key] = session

        # Create Runner
        runner = Runner(
            agent=adk_agent,
            app_name="ResearchMind",
            session_service=session_service
        )
        self.runners[session_key] = runner

        # Initialize message count
        self.session_message_counts[session_key] = 0

    def _get_tool_friendly_message(self, tool_name: str) -> str:
        """
        根据工具名称生成友好的提示信息

        Args:
            tool_name: 工具名称

        Returns:
            友好的提示信息
        """
        # 工具名称到友好提示的映射
        tool_messages = {
            # 文献搜索工具
            "search_papers": "🔍 正在搜索相关论文...",
            "search_arxiv_papers": "📚 正在ArXiv搜索论文...",
            "search_papers_all_sources": "🌐 正在多源搜索论文（ArXiv + Tavily）...",
            "tavily_search": "🔎 正在Tavily搜索...",
            "tavily_academic_search": "🎓 正在Tavily学术搜索...",
            "generate_research_plan": "📋 正在生成研究计划...",
            "batch_paper_analysis": "📊 正在批量分析论文...",
            "generate_research_report": "📝 正在生成研究报告...",
            "download_paper": "⬇️ 正在下载论文PDF...",
            "get_arxiv_paper_content": "📄 正在提取论文全文...",
            "ingest_papers_to_vector_store": "💾 正在向量化存储论文...",
            "semantic_search_papers": "🔍 正在语义搜索论文...",

            # 数据库查询工具
            "query_materials_project": "🗄️ 正在查询Materials Project数据库...",
            "query_oqmd": "🗄️ 正在查询OQMD数据库...",
            "query_cod": "🗄️ 正在查询COD数据库...",
            "query_aflow": "🗄️ 正在查询AFLOW数据库...",

            # 仿真计算工具
            "generate_crystal_structure": "🔬 正在生成晶体结构...",
            "calculate_thermal_conductivity": "🌡️ 正在计算热导率...",
            "calculate_phonon_spectrum": "📈 正在计算声子谱...",
            "optimize_structure": "⚙️ 正在优化结构...",
        }

        # 返回友好提示，如果没有映射则返回默认提示
        return tool_messages.get(tool_name, f"🔧 正在调用工具: {tool_name}...")

    async def _charge_for_tool_if_needed(
        self,
        tool_name: str,
        session_id: str,
        user_id: Optional[str] = None,
        user_access_key: Optional[str] = None,
        user_client_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        在工具调用前检查是否需要扣费，并执行扣费

        Args:
            tool_name: 工具名称
            session_id: 会话 ID
            user_id: 用户 ID（可选）
            user_access_key: 用户访问密钥（可选）
            user_client_name: 用户客户端名称（可选）

        Returns:
            扣费结果字典，包含 success, message, photons 等字段
        """
        # 检查工具是否需要扣费
        feature_type = TOOL_FEATURE_MAPPING.get(tool_name)

        if not feature_type:
            # 免费工具，无需扣费
            logger.debug(f"🆓 工具 {tool_name} 是免费工具，无需扣费")
            return {
                "success": True,
                "message": "免费工具",
                "photons": 0,
                "feature_type": None
            }

        # 需要扣费的工具
        try:
            logger.info(f"💰 工具 {tool_name} 需要扣费，功能类型: {feature_type}")

            # 调用扣费服务
            result = PricingService.charge_for_feature(
                feature_type=feature_type,
                session_id=session_id,
                user_id=user_id,
                user_access_key=user_access_key,
                user_client_name=user_client_name,
                quantity=1
            )

            # 🆕 记录扣费到会话的计费上下文（无论成功或失败都记录）
            try:
                from services.user_billing_config import get_billing_context_manager
                context_manager = get_billing_context_manager()
                conversation_id = session_id or 'unknown'

                # 获取或创建计费上下文
                context = context_manager.get_or_create_context(
                    conversation_id=conversation_id,
                    user_id=user_id or 'unknown'
                )

                photons = result.get("photons", 0)
                success = result.get("success", False)
                error_msg = result.get("message", "未知错误")

                # 记录功能扣费（包含成功/失败状态）
                context.record_feature_charge(
                    feature_type=feature_type,
                    photons=photons,
                    success=success,
                    error_message=None if success else error_msg
                )

                if success:
                    logger.info(f"✅ 扣费成功: {tool_name} ({feature_type}) = {photons} 光子")
                    logger.info(f"📝 已记录扣费到会话 {conversation_id}: {feature_type} = {photons} 光子")
                else:
                    logger.warning(f"⚠️ 扣费失败: {tool_name} ({feature_type}) - {error_msg}")
                    logger.info(f"📝 已记录扣费失败到会话 {conversation_id}: {feature_type} = {photons} 光子 (失败原因: {error_msg})")

            except Exception as e:
                logger.error(f"❌ 记录扣费到会话失败: {e}", exc_info=True)

            return result

        except Exception as e:
            logger.error(f"❌ 扣费异常: {tool_name} ({feature_type}) - {e}", exc_info=True)
            return {
                "success": False,
                "message": f"扣费异常: {str(e)}",
                "photons": 0,
                "feature_type": feature_type
            }

    async def _handle_agent_event(
        self,
        event: Any,
        agent_id: str,
        websocket: Any,
        client_id: str,
        session_id: Optional[str] = None
    ) -> None:
        """Handle agent event"""
        try:
            event_type = type(event).__name__
            logger.debug(f"📨 Agent event: {event_type}")
            logger.debug(f"📨 Event attributes: {dir(event)}")

            # 获取计费服务（用于计算消息级别的计费）
            billing_service = get_billing_service()

            # Handle text content
            if hasattr(event, 'content') and event.content:
                content_obj = event.content
                if hasattr(content_obj, 'parts') and content_obj.parts:
                    for part in content_obj.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content = part.text
                            if text_content.strip():
                                # 获取当前会话的tool calls
                                # 使用与 process_chat_message() 相同的 session_key 格式
                                session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"
                                tool_calls = self.current_tool_calls.get(session_key, [])

                                # 计算本条消息的 token 使用增量
                                billing_data = None
                                try:
                                    from services.user_billing_config import get_billing_context_manager
                                    context_manager = get_billing_context_manager()

                                    start_billing_info = self.message_start_billing.get(session_key, {})
                                    conversation_id = start_billing_info.get('conversation_id', session_id or 'unknown')

                                    context = context_manager.get_context(conversation_id)
                                    if context:
                                        current_snapshot = context.get_snapshot()
                                    else:
                                        current_snapshot = {'total_tokens': 0}

                                    logger.debug(f"📊 [消息统计] 调试信息:")
                                    logger.debug(f"  session_key={session_key}")
                                    logger.debug(f"  conversation_id={conversation_id}")
                                    logger.debug(f"  start_billing_info={start_billing_info}")
                                    logger.debug(f"  current_snapshot={current_snapshot}")

                                    current_tokens = current_snapshot.get('total_tokens', 0) - start_billing_info.get('total_tokens', 0)

                                    if current_tokens > 0:
                                        billing_data = {
                                            'tokens': current_tokens,
                                            'model_name': os.getenv('MODEL_USE', 'qwen-plus')
                                        }
                                        logger.info(f"📊 [消息统计] 本条消息 token 使用: {current_tokens} tokens")
                                except Exception as e:
                                    logger.error(f"⚠️ 计算消息统计失败: {e}", exc_info=True)

                                await MessageHandler.send_agent_response(
                                    websocket=websocket,
                                    agent_id=agent_id,
                                    content=text_content,
                                    tool_calls=tool_calls if tool_calls else None,
                                    billing=billing_data
                                )

                                # 清除已发送的tool calls记录
                                if session_key in self.current_tool_calls:
                                    self.current_tool_calls[session_key] = []

            # Handle tool calls - Try multiple ways to get tool calls from the event
            tool_calls = None

            # Method 1: Direct attribute access
            if hasattr(event, 'tool_calls') and event.tool_calls:
                tool_calls = event.tool_calls
                logger.info(f"🔧 Found tool_calls via attribute: {len(tool_calls)} calls")

            # Method 2: get_function_calls() method (Google ADK)
            elif hasattr(event, 'get_function_calls'):
                try:
                    function_calls = event.get_function_calls()
                    if function_calls:
                        tool_calls = function_calls
                        logger.info(f"🔧 Found tool_calls via get_function_calls(): {len(tool_calls)} calls")
                except Exception as e:
                    logger.debug(f"get_function_calls() failed: {e}")

            # Process tool calls if found
            if tool_calls:
                for tool_call in tool_calls:
                    logger.info(f"🔧 Tool called: {tool_call}")
                    logger.info(f"🔧 Tool call type: {type(tool_call)}")
                    logger.info(f"🔧 Tool call attributes: {dir(tool_call)}")

                    # Extract tool name
                    tool_name = None
                    if hasattr(tool_call, 'name'):
                        tool_name = tool_call.name
                    elif hasattr(tool_call, 'function') and hasattr(tool_call.function, 'name'):
                        tool_name = tool_call.function.name

                    if tool_name:
                        # 提取工具调用参数
                        tool_input = {}
                        if hasattr(tool_call, 'args'):
                            tool_input = tool_call.args if isinstance(tool_call.args, dict) else {}
                        elif hasattr(tool_call, 'input'):
                            tool_input = tool_call.input if isinstance(tool_call.input, dict) else {}
                        elif hasattr(tool_call, 'function') and hasattr(tool_call.function, 'args'):
                            tool_input = tool_call.function.args if isinstance(tool_call.function.args, dict) else {}

                        # 记录工具调用信息
                        # 使用与 process_chat_message() 相同的 session_key 格式
                        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"
                        if session_key not in self.current_tool_calls:
                            self.current_tool_calls[session_key] = []

                        tool_call_record = {
                            "name": tool_name,
                            "input": tool_input,
                            "timestamp": datetime.now().isoformat(),
                            "status": "pending"
                        }
                        self.current_tool_calls[session_key].append(tool_call_record)

                        # 🆕 在工具调用前执行扣费
                        try:
                            # 获取用户凭证（从 WebSocket 服务器的客户端会话中获取）
                            user_access_key = None
                            user_client_name = None
                            user_id_for_charge = None

                            try:
                                from .websocket_server import WebSocketServer
                                ws = WebSocketServer.get_instance()
                                if ws and client_id in ws.client_sessions:
                                    client_session = ws.client_sessions[client_id]

                                    # 🔧 修复：从 cookie_credentials 中获取凭证
                                    cookie_creds = client_session.get("cookie_credentials", {})
                                    user_access_key = cookie_creds.get("access_key")
                                    user_client_name = cookie_creds.get("client_name")

                                    # 获取用户 ID
                                    authed_user_id = client_session.get("authenticated_user_id")
                                    user_id_for_charge = str(authed_user_id) if authed_user_id else (session_id or 'unknown')

                                    logger.debug(f"🔍 [扣费凭证] access_key={'已提供' if user_access_key else '未提供'}, client_name={user_client_name}")
                            except Exception as e:
                                logger.debug(f"无法获取用户凭证: {e}")
                                user_id_for_charge = session_id or 'unknown'

                            # 调用扣费方法
                            charge_result = await self._charge_for_tool_if_needed(
                                tool_name=tool_name,
                                session_id=session_id or 'unknown',
                                user_id=user_id_for_charge,
                                user_access_key=user_access_key,
                                user_client_name=user_client_name
                            )

                            # 记录扣费结果到工具调用记录
                            tool_call_record["charge_result"] = charge_result

                            # 如果扣费失败，记录警告（但不阻止工具执行）
                            if not charge_result.get("success") and charge_result.get("feature_type"):
                                logger.warning(f"⚠️ 工具 {tool_name} 扣费失败，但继续执行: {charge_result.get('message')}")
                                # 可选：发送扣费失败通知到前端
                                await MessageHandler.send_message(websocket, "warning", {
                                    "message": f"扣费失败: {charge_result.get('message')}，但功能将继续执行"
                                })

                        except Exception as e:
                            logger.error(f"❌ 工具扣费异常: {tool_name} - {e}", exc_info=True)
                            # 扣费异常不阻止工具执行

                        # 🆕 发送独立的工具执行消息到前端
                        logger.info(f"🔧 发送工具执行消息 (pending): {tool_name}")
                        await MessageHandler.send_message(websocket, "tool_execution", {
                            "agentId": agent_id,
                            "sessionId": session_id,
                            "toolName": tool_name,
                            "input": tool_input,
                            "status": "pending",
                            "timestamp": tool_call_record["timestamp"]
                        })

                        # 根据工具名称生成更友好的提示信息
                        tool_message = self._get_tool_friendly_message(tool_name)

                        await MessageHandler.send_message(websocket, "status", {
                            "status": "working",
                            "message": tool_message
                        })

                        # 同时发送thinking消息（保留原有逻辑）
                        await MessageHandler.send_agent_thinking(
                            websocket=websocket,
                            agent_id=agent_id,
                            thinking=f"Using tool: {tool_name}"
                        )

            # Handle tool results - THIS IS CRITICAL!
            # Try multiple ways to get tool results from the event
            tool_results = None

            # Method 1: Direct attribute access
            if hasattr(event, 'tool_results') and event.tool_results:
                tool_results = event.tool_results
                logger.info(f"📊 Found tool_results via attribute: {len(tool_results)} results")

            # Method 2: get_function_responses() method
            elif hasattr(event, 'get_function_responses'):
                try:
                    function_responses = event.get_function_responses()
                    if function_responses:
                        tool_results = function_responses
                        logger.info(f"📊 Found tool_results via get_function_responses(): {len(tool_results)} results")
                except Exception as e:
                    logger.debug(f"get_function_responses() failed: {e}")

            # Process tool results if found
            if tool_results:
                for tool_result in tool_results:
                    logger.info(f"📊 Tool result received: {type(tool_result)}")
                    logger.info(f"📊 Tool result attributes: {dir(tool_result)}")

                    # Try to extract the actual result data
                    result_data = None

                    # Try different ways to get result data
                    if hasattr(tool_result, 'result'):
                        result_data = tool_result.result
                        logger.info(f"📊 Got result via .result attribute")
                    elif hasattr(tool_result, 'output'):
                        result_data = tool_result.output
                        logger.info(f"📊 Got result via .output attribute")
                    elif hasattr(tool_result, 'content'):
                        result_data = tool_result.content
                        logger.info(f"📊 Got result via .content attribute")
                    elif isinstance(tool_result, dict):
                        result_data = tool_result
                        logger.info(f"📊 Tool result is already a dict")
                    else:
                        # Try to convert to dict
                        if hasattr(tool_result, 'to_dict'):
                            result_data = tool_result.to_dict()
                            logger.info(f"📊 Got result via .to_dict()")
                        elif hasattr(tool_result, '__dict__'):
                            result_data = tool_result.__dict__
                            logger.info(f"📊 Got result via .__dict__")

                    if result_data:
                        logger.info(f"📊 Processing tool result with type: {type(result_data)}")
                        if isinstance(result_data, dict):
                            logger.info(f"📊 Result keys: {list(result_data.keys())}")

                            # Check if the actual data is in the 'response' field
                            if 'response' in result_data and isinstance(result_data['response'], dict):
                                logger.info(f"📊 Found nested response field, extracting...")
                                actual_result = result_data['response']
                                logger.info(f"📊 Actual result keys: {list(actual_result.keys())}")
                                result_data = actual_result

                            # Check if the actual data is in the 'result' field (can be nested in response or at top level)
                            # This may need to be done multiple times for deeply nested structures
                            max_depth = 5  # Prevent infinite loops
                            depth = 0
                            while 'result' in result_data and depth < max_depth:
                                depth += 1
                                logger.info(f"📊 [Depth {depth}] Found 'result' key, type: {type(result_data['result'])}")
                                result_obj = result_data['result']

                                # Check if it's a dict
                                if isinstance(result_obj, dict):
                                    logger.info(f"📊 [Depth {depth}] Found nested result field (dict), extracting...")
                                    logger.info(f"📊 [Depth {depth}] Result keys: {list(result_obj.keys())}")
                                    result_data = result_obj
                                # Check if it's an MCP CallToolResult object
                                elif hasattr(result_obj, 'structuredContent') or hasattr(result_obj, 'content'):
                                    logger.info(f"📊 [Depth {depth}] Found MCP CallToolResult object")

                                    # Try structuredContent first
                                    if hasattr(result_obj, 'structuredContent'):
                                        structured_content = result_obj.structuredContent
                                        logger.info(f"📊 [Depth {depth}] structuredContent type: {type(structured_content)}")
                                        if isinstance(structured_content, dict):
                                            logger.info(f"📊 [Depth {depth}] structuredContent keys: {list(structured_content.keys())}")
                                            result_data = structured_content
                                            continue
                                        elif structured_content is not None:
                                            logger.warning(f"⚠️ structuredContent is not a dict: {type(structured_content)}")

                                    # Try content field (list of ContentPart)
                                    if hasattr(result_obj, 'content'):
                                        content = result_obj.content
                                        logger.info(f"📊 [Depth {depth}] content type: {type(content)}")

                                        # If content is a list, try to extract text from first item
                                        if isinstance(content, list) and len(content) > 0:
                                            first_item = content[0]
                                            logger.info(f"📊 [Depth {depth}] first content item type: {type(first_item)}")

                                            # Try to get text from TextContent
                                            if hasattr(first_item, 'text'):
                                                import json
                                                try:
                                                    logger.info(f"📊 [Depth {depth}] content.text preview: {first_item.text[:200] if len(first_item.text) > 200 else first_item.text}")
                                                    text_data = json.loads(first_item.text)
                                                    logger.info(f"📊 [Depth {depth}] Parsed JSON from content.text")
                                                    logger.info(f"📊 [Depth {depth}] Parsed data keys: {list(text_data.keys()) if isinstance(text_data, dict) else 'not a dict'}")
                                                    if isinstance(text_data, dict):
                                                        result_data = text_data
                                                        continue
                                                except json.JSONDecodeError as e:
                                                    logger.warning(f"⚠️ content.text is not valid JSON: {e}")
                                                    logger.warning(f"⚠️ content.text value: {first_item.text[:500] if len(first_item.text) > 500 else first_item.text}")
                                        elif isinstance(content, str):
                                            # Try to parse as JSON
                                            import json
                                            try:
                                                text_data = json.loads(content)
                                                logger.info(f"📊 [Depth {depth}] Parsed JSON from content string")
                                                if isinstance(text_data, dict):
                                                    result_data = text_data
                                                    continue
                                            except json.JSONDecodeError:
                                                logger.warning(f"⚠️ content string is not valid JSON")

                                    logger.warning(f"⚠️ Could not extract data from MCP CallToolResult")
                                    break
                                else:
                                    logger.warning(f"⚠️ 'result' is not a dict or MCP object, it's {type(result_obj)}")
                                    logger.warning(f"⚠️ 'result' value: {result_obj}")
                                    break

                            if depth > 0:
                                logger.info(f"📊 ✅ Finished extracting nested results after {depth} levels")
                                logger.info(f"📊 ✅ Final result keys: {list(result_data.keys()) if isinstance(result_data, dict) else 'not a dict'}")

                        await DataProcessor.process_tool_result(
                            result=result_data,
                            agent_id=agent_id,
                            websocket=websocket,
                            session_id=session_id  # Pass session_id
                        )

                        # 更新工具调用记录的输出
                        # 使用与 process_chat_message() 相同的 session_key 格式
                        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"
                        tool_name = None
                        tool_input = None
                        tool_timestamp = None

                        if session_key in self.current_tool_calls and self.current_tool_calls[session_key]:
                            # 找到最后一个pending状态的tool call并更新
                            for tool_call_record in reversed(self.current_tool_calls[session_key]):
                                if tool_call_record.get("status") == "pending":
                                    tool_call_record["output"] = result_data
                                    tool_call_record["status"] = "success"
                                    tool_name = tool_call_record.get("name")
                                    tool_input = tool_call_record.get("input")
                                    tool_timestamp = tool_call_record.get("timestamp")
                                    break

                        # 🆕 发送工具执行成功消息到前端
                        if tool_name:
                            logger.info(f"🔧 发送工具执行消息 (success): {tool_name}")
                            await MessageHandler.send_message(websocket, "tool_execution", {
                                "agentId": agent_id,
                                "sessionId": session_id,
                                "toolName": tool_name,
                                "input": tool_input,
                                "output": result_data,
                                "status": "success",
                                "timestamp": tool_timestamp or datetime.now().isoformat()
                            })

                        # 工具结果处理完成后，发送thinking状态
                        await MessageHandler.send_message(websocket, "status", {
                            "status": "thinking",
                            "message": "正在分析工具返回结果..."
                        })
                    else:
                        logger.warning(f"⚠️ Could not extract result data from tool_result: {type(tool_result)}")

        except Exception as e:
            logger.error(f"Failed to handle agent event: {e}", exc_info=True)

    def clear_session(self, client_id: str, agent_id: str, session_id: Optional[str] = None):
        """
        Clear session for client and agent

        Args:
            client_id: Client ID
            agent_id: Agent ID
            session_id: Optional session ID
        """
        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

        if session_key in self.session_services:
            del self.session_services[session_key]
            del self.runners[session_key]
            del self.adk_sessions[session_key]
            if session_key in self.session_message_counts:
                del self.session_message_counts[session_key]
            # 🆕 清除停止标志
            self.clear_stop_flag(session_key)
            logger.info(f"🗑️ Cleared session: {session_key}")

    def clear_all_sessions(self, client_id: str):
        """
        Clear all sessions for a client

        Args:
            client_id: Client ID
        """
        keys_to_remove = [
            key for key in self.session_services.keys()
            if key.startswith(f"{client_id}_")
        ]

        for key in keys_to_remove:
            del self.session_services[key]
            del self.runners[key]
            del self.adk_sessions[key]
            if key in self.session_message_counts:
                del self.session_message_counts[key]
            # 🆕 清除停止标志
            self.clear_stop_flag(key)

        logger.info(f"🗑️ Cleared {len(keys_to_remove)} sessions for client {client_id}")

    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        return len(self.session_services)

    def get_client_session_count(self, client_id: str) -> int:
        """Get number of sessions for a specific client"""
        return len([
            key for key in self.session_services.keys()
            if key.startswith(f"{client_id}_")
        ])

    def get_session_info(self, client_id: str, agent_id: str, session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get session information including message count

        Args:
            client_id: Client ID
            agent_id: Agent ID
            session_id: Optional session ID

        Returns:
            Dict with session info or None if session doesn't exist
        """
        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"

        if session_key in self.session_services:
            return {
                "session_key": session_key,
                "message_count": self.session_message_counts.get(session_key, 0),
                "max_messages": MAX_CONTEXT_MESSAGES,
                "needs_summary": self.session_message_counts.get(session_key, 0) >= CONTEXT_SUMMARY_THRESHOLD
            }
        return None

    def stop_current_task(self, client_id: str, agent_id: str, session_id: Optional[str] = None):
        """
        🆕 停止当前任务

        Args:
            client_id: Client ID
            agent_id: Agent ID
            session_id: Optional session ID
        """
        session_key = f"{client_id}_{agent_id}_{session_id or 'default'}"
        self.stop_flags[session_key] = True
        logger.info(f"🛑 设置停止标志: {session_key}")

    def should_stop(self, session_key: str) -> bool:
        """
        🆕 检查是否应该停止

        Args:
            session_key: Session key

        Returns:
            True if should stop, False otherwise
        """
        return self.stop_flags.get(session_key, False)

    def clear_stop_flag(self, session_key: str):
        """
        🆕 清除停止标志

        Args:
            session_key: Session key
        """
        if session_key in self.stop_flags:
            del self.stop_flags[session_key]
            logger.info(f"✅ 清除停止标志: {session_key}")

