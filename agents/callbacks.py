"""
Google ADK Callbacks for context management and billing.
参考: https://google.github.io/adk-docs/callbacks/
"""
import logging
from typing import Optional
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.genai import types

logger = logging.getLogger(__name__)

# Import billing service
try:
    from services.photon_billing import get_billing_service
    BILLING_AVAILABLE = True
except ImportError:
    BILLING_AVAILABLE = False
    logger.warning("⚠️ Photon billing service not available")

# 上下文管理配置
MAX_CONTEXT_TOKENS = 50000  # DeepSeek模型的安全上下文长度（降低以强制触发修剪）
RECENT_MESSAGES_TO_KEEP = 3  # 保留最近的消息数量（减少以更激进地修剪）


def estimate_token_count(text: str) -> int:
    """估算文本的token数量（简单估算：1 token ≈ 4 字符）"""
    return len(text) // 4


def trim_llm_request_context(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    修剪LLM请求的上下文，防止超过token限制

    这个callback会在每次调用LLM之前执行，检查并修剪上下文。
    参考: https://github.com/google/adk-python/discussions/826

    Args:
        callback_context: ADK提供的回调上下文
        llm_request: 即将发送给LLM的请求

    Returns:
        None: 允许请求继续（可能已修剪）
        LlmResponse: 跳过LLM调用，直接返回响应
    """
    try:
        agent_name = callback_context.agent_name
        logger.info(f"🎯 [CALLBACK TRIGGERED] Agent: {agent_name}")

        # 获取当前的消息列表
        contents = llm_request.contents if hasattr(llm_request, 'contents') else []
        logger.info(f"🎯 [CALLBACK] Contents type: {type(contents)}, Has contents: {bool(contents)}")
        
        if not contents:
            return None  # 允许请求继续
        
        # 估算总token数
        total_tokens = 0
        for content in contents:
            if hasattr(content, 'parts'):
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        total_tokens += estimate_token_count(part.text)
        
        logger.info(f"🔍 [{agent_name}] LLM请求token估算: {total_tokens} tokens, {len(contents)} 条消息")
        
        # 如果超过限制，修剪历史消息
        if total_tokens > MAX_CONTEXT_TOKENS:
            logger.warning(f"⚠️ [{agent_name}] 上下文过长 ({total_tokens} tokens)，开始修剪...")
            
            # 保留系统消息和最近的N条消息
            trimmed_contents = []
            
            # 首先保留系统消息
            for content in contents:
                if hasattr(content, 'role') and content.role == 'system':
                    trimmed_contents.append(content)
            
            # 然后保留最近的用户和助手消息
            user_assistant_messages = [
                c for c in contents 
                if hasattr(c, 'role') and c.role in ['user', 'model']
            ]
            
            if len(user_assistant_messages) > RECENT_MESSAGES_TO_KEEP:
                trimmed_contents.extend(user_assistant_messages[-RECENT_MESSAGES_TO_KEEP:])
            else:
                trimmed_contents.extend(user_assistant_messages)
            
            # 更新请求
            llm_request.contents = trimmed_contents
            
            # 重新计算token数
            new_total = sum(
                estimate_token_count(part.text)
                for content in trimmed_contents
                if hasattr(content, 'parts')
                for part in content.parts
                if hasattr(part, 'text') and part.text
            )
            
            logger.info(f"✅ [{agent_name}] 修剪完成: {len(contents)} → {len(trimmed_contents)} 条消息, {total_tokens} → {new_total} tokens")
        
        return None  # 允许请求继续
        
    except Exception as e:
        logger.error(f"❌ 修剪上下文失败: {e}", exc_info=True)
        return None  # 即使失败也允许请求继续


def record_llm_usage(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
    llm_response: LlmResponse
) -> None:
    """
    记录 LLM 使用情况并计费

    这个 callback 在 LLM 调用完成后执行，用于记录 token 使用和计算光子消耗

    Args:
        callback_context: ADK 提供的回调上下文
        llm_request: 发送给 LLM 的请求
        llm_response: LLM 返回的响应
    """
    if not BILLING_AVAILABLE:
        return

    try:
        agent_name = callback_context.agent_name

        # 从响应中提取 token 使用信息
        # LiteLLM 的响应通常包含 usage 信息
        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        model_name = "unknown"

        # 尝试从响应中获取 usage 信息
        if hasattr(llm_response, 'usage_metadata'):
            usage = llm_response.usage_metadata
            if hasattr(usage, 'total_token_count'):
                total_tokens = usage.total_token_count
            if hasattr(usage, 'prompt_token_count'):
                prompt_tokens = usage.prompt_token_count
            if hasattr(usage, 'candidates_token_count'):
                completion_tokens = usage.candidates_token_count

        # 如果没有 usage 信息，尝试估算
        if total_tokens == 0:
            # 估算请求 tokens
            if hasattr(llm_request, 'contents'):
                for content in llm_request.contents:
                    if hasattr(content, 'parts'):
                        for part in content.parts:
                            if hasattr(part, 'text') and part.text:
                                prompt_tokens += estimate_token_count(part.text)

            # 估算响应 tokens
            if hasattr(llm_response, 'candidates'):
                for candidate in llm_response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                completion_tokens += estimate_token_count(part.text)

            total_tokens = prompt_tokens + completion_tokens

        # 获取模型名称
        if hasattr(llm_request, 'model'):
            model_name = llm_request.model

        # 如果有 token 使用，记录计费
        if total_tokens > 0:
            billing_service = get_billing_service()

            # 从 callback_context 获取 session_id（如果可用）
            session_id = getattr(callback_context, 'session_id', 'unknown')

            # 记录使用
            billing_result = billing_service.record_usage(
                session_id=session_id,
                tokens=total_tokens,
                model=model_name,
                metadata={
                    'agent_name': agent_name,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens
                }
            )

            # 记录日志
            if billing_result.get('billing_enabled'):
                current = billing_result['current_request']
                session_total = billing_result['session_total']
                logger.info(
                    f"💎 [{agent_name}] Token使用: {current['tokens']} tokens "
                    f"({prompt_tokens} prompt + {completion_tokens} completion) → "
                    f"{current['photons']} 光子 | "
                    f"会话累计: {session_total['photons']} 光子"
                )

    except Exception as e:
        logger.error(f"❌ [BILLING CALLBACK ERROR] {e}", exc_info=True)

