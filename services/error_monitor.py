"""
错误监控和告警服务

提供错误计数、告警、统计等功能
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ErrorMonitor:
    """
    错误监控器
    
    功能：
    1. 记录错误发生次数
    2. 区分可恢复错误和致命错误
    3. 提供错误统计和告警
    """
    
    def __init__(self, alert_threshold: int = 10, time_window_minutes: int = 5):
        """
        初始化错误监控器
        
        Args:
            alert_threshold: 告警阈值（时间窗口内的错误次数）
            time_window_minutes: 时间窗口（分钟）
        """
        self.alert_threshold = alert_threshold
        self.time_window = timedelta(minutes=time_window_minutes)
        
        # 错误计数器（按错误类型）
        self._error_counts: Dict[str, int] = defaultdict(int)
        
        # 错误时间戳队列（用于时间窗口统计）
        self._error_timestamps: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # 致命错误列表
        self._fatal_errors: List[Dict] = []
        
        # 线程锁
        self._lock = threading.RLock()
        
        logger.info(f"✅ 错误监控器已启动 - 告警阈值: {alert_threshold}, 时间窗口: {time_window_minutes}分钟")
    
    def record_error(
        self,
        error_type: str,
        error_message: str,
        is_fatal: bool = False,
        context: Optional[Dict] = None
    ) -> None:
        """
        记录错误
        
        Args:
            error_type: 错误类型（如 "websocket_error", "llm_timeout"）
            error_message: 错误消息
            is_fatal: 是否为致命错误
            context: 错误上下文信息
        """
        with self._lock:
            # 增加计数
            self._error_counts[error_type] += 1
            
            # 记录时间戳
            now = datetime.now()
            self._error_timestamps[error_type].append(now)
            
            # 记录致命错误
            if is_fatal:
                self._fatal_errors.append({
                    'type': error_type,
                    'message': error_message,
                    'timestamp': now.isoformat(),
                    'context': context or {}
                })
                logger.critical(f"💀 [致命错误] {error_type}: {error_message}")
            
            # 检查是否需要告警
            self._check_alert(error_type)
    
    def _check_alert(self, error_type: str) -> None:
        """
        检查是否需要告警
        
        Args:
            error_type: 错误类型
        """
        # 清理过期的时间戳
        now = datetime.now()
        cutoff_time = now - self.time_window
        
        timestamps = self._error_timestamps[error_type]
        while timestamps and timestamps[0] < cutoff_time:
            timestamps.popleft()
        
        # 检查是否超过阈值
        if len(timestamps) >= self.alert_threshold:
            logger.warning(
                f"⚠️ [告警] 错误类型 '{error_type}' 在过去 {self.time_window.total_seconds() / 60:.0f} 分钟内"
                f"发生了 {len(timestamps)} 次，超过阈值 {self.alert_threshold}"
            )
    
    def get_error_stats(self, error_type: Optional[str] = None) -> Dict:
        """
        获取错误统计
        
        Args:
            error_type: 错误类型（可选，不指定则返回所有类型）
        
        Returns:
            错误统计信息
        """
        with self._lock:
            if error_type:
                return {
                    'type': error_type,
                    'total_count': self._error_counts[error_type],
                    'recent_count': len(self._error_timestamps[error_type])
                }
            else:
                return {
                    'total_errors': sum(self._error_counts.values()),
                    'error_types': dict(self._error_counts),
                    'fatal_errors_count': len(self._fatal_errors)
                }
    
    def get_fatal_errors(self, limit: int = 10) -> List[Dict]:
        """
        获取致命错误列表
        
        Args:
            limit: 返回的最大数量
        
        Returns:
            致命错误列表
        """
        with self._lock:
            return self._fatal_errors[-limit:]
    
    def reset_stats(self) -> None:
        """重置统计数据"""
        with self._lock:
            self._error_counts.clear()
            self._error_timestamps.clear()
            self._fatal_errors.clear()
            logger.info("✅ 错误统计已重置")


# 全局错误监控器实例
_error_monitor: Optional[ErrorMonitor] = None
_monitor_lock = threading.Lock()


def get_error_monitor() -> ErrorMonitor:
    """获取全局错误监控器实例"""
    global _error_monitor
    if _error_monitor is None:
        with _monitor_lock:
            if _error_monitor is None:
                _error_monitor = ErrorMonitor()
    return _error_monitor

