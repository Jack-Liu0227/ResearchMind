"""
Streaming Handler (流式生成处理器)

功能：
1. 流式LLM调用 - 支持OpenAI/Anthropic API的流式响应
2. 实时推送 - 通过回调函数实时推送生成的内容片段
3. 缓存兼容 - 流式响应完成后仍可缓存完整内容
4. 错误处理 - 流式生成失败时优雅降级到非流式模式
"""

import asyncio
from typing import Optional, Callable, Dict, Any, AsyncIterator
from litellm import completion
import structlog

logger = structlog.get_logger(__name__)

# 🔧 使用统一的配置
# 添加 paper_search 目录到 sys.path
import sys
from pathlib import Path as PathLib
_CURRENT_FILE = PathLib(__file__)
_PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
if str(_PAPER_SEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

from config import (
    ENABLE_STREAMING,
    STREAMING_BUFFER_SIZE,
    STREAMING_UPDATE_INTERVAL
)


class StreamingHandler:
    """流式生成处理器"""
    
    def __init__(
        self,
        model: str,
        enable_streaming: bool = ENABLE_STREAMING,
        buffer_size: int = STREAMING_BUFFER_SIZE,
        update_interval: float = STREAMING_UPDATE_INTERVAL
    ):
        """
        初始化流式处理器
        
        Args:
            model: LLM模型名称
            enable_streaming: 是否启用流式生成
            buffer_size: 缓冲区大小（字符数）
            update_interval: 更新间隔（秒）
        """
        self.model = model
        self.enable_streaming = enable_streaming
        self.buffer_size = buffer_size
        self.update_interval = update_interval
        
        logger.info(
            "StreamingHandler initialized",
            model=model,
            streaming_enabled=enable_streaming
        )
    
    async def generate_with_streaming(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        stream_callback: Optional[Callable[[str], Any]] = None
    ) -> str:
        """
        使用流式生成（如果启用）
        
        Args:
            messages: LLM消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            stream_callback: 流式回调函数（接收每个内容片段）
        
        Returns:
            完整的生成内容
        """
        if not self.enable_streaming or stream_callback is None:
            # 非流式模式：直接调用
            return await self._generate_non_streaming(
                messages, temperature, max_tokens
            )
        
        try:
            # 流式模式：逐步生成并推送
            return await self._generate_streaming(
                messages, temperature, max_tokens, stream_callback
            )
        except Exception as e:
            logger.warning(
                f"Streaming generation failed, falling back to non-streaming: {e}"
            )
            # 降级到非流式模式
            return await self._generate_non_streaming(
                messages, temperature, max_tokens
            )
    
    async def _generate_non_streaming(
        self,
        messages: list,
        temperature: float,
        max_tokens: int
    ) -> str:
        """非流式生成（传统模式）"""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
        )
        
        # 提取内容
        content = self._extract_content_from_response(response)
        logger.info("Non-streaming generation completed")
        return content
    
    async def _generate_streaming(
        self,
        messages: list,
        temperature: float,
        max_tokens: int,
        stream_callback: Callable[[str], Any]
    ) -> str:
        """流式生成（实时推送）"""
        logger.info("Starting streaming generation...")
        
        full_content = ""
        buffer = ""
        last_update_time = asyncio.get_event_loop().time()
        
        # 调用LLM流式API
        loop = asyncio.get_event_loop()
        response_stream = await loop.run_in_executor(
            None,
            lambda: completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
        )
        
        # 处理流式响应
        for chunk in response_stream:
            # 提取内容片段
            delta_content = self._extract_delta_content(chunk)
            if not delta_content:
                continue
            
            full_content += delta_content
            buffer += delta_content
            
            # 检查是否需要推送更新
            current_time = loop.time()
            should_update = (
                len(buffer) >= self.buffer_size or
                (current_time - last_update_time) >= self.update_interval
            )
            
            if should_update:
                # 推送缓冲区内容
                await self._send_stream_update(stream_callback, buffer)
                buffer = ""
                last_update_time = current_time
        
        # 推送剩余内容
        if buffer:
            await self._send_stream_update(stream_callback, buffer)
        
        logger.info(f"Streaming generation completed ({len(full_content)} chars)")
        return full_content

    def _extract_content_from_response(self, response: Any) -> str:
        """从非流式响应中提取内容"""
        try:
            if response is None:
                return ""

            # 使用字典方式访问属性
            response_dict = vars(response) if hasattr(response, '__dict__') else {}
            choices = response_dict.get('choices', [])

            if choices and len(choices) > 0:
                choice = choices[0]
                choice_dict = vars(choice) if hasattr(choice, '__dict__') else {}
                message = choice_dict.get('message')

                if message is not None:
                    message_dict = vars(message) if hasattr(message, '__dict__') else {}
                    content = message_dict.get('content', '')
                    return content.strip() if content else ""

            return ""
        except Exception as e:
            logger.error(f"Failed to extract content from response: {e}")
            return ""

    def _extract_delta_content(self, chunk: Any) -> str:
        """从流式响应块中提取内容片段"""
        try:
            if chunk is None:
                return ""

            # 使用字典方式访问属性
            chunk_dict = vars(chunk) if hasattr(chunk, '__dict__') else {}
            choices = chunk_dict.get('choices', [])

            if choices and len(choices) > 0:
                choice = choices[0]
                choice_dict = vars(choice) if hasattr(choice, '__dict__') else {}
                delta = choice_dict.get('delta')

                if delta is not None:
                    delta_dict = vars(delta) if hasattr(delta, '__dict__') else {}
                    content = delta_dict.get('content', '')
                    return content if content else ""

            return ""
        except Exception as e:
            logger.error(f"Failed to extract delta content: {e}")
            return ""

    async def _send_stream_update(
        self,
        callback: Callable[[str], Any],
        content: str
    ):
        """发送流式更新（支持同步和异步回调）"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(content)
            else:
                callback(content)
        except Exception as e:
            logger.error(f"Failed to send stream update: {e}")


# ============================================================================
# 全局单例管理器（便于使用）
# ============================================================================

_streaming_handlers: Dict[str, StreamingHandler] = {}


def get_streaming_handler(
    model: str,
    enable_streaming: bool = ENABLE_STREAMING
) -> StreamingHandler:
    """
    获取流式处理器实例（单例模式）

    Args:
        model: LLM模型名称
        enable_streaming: 是否启用流式生成

    Returns:
        StreamingHandler instance
    """
    cache_key = f"{model}_{enable_streaming}"

    if cache_key not in _streaming_handlers:
        _streaming_handlers[cache_key] = StreamingHandler(
            model=model,
            enable_streaming=enable_streaming
        )

    return _streaming_handlers[cache_key]

