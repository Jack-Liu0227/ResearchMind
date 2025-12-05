"""
进度追踪器模块

提供批量分析和报告生成的进度追踪功能，支持：
- 实时进度更新
- WebSocket 消息推送
- 错误处理
- 取消操作
"""

import asyncio
from typing import Optional, Callable, Any
from datetime import datetime


class ProgressTracker:
    """
    进度追踪器
    
    用于跟踪批量操作的进度并通过回调函数发送更新
    """
    
    def __init__(
        self,
        total: int,
        callback: Optional[Callable[[dict], Any]] = None,
        operation_name: str = "批量处理",
        throttle_interval: float = None  # 🆕 节流间隔（秒）
    ):
        """
        初始化进度追踪器

        Args:
            total: 总任务数
            callback: 进度更新回调函数，接收进度数据字典
            operation_name: 操作名称，用于日志和消息
            throttle_interval: 进度更新节流间隔（秒），默认从配置读取
        """
        self.total = total
        self.current = 0
        self.callback = callback
        self.operation_name = operation_name
        self.start_time = datetime.now()
        self.is_cancelled = False
        self.errors = []

        # 🆕 节流相关
        if throttle_interval is None:
            try:
                # 添加 paper_search 目录到 sys.path
                import sys
                from pathlib import Path as PathLib
                _CURRENT_FILE = PathLib(__file__)
                _PAPER_SEARCH_DIR = _CURRENT_FILE.parent.parent.parent
                if str(_PAPER_SEARCH_DIR) not in sys.path:
                    sys.path.insert(0, str(_PAPER_SEARCH_DIR))

                from config import PROGRESS_UPDATE_MIN_INTERVAL, ENABLE_PROGRESS_THROTTLE
                self.throttle_interval = PROGRESS_UPDATE_MIN_INTERVAL if ENABLE_PROGRESS_THROTTLE else 0
            except:
                self.throttle_interval = 0.5  # 默认 0.5 秒
        else:
            self.throttle_interval = throttle_interval

        self.last_update_time = 0.0  # 上次更新时间
        
    @property
    def progress(self) -> float:
        """计算进度百分比 (0-1)"""
        if self.total == 0:
            return 1.0
        return min(self.current / self.total, 1.0)
    
    async def update(self, current: Optional[int] = None, message: str = "", force: bool = False):
        """
        更新进度（带节流）

        Args:
            current: 当前完成数（如果为 None，则自动递增）
            message: 进度消息
            force: 是否强制更新（忽略节流）
        """
        if current is not None:
            self.current = current
        else:
            self.current += 1

        # 🆕 节流检查
        import time
        current_time = time.time()
        time_since_last_update = current_time - self.last_update_time

        # 如果不是强制更新，且距离上次更新时间小于节流间隔，则跳过
        if not force and self.throttle_interval > 0 and time_since_last_update < self.throttle_interval:
            # 但如果是第一次或最后一次，仍然更新
            if self.current != 1 and self.current != self.total:
                return

        # 更新最后更新时间
        self.last_update_time = current_time

        # 构造进度数据
        progress_data = {
            "current": self.current,
            "total": self.total,
            "progress": self.progress,
            "message": message or f"{self.operation_name}: {self.current}/{self.total}",
            "status": "running",
            "start_time": int(self.start_time.timestamp() * 1000)  # 毫秒时间戳
        }

        # 调用回调函数
        if self.callback:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(progress_data)
            else:
                self.callback(progress_data)
    
    async def complete(self, message: str = ""):
        """
        标记为完成
        
        Args:
            message: 完成消息
        """
        self.current = self.total
        
        complete_data = {
            "current": self.total,
            "total": self.total,
            "progress": 1.0,
            "message": message or f"{self.operation_name}已完成",
            "status": "success"
        }
        
        if self.callback:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(complete_data)
            else:
                self.callback(complete_data)
    
    async def error(self, error_message: str, details: str = ""):
        """
        报告错误
        
        Args:
            error_message: 错误消息
            details: 错误详情
        """
        self.errors.append({
            "message": error_message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
        error_data = {
            "current": self.current,
            "total": self.total,
            "progress": self.progress,
            "message": f"错误: {error_message}",
            "status": "error",
            "error": error_message,
            "details": details
        }
        
        if self.callback:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(error_data)
            else:
                self.callback(error_data)
    
    def cancel(self):
        """取消操作"""
        self.is_cancelled = True
    
    async def check_cancelled(self):
        """检查是否已取消，如果已取消则抛出异常"""
        if self.is_cancelled:
            raise asyncio.CancelledError(f"{self.operation_name}已被取消")
    
    def get_summary(self) -> dict:
        """
        获取进度摘要
        
        Returns:
            包含进度统计的字典
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "operation": self.operation_name,
            "total": self.total,
            "completed": self.current,
            "progress": self.progress,
            "elapsed_seconds": elapsed,
            "errors_count": len(self.errors),
            "errors": self.errors,
            "is_cancelled": self.is_cancelled
        }

