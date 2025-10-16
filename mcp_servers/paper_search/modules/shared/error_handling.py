"""
Error Handling Module (错误处理模块)

统一错误处理和重试机制 - 高优先级优化功能

功能：
1. 定义统一的错误类型
2. 提供重试装饰器
3. 错误日志和监控
4. 优雅降级处理

设计模式：装饰器模式
"""
import os
import time
import asyncio
from typing import Callable, Any, Optional, Type, Tuple
from functools import wraps
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# 错误类型定义
# ============================================================================

class ResearchError(Exception):
    """研究流程错误基类"""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        """
        初始化错误
        
        Args:
            message: 错误消息
            details: 错误详情
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = time.time()


class SearchError(ResearchError):
    """搜索错误"""
    pass


class DownloadError(ResearchError):
    """下载错误"""
    pass


class AnalysisError(ResearchError):
    """分析错误"""
    pass


class ReportGenerationError(ResearchError):
    """报告生成错误"""
    pass


class CacheError(ResearchError):
    """缓存错误"""
    pass


class NetworkError(ResearchError):
    """网络错误"""
    pass


class TimeoutError(ResearchError):
    """超时错误"""
    pass


class ValidationError(ResearchError):
    """验证错误"""
    pass


# ============================================================================
# 重试装饰器
# ============================================================================

def retry(
    max_attempts: int = 3,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大尝试次数
        backoff: 退避系数（每次重试等待时间 = backoff ^ attempt）
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    
    Example:
        @retry(max_attempts=3, backoff=2.0, exceptions=(SearchError,))
        async def search_papers(query: str):
            # 搜索逻辑
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        wait_time = backoff ** attempt
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {wait_time}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        wait_time = backoff ** attempt
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {wait_time}s..."
                        )
                        
                        if on_retry:
                            on_retry(attempt, e)
                        
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {str(e)}"
                        )
            
            raise last_exception
        
        # 根据函数类型返回对应的包装器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# ============================================================================
# 超时装饰器
# ============================================================================

def timeout(seconds: float):
    """
    超时装饰器
    
    Args:
        seconds: 超时时间（秒）
    
    Example:
        @timeout(30.0)
        async def long_running_task():
            # 长时间运行的任务
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise TimeoutError(
                    f"Function {func.__name__} timed out after {seconds}s",
                    details={'timeout': seconds}
                )
        
        # 同步函数不支持超时装饰器
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            logger.warning(f"Timeout decorator not supported for sync function {func.__name__}")
            return func
    
    return decorator


# ============================================================================
# 错误处理辅助函数
# ============================================================================

def handle_error(
    error: Exception,
    context: str = "",
    fallback_value: Any = None,
    raise_error: bool = False
) -> Any:
    """
    统一错误处理函数
    
    Args:
        error: 异常对象
        context: 错误上下文
        fallback_value: 降级返回值
        raise_error: 是否重新抛出错误
    
    Returns:
        降级返回值或重新抛出错误
    """
    error_msg = f"{context}: {str(error)}" if context else str(error)
    
    # 记录错误
    logger.error(error_msg, exc_info=True)
    
    # 根据错误类型进行不同处理
    if isinstance(error, NetworkError):
        logger.warning("Network error detected, consider retrying")
    elif isinstance(error, ValidationError):
        logger.warning("Validation error, check input parameters")
    
    # 是否重新抛出
    if raise_error:
        raise error
    
    return fallback_value


def safe_execute(
    func: Callable,
    *args,
    fallback_value: Any = None,
    context: str = "",
    **kwargs
) -> Any:
    """
    安全执行函数，捕获所有异常
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        fallback_value: 降级返回值
        context: 错误上下文
        **kwargs: 关键字参数
    
    Returns:
        函数返回值或降级值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return handle_error(e, context=context, fallback_value=fallback_value)


async def safe_execute_async(
    func: Callable,
    *args,
    fallback_value: Any = None,
    context: str = "",
    **kwargs
) -> Any:
    """
    安全执行异步函数，捕获所有异常
    
    Args:
        func: 要执行的异步函数
        *args: 位置参数
        fallback_value: 降级返回值
        context: 错误上下文
        **kwargs: 关键字参数
    
    Returns:
        函数返回值或降级值
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        return handle_error(e, context=context, fallback_value=fallback_value)


# ============================================================================
# 错误恢复策略
# ============================================================================

class ErrorRecoveryStrategy:
    """错误恢复策略"""
    
    @staticmethod
    def retry_with_backoff(
        func: Callable,
        max_attempts: int = 3,
        backoff: float = 2.0
    ) -> Any:
        """使用退避策略重试"""
        return retry(max_attempts=max_attempts, backoff=backoff)(func)
    
    @staticmethod
    def fallback_to_cache(
        func: Callable,
        cache_key: str,
        cache_manager: Any
    ) -> Any:
        """降级到缓存"""
        try:
            return func()
        except Exception as e:
            logger.warning(f"Function failed, falling back to cache: {str(e)}")
            cached = cache_manager.get(cache_key)
            if cached:
                return cached
            raise e
    
    @staticmethod
    def partial_success(
        items: list,
        process_func: Callable,
        min_success_rate: float = 0.5
    ) -> Tuple[list, list]:
        """
        部分成功策略 - 处理批量操作时允许部分失败
        
        Args:
            items: 要处理的项目列表
            process_func: 处理函数
            min_success_rate: 最小成功率
        
        Returns:
            (成功列表, 失败列表)
        """
        successes = []
        failures = []
        
        for item in items:
            try:
                result = process_func(item)
                successes.append(result)
            except Exception as e:
                failures.append({'item': item, 'error': str(e)})
                logger.warning(f"Failed to process item: {str(e)}")
        
        success_rate = len(successes) / len(items) if items else 0
        
        if success_rate < min_success_rate:
            raise ResearchError(
                f"Success rate {success_rate:.2%} below minimum {min_success_rate:.2%}",
                details={
                    'successes': len(successes),
                    'failures': len(failures),
                    'total': len(items)
                }
            )
        
        return successes, failures

