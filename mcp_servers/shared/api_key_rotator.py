"""
API密钥轮询管理器 - 实现round-robin轮询机制

功能：
1. 支持多个API密钥的轮询调度
2. 自动切换失效的密钥
3. 线程安全的密钥管理
"""

import os
import threading
from typing import List, Optional
import structlog

logger = structlog.get_logger(__name__)


class APIKeyRotator:
    """API密钥轮询器"""
    
    def __init__(self, env_var_name: str, delimiter: str = ','):
        """
        初始化API密钥轮询器
        
        Args:
            env_var_name: 环境变量名称
            delimiter: 密钥分隔符（默认为逗号）
        """
        self.env_var_name = env_var_name
        self.delimiter = delimiter
        self._lock = threading.Lock()
        self._current_index = 0
        self._failed_keys = set()
        
        # 从环境变量加载密钥
        self._keys = self._load_keys()
        
        if not self._keys:
            logger.warning(f"No API keys found for {env_var_name}")
        else:
            logger.info(f"Loaded {len(self._keys)} API keys for {env_var_name}")
    
    def _load_keys(self) -> List[str]:
        """从环境变量加载密钥列表"""
        keys_str = os.getenv(self.env_var_name, '')
        if not keys_str:
            return []
        
        # 分割并清理密钥
        keys = [key.strip() for key in keys_str.split(self.delimiter) if key.strip()]
        return keys
    
    def get_next_key(self) -> Optional[str]:
        """
        获取下一个可用的API密钥（round-robin）
        
        Returns:
            API密钥字符串，如果没有可用密钥则返回None
        """
        with self._lock:
            if not self._keys:
                return None
            
            # 查找下一个未失效的密钥
            attempts = 0
            max_attempts = len(self._keys)
            
            while attempts < max_attempts:
                key = self._keys[self._current_index]
                self._current_index = (self._current_index + 1) % len(self._keys)
                
                # 如果密钥未失效，返回它
                if key not in self._failed_keys:
                    logger.debug(f"Using API key index {self._current_index - 1} for {self.env_var_name}")
                    return key
                
                attempts += 1
            
            # 所有密钥都失效了
            logger.error(f"All API keys for {self.env_var_name} have failed")
            return None
    
    def mark_key_failed(self, key: str):
        """
        标记密钥为失效
        
        Args:
            key: 失效的API密钥
        """
        with self._lock:
            if key in self._keys:
                self._failed_keys.add(key)
                logger.warning(f"Marked API key as failed for {self.env_var_name}: {key[:10]}...")
    
    def reset_failed_keys(self):
        """重置所有失效的密钥（用于重试）"""
        with self._lock:
            self._failed_keys.clear()
            logger.info(f"Reset all failed keys for {self.env_var_name}")
    
    def get_available_count(self) -> int:
        """获取可用密钥数量"""
        with self._lock:
            return len(self._keys) - len(self._failed_keys)
    
    def get_total_count(self) -> int:
        """获取总密钥数量"""
        return len(self._keys)


# 全局轮询器实例
_semantic_scholar_rotator: Optional[APIKeyRotator] = None
_tavily_rotator: Optional[APIKeyRotator] = None


def get_semantic_scholar_key() -> Optional[str]:
    """获取Semantic Scholar API密钥"""
    global _semantic_scholar_rotator
    if _semantic_scholar_rotator is None:
        _semantic_scholar_rotator = APIKeyRotator('SEMANTIC_SCHOLAR_API_KEY')
    return _semantic_scholar_rotator.get_next_key()


def get_tavily_key() -> Optional[str]:
    """获取Tavily API密钥"""
    global _tavily_rotator
    if _tavily_rotator is None:
        _tavily_rotator = APIKeyRotator('TAVILY_API_KEY')
    return _tavily_rotator.get_next_key()


def mark_semantic_scholar_key_failed(key: str):
    """标记Semantic Scholar密钥失效"""
    global _semantic_scholar_rotator
    if _semantic_scholar_rotator:
        _semantic_scholar_rotator.mark_key_failed(key)


def mark_tavily_key_failed(key: str):
    """标记Tavily密钥失效"""
    global _tavily_rotator
    if _tavily_rotator:
        _tavily_rotator.mark_key_failed(key)

