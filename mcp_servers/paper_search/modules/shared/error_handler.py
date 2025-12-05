"""
统一错误处理模块

功能：
1. 统一的错误分类和处理
2. 错误日志记录
3. 用户友好的错误消息
4. 错误恢复策略
"""
from typing import Dict, Any, Optional, Callable
from enum import Enum
import structlog
import traceback

logger = structlog.get_logger(__name__)


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"           # 网络错误（超时、连接失败等）
    API = "api"                   # API 错误（限流、认证失败等）
    PARSING = "parsing"           # 解析错误（JSON、XML 等）
    VALIDATION = "validation"     # 验证错误（参数错误、格式错误等）
    TIMEOUT = "timeout"           # 超时错误
    RESOURCE = "resource"         # 资源错误（内存不足、文件不存在等）
    UNKNOWN = "unknown"           # 未知错误


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"           # 低：可忽略，不影响主流程
    MEDIUM = "medium"     # 中：影响单个操作，但不影响整体
    HIGH = "high"         # 高：影响整体流程，需要人工介入
    CRITICAL = "critical" # 严重：系统级错误，需要立即处理


class ErrorHandler:
    """统一错误处理器"""
    
    # 错误分类规则（异常类型 -> 错误类别）
    ERROR_CLASSIFICATION = {
        'TimeoutError': ErrorCategory.TIMEOUT,
        'asyncio.TimeoutError': ErrorCategory.TIMEOUT,
        'ConnectionError': ErrorCategory.NETWORK,
        'requests.exceptions.ConnectionError': ErrorCategory.NETWORK,
        'requests.exceptions.Timeout': ErrorCategory.TIMEOUT,
        'JSONDecodeError': ErrorCategory.PARSING,
        'ValueError': ErrorCategory.VALIDATION,
        'KeyError': ErrorCategory.VALIDATION,
        'FileNotFoundError': ErrorCategory.RESOURCE,
        'MemoryError': ErrorCategory.RESOURCE,
    }
    
    # 用户友好的错误消息模板
    ERROR_MESSAGES = {
        ErrorCategory.NETWORK: "网络连接失败，请检查网络连接",
        ErrorCategory.API: "API 调用失败，可能是限流或认证问题",
        ErrorCategory.PARSING: "数据解析失败，可能是格式错误",
        ErrorCategory.VALIDATION: "参数验证失败，请检查输入",
        ErrorCategory.TIMEOUT: "操作超时，请稍后重试",
        ErrorCategory.RESOURCE: "资源不足或不可用",
        ErrorCategory.UNKNOWN: "发生未知错误",
    }
    
    def __init__(self):
        """初始化错误处理器"""
        self.error_stats = {
            'total': 0,
            'by_category': {},
            'by_severity': {}
        }
    
    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        severity: ErrorSeverity = None,
        recovery_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            error: 异常对象
            context: 错误上下文（如 paper_id、operation 等）
            severity: 错误严重程度（如果为 None，自动判断）
            recovery_callback: 恢复回调函数（可选）
        
        Returns:
            错误信息字典
        """
        # 1. 分类错误
        category = self._classify_error(error)
        
        # 2. 判断严重程度
        if severity is None:
            severity = self._determine_severity(error, category)
        
        # 3. 生成用户友好的错误消息
        user_message = self._generate_user_message(error, category)
        
        # 4. 记录错误日志
        self._log_error(error, category, severity, context)
        
        # 5. 更新统计
        self._update_stats(category, severity)
        
        # 6. 尝试恢复
        recovery_result = None
        if recovery_callback:
            try:
                recovery_result = recovery_callback()
            except Exception as e:
                logger.warning(f"Recovery callback failed: {e}")
        
        # 7. 返回错误信息
        return {
            'error': str(error),
            'error_type': type(error).__name__,
            'category': category.value,
            'severity': severity.value,
            'user_message': user_message,
            'context': context or {},
            'recovery_result': recovery_result,
            'traceback': traceback.format_exc() if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else None
        }
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """分类错误"""
        error_type = type(error).__name__
        full_error_type = f"{type(error).__module__}.{error_type}"
        
        # 检查完整类型
        if full_error_type in self.ERROR_CLASSIFICATION:
            return self.ERROR_CLASSIFICATION[full_error_type]
        
        # 检查简单类型
        if error_type in self.ERROR_CLASSIFICATION:
            return self.ERROR_CLASSIFICATION[error_type]
        
        # 检查错误消息中的关键词
        error_msg = str(error).lower()
        if 'timeout' in error_msg:
            return ErrorCategory.TIMEOUT
        elif 'connection' in error_msg or 'network' in error_msg:
            return ErrorCategory.NETWORK
        elif 'api' in error_msg or 'rate limit' in error_msg:
            return ErrorCategory.API
        elif 'parse' in error_msg or 'json' in error_msg:
            return ErrorCategory.PARSING
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """判断错误严重程度"""
        # 根据错误类别判断严重程度
        if category == ErrorCategory.CRITICAL:
            return ErrorSeverity.CRITICAL
        elif category in [ErrorCategory.RESOURCE]:
            return ErrorSeverity.HIGH
        elif category in [ErrorCategory.TIMEOUT, ErrorCategory.NETWORK, ErrorCategory.API]:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _generate_user_message(self, error: Exception, category: ErrorCategory) -> str:
        """生成用户友好的错误消息"""
        base_message = self.ERROR_MESSAGES.get(category, self.ERROR_MESSAGES[ErrorCategory.UNKNOWN])
        
        # 添加具体错误信息（如果有用）
        error_str = str(error)
        if error_str and len(error_str) < 100:
            return f"{base_message}：{error_str}"
        else:
            return base_message
    
    def _log_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any] = None
    ):
        """记录错误日志"""
        log_data = {
            'error_type': type(error).__name__,
            'error_message': str(error)[:200],
            'category': category.value,
            'severity': severity.value,
            **(context or {})
        }
        
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            logger.error("Error occurred", **log_data, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning("Error occurred", **log_data)
        else:
            logger.info("Minor error occurred", **log_data)
    
    def _update_stats(self, category: ErrorCategory, severity: ErrorSeverity):
        """更新错误统计"""
        self.error_stats['total'] += 1
        
        # 按类别统计
        cat_key = category.value
        self.error_stats['by_category'][cat_key] = self.error_stats['by_category'].get(cat_key, 0) + 1
        
        # 按严重程度统计
        sev_key = severity.value
        self.error_stats['by_severity'][sev_key] = self.error_stats['by_severity'].get(sev_key, 0) + 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取错误统计"""
        return self.error_stats.copy()


# 全局错误处理器实例
_error_handler: Optional[ErrorHandler] = None


def get_error_handler() -> ErrorHandler:
    """获取全局错误处理器实例"""
    global _error_handler
    
    if _error_handler is None:
        _error_handler = ErrorHandler()
    
    return _error_handler

