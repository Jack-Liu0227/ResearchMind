"""
Agent Coordinator

Coordinates Google ADK agents and manages their sessions.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .config import agent_config
from .data_processor import DataProcessor
from .message_handler import MessageHandler

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

            # Run agent
            logger.info(f"🤖 Running agent: {agent_id} (message #{self.session_message_counts[session_key]})")

            # 创建用户消息 - 需要使用 types.Content 包装 types.Part
            parts = [types.Part(text=content)]
            # Attach optional file/text parts (e.g., CIF content) so agents can parse them
            if attachments:
                for att in attachments:
                    fname = att.get('filename') or 'attachment.txt'
                    text = att.get('content') or ''
                    # Prefix to help agent tools detect attachment context
                    att_text = f"[附件: {fname}]\n{text}"
                    parts.append(types.Part(text=att_text))
            user_message = types.Content(role='user', parts=parts)

            # Google ADK API: run_async() 需要 user_id, session_id 和 new_message 参数
            event_count = 0
            async for event in runner.run_async(
                user_id=client_id,
                session_id=session.id,
                new_message=user_message
            ):
                event_count += 1
                logger.info(f"🔍 [Event {event_count}] Type: {type(event).__name__}")
                logger.info(f"🔍 [Event {event_count}] Attributes: {[attr for attr in dir(event) if not attr.startswith('_')]}")
                await self._handle_agent_event(event, agent_id, websocket, session_id)

            logger.info(f"✅ Agent {agent_id} completed - processed {event_count} events")

            # 发送完成状态
            await MessageHandler.send_message(websocket, "status", {
                "status": "complete",
                "message": "处理完成"
            })

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
        session_id: Optional[str] = None
    ) -> None:
        """Handle agent event"""
        try:
            event_type = type(event).__name__
            logger.debug(f"📨 Agent event: {event_type}")
            logger.debug(f"📨 Event attributes: {dir(event)}")

            # Handle text content
            if hasattr(event, 'content') and event.content:
                content_obj = event.content
                if hasattr(content_obj, 'parts') and content_obj.parts:
                    for part in content_obj.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content = part.text
                            if text_content.strip():
                                # 获取当前会话的tool calls
                                session_key = f"{client_id}:{session_id or 'default'}"
                                tool_calls = self.current_tool_calls.get(session_key, [])

                                await MessageHandler.send_agent_response(
                                    websocket=websocket,
                                    agent_id=agent_id,
                                    content=text_content,
                                    tool_calls=tool_calls if tool_calls else None
                                )

                                # 清除已发送的tool calls记录
                                if session_key in self.current_tool_calls:
                                    self.current_tool_calls[session_key] = []

            # Handle tool calls
            if hasattr(event, 'tool_calls') and event.tool_calls:
                for tool_call in event.tool_calls:
                    logger.info(f"🔧 Tool called: {tool_call}")
                    if hasattr(tool_call, 'name'):
                        # 发送工具调用状态到前端
                        tool_name = tool_call.name

                        # 提取工具调用参数
                        tool_input = {}
                        if hasattr(tool_call, 'args'):
                            tool_input = tool_call.args if isinstance(tool_call.args, dict) else {}
                        elif hasattr(tool_call, 'input'):
                            tool_input = tool_call.input if isinstance(tool_call.input, dict) else {}

                        # 记录工具调用信息
                        session_key = f"{client_id}:{session_id or 'default'}"
                        if session_key not in self.current_tool_calls:
                            self.current_tool_calls[session_key] = []

                        tool_call_record = {
                            "name": tool_name,
                            "input": tool_input,
                            "timestamp": datetime.now().isoformat(),
                            "status": "pending"
                        }
                        self.current_tool_calls[session_key].append(tool_call_record)

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
                        session_key = f"{client_id}:{session_id or 'default'}"
                        if session_key in self.current_tool_calls and self.current_tool_calls[session_key]:
                            # 找到最后一个pending状态的tool call并更新
                            for tool_call_record in reversed(self.current_tool_calls[session_key]):
                                if tool_call_record.get("status") == "pending":
                                    tool_call_record["output"] = result_data
                                    tool_call_record["status"] = "success"
                                    break

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

