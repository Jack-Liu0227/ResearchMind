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

logger = logging.getLogger(__name__)

# 会话管理配置
MAX_CONTEXT_MESSAGES = 20  # 最多保留20条消息（10轮对话）
CONTEXT_SUMMARY_THRESHOLD = 15  # 超过15条消息时开始总结


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

            # Create or get session
            if session_key not in self.session_services:
                await self._create_session(session_key, client_id, adk_agent)

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

            # 记录消息开始时的计费状态（用于计算本条消息的增量）
            from services.user_billing_config import get_billing_context_manager
            context_manager = get_billing_context_manager()
            # 使用 session_id 作为对话 ID
            conversation_id = session_id or 'unknown'
            user_id = client_id or 'unknown'
            context = context_manager.get_or_create_context(conversation_id, user_id)
            start_snapshot = context.get_snapshot()

            self.message_start_billing[session_key] = {
                'total_tokens': start_snapshot.get('total_tokens', 0),
                'total_photons': start_snapshot.get('total_photons', 0.0),
                'conversation_id': conversation_id,  # 保存 conversation_id 供后续使用
                'user_id': user_id
            }
            logger.info(f"💎 [消息计费] 消息开始时计费状态:")
            logger.info(f"  session_key={session_key}")
            logger.info(f"  conversation_id={conversation_id}")
            logger.info(f"  start_snapshot={start_snapshot}")
            logger.info(f"  message_start_billing[{session_key}]={self.message_start_billing[session_key]}")

            # Run agent
            logger.info(f"🤖 Running agent: {agent_id} (message #{self.session_message_counts[session_key]})")

            # 创建用户消息 - 需要使用 types.Content 包装 types.Part
            parts = [types.Part(text=content)]
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

                    # 确保 session_id 存在（如果为 None，使用 session_key 的一部分）
                    actual_session_id = session_id
                    if not actual_session_id:
                        # 从 session_key 中提取或生成 session_id
                        import uuid
                        from datetime import datetime
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_id = str(uuid.uuid4())[:8]
                        actual_session_id = f"upload_{timestamp}_{unique_id}"
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
                            create=True
                        ) / "uploads"
                    elif agent_id == 'simulation_agent':
                        # 模拟 agent 使用 cif 目录
                        upload_dir = get_session_storage_path(
                            session_id=actual_session_id,
                            data_type="cif",
                            create=True
                        )
                    else:
                        # 默认使用 papers 目录
                        upload_dir = get_session_storage_path(
                            session_id=actual_session_id,
                            data_type="papers",
                            create=True
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

                                # 🆕 如果文件已存在，添加序号避免覆盖
                                if file_path.exists():
                                    base_name = file_path.stem
                                    suffix = file_path.suffix
                                    counter = 1
                                    while file_path.exists():
                                        file_path = upload_dir / f"{base_name}_{counter}{suffix}"
                                        counter += 1
                                    logger.info(f"File already exists, using new name: {file_path.name}")

                                file_path.write_bytes(file_bytes)

                                saved_files.append({
                                    'filename': original_filename,  # 保留原始文件名用于显示
                                    'saved_filename': filename,  # 保存的文件名
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

                                    # 🆕 如果文件已存在，添加序号避免覆盖
                                    if file_path.exists():
                                        base_name = file_path.stem
                                        suffix = file_path.suffix
                                        counter = 1
                                        while file_path.exists():
                                            file_path = upload_dir / f"{base_name}_{counter}{suffix}"
                                            counter += 1
                                        logger.info(f"File already exists, using new name: {file_path.name}")

                                    file_path.write_text(text_content, encoding='utf-8')

                                    saved_files.append({
                                        'filename': original_filename,  # 保留原始文件名用于显示
                                        'saved_filename': filename,  # 保存的文件名
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
            from agents.callbacks import set_current_session_context
            set_current_session_context(session_id or 'unknown', session_id or 'unknown')
            logger.info(f"🔍 [AGENT_COORDINATOR] 设置 session 上下文: session_id={session_id}, user_id={session_id}")

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

            # 获取会话的计费统计（使用隔离上下文）
            from .user_billing_config import get_billing_context_manager
            context_manager = get_billing_context_manager()

            # 使用 session_id 和 client_id 获取隔离的计费上下文
            billing_session_key = session_id or 'unknown'
            context = context_manager.get_context(billing_session_key)

            # 计算本次对话的计费信息
            previous_total_tokens = 0
            previous_total_photons = 0.0
            session_usage = {
                'total_tokens': 0,
                'total_photons': 0.0,
                'requests_count': 0
            }

            if context:
                # 从隔离上下文获取统计数据
                snapshot = context.get_snapshot()
                session_usage = {
                    'total_tokens': snapshot['total_tokens'],
                    'total_photons': snapshot['total_photons'],
                    'requests_count': snapshot['request_count']
                }

            # 同步计费信息到 SessionManager
            if session_id:
                from .session_manager import SessionManager

                # 更新会话的计费使用情况
                current_billing = SessionManager.get_billing_summary(session_id)
                if current_billing:
                    previous_total_tokens = current_billing['total_tokens']
                    previous_total_photons = current_billing['total_photons']

            # 计算本次新增的 tokens 和光子
            current_tokens = session_usage.get('total_tokens', 0) - previous_total_tokens
            current_photons = session_usage.get('total_photons', 0.0) - previous_total_photons

            # 如果本次有新增，更新 SessionManager
            if session_id and current_tokens > 0:
                from .session_manager import SessionManager
                SessionManager.update_billing_usage(session_id, current_tokens, current_photons)
                logger.info(f"💳 更新会话 {session_id[:8]}... 计费: +{current_tokens} tokens, +{current_photons:.4f} 光子")

            logger.info(f"💎 [计费] 本次对话: {current_tokens} tokens = {current_photons:.4f} 光子 | 会话累计: {session_usage.get('total_tokens', 0)} tokens = {session_usage.get('total_photons', 0.0):.4f} 光子")

            # 发送完成状态（包含计费信息）
            billing_data = {
                "session_total_tokens": session_usage.get('total_tokens', 0),
                "session_total_photons": session_usage.get('total_photons', 0.0),
                "requests_count": session_usage.get('requests_count', 0),
                "current_tokens": current_tokens,  # 本次对话的 tokens
                "current_photons": current_photons,  # 本次对话的光子
                "model_name": os.getenv('MODEL_USE', 'qwen-plus')  # 使用的模型
            }
            logger.info(f"📤 [WebSocket] 准备发送 complete 状态，计费数据: {billing_data}")

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
        adk_agent: Any
    ) -> None:
        """Create new session for agent"""
        logger.info(f"🆕 Creating new session: {session_key}")

        session_service = InMemorySessionService()
        self.session_services[session_key] = session_service

        # Create ADK Session
        session = await session_service.create_session(
            app_name="ResearchMind",
            user_id=client_id,
            session_id=f"session_{session_key}",
            state={}
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

                                # 计算本条消息的计费增量
                                billing_data = None
                                try:
                                    from services.user_billing_config import get_billing_context_manager
                                    context_manager = get_billing_context_manager()

                                    start_billing_info = self.message_start_billing.get(session_key, {})
                                    conversation_id = start_billing_info.get('conversation_id', session_id or 'unknown')
                                    user_id = start_billing_info.get('user_id', client_id or 'unknown')

                                    context = context_manager.get_context(conversation_id)
                                    if context:
                                        current_snapshot = context.get_snapshot()
                                    else:
                                        current_snapshot = {'total_tokens': 0, 'total_photons': 0.0}

                                    logger.debug(f"💎 [消息计费] 调试信息:")
                                    logger.debug(f"  session_key={session_key}")
                                    logger.debug(f"  conversation_id={conversation_id}")
                                    logger.debug(f"  start_billing_info={start_billing_info}")
                                    logger.debug(f"  current_snapshot={current_snapshot}")

                                    current_tokens = current_snapshot.get('total_tokens', 0) - start_billing_info.get('total_tokens', 0)
                                    current_photons = current_snapshot.get('total_photons', 0.0) - start_billing_info.get('total_photons', 0.0)

                                    if current_tokens > 0 or current_photons > 0:
                                        billing_data = {
                                            'tokens': current_tokens,
                                            'photons': round(current_photons, 4),
                                            'model_name': os.getenv('MODEL_USE', 'qwen-plus')
                                        }
                                        logger.info(f"💎 [消息计费] 本条消息计费: tokens={current_tokens}, photons={current_photons}")
                                except Exception as e:
                                    logger.error(f"⚠️ 计算消息计费失败: {e}", exc_info=True)

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

