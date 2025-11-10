"""
用户计费配置管理

提供对话级别的计费上下文隔离，防止多用户并发时的数据混乱
"""

import os
import logging
from typing import Dict, Optional
import threading
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationBillingContext:
    """
    每个对话的独立计费上下文

    确保每个用户/对话的计费数据完全隔离，防止并发访问时的数据混乱
    """

    def __init__(self, conversation_id: str, user_id: str):
        """
        初始化对话计费上下文

        Args:
            conversation_id: 对话/会话 ID（唯一标识）
            user_id: 用户 ID
        """
        self.conversation_id = conversation_id
        self.user_id = user_id
        self._lock = threading.RLock()

        # 计费统计
        self.total_tokens: int = 0
        self.total_photons: float = 0.0
        self.request_count: int = 0

        # 扣费状态
        self.charged: bool = False
        self.charge_result: Optional[Dict] = None
        self.charged_photons: int = 0

        # 时间戳
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def update_token_usage(self, tokens: int, photons: float, model: str = "unknown", metadata: Optional[Dict] = None) -> None:
        """
        线程安全地更新 token 使用

        Args:
            tokens: 本次使用的 token 数
            photons: 本次消耗的光子数
            model: 使用的模型名称
            metadata: 额外元数据
        """
        with self._lock:
            self.total_tokens += tokens
            self.total_photons += photons
            self.request_count += 1
            self.updated_at = datetime.now().isoformat()

    def mark_charged(self, result: Dict, photons_charged: int = 0) -> None:
        """
        线程安全地标记已扣费

        Args:
            result: 扣费结果
            photons_charged: 本次扣费的光子数（可选）
        """
        with self._lock:
            self.charged = True
            self.charge_result = result
            if photons_charged > 0:
                self.charged_photons += photons_charged  # 🔧 修复：累加已扣费光子数
            self.updated_at = datetime.now().isoformat()

            # 🔍 调试日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🔍 [mark_charged] conversation_id={self.conversation_id}, charged={self.charged}, charged_photons={self.charged_photons}, photons_charged={photons_charged}")

    def get_snapshot(self) -> Dict:
        """
        获取当前计费状态的快照（线程安全）

        Returns:
            计费状态快照
        """
        with self._lock:
            snapshot = {
                'conversation_id': self.conversation_id,
                'user_id': self.user_id,
                'total_tokens': self.total_tokens,
                'total_photons': self.total_photons,
                'request_count': self.request_count,
                'charged': self.charged,
                'charged_photons': self.charged_photons,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }

            # 🔍 调试日志
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"🔍 [get_snapshot] conversation_id={self.conversation_id}, charged={self.charged}, charged_photons={self.charged_photons}")

            return snapshot


# UserBillingConfigManager 已删除
# 用户配置现在直接存储在数据库中（services/database/models.py - User 表）
# 请使用以下方式访问用户配置：
#
# from .database import get_db, User
# db = next(get_db())
# user = db.query(User).filter(User.id == user_id).first()
# if user:
#     access_key = user.access_key
#     sku_id = user.sku_id
#     client_name = user.client_name


class ConversationBillingContextManager:
    """
    管理所有对话的计费隔离上下文

    职责：
    1. 为每个对话创建独立的计费上下文
    2. 防止跨对话的数据泄露
    3. 提供线程安全的上下文访问
    4. 支持对话清理和资源释放
    """

    def __init__(self):
        """初始化计费上下文管理器"""
        # 全局锁，保护上下文字典
        self._contexts_lock = threading.RLock()

        # 对话 ID -> 计费上下文的映射
        self._contexts: Dict[str, ConversationBillingContext] = {}

        # 🔒 生产模式：简化日志
        verbose = os.getenv('PHOTON_BILLING_VERBOSE', 'false').lower() == 'true'
        if verbose:
            logger.info("💎 对话计费隔离管理器已初始化")
        else:
            logger.debug("💎 对话计费隔离管理器已初始化")

    def get_or_create_context(self, conversation_id: str, user_id: str) -> ConversationBillingContext:
        """
        获取或创建对话的计费上下文

        Args:
            conversation_id: 对话 ID
            user_id: 用户 ID

        Returns:
            对话的计费上下文
        """
        with self._contexts_lock:
            if conversation_id not in self._contexts:
                context = ConversationBillingContext(conversation_id, user_id)
                self._contexts[conversation_id] = context

                # 🔒 生产模式：简化日志
                verbose = os.getenv('PHOTON_BILLING_VERBOSE', 'false').lower() == 'true'
                if verbose:
                    logger.info(f"✅ 为对话 {conversation_id[:8]}... 创建了新的计费上下文")
                else:
                    logger.debug("✅ 创建了新的计费上下文")

            return self._contexts[conversation_id]

    def get_context(self, conversation_id: str) -> Optional[ConversationBillingContext]:
        """
        获取对话的计费上下文

        Args:
            conversation_id: 对话 ID

        Returns:
            对话的计费上下文，如果不存在则返回 None
        """
        with self._contexts_lock:
            return self._contexts.get(conversation_id)

    def list_contexts(self, user_id: Optional[str] = None) -> list:
        """
        列出所有计费上下文

        Args:
            user_id: 可选的用户 ID 过滤

        Returns:
            计费上下文列表
        """
        with self._contexts_lock:
            contexts = list(self._contexts.values())

            if user_id:
                contexts = [c for c in contexts if c.user_id == user_id]

            return contexts

    def get_user_total_usage(self, user_id: str) -> Dict:
        """
        获取用户的总使用统计（所有对话的聚合）

        Args:
            user_id: 用户 ID

        Returns:
            用户的总使用统计
        """
        with self._contexts_lock:
            user_contexts = [c for c in self._contexts.values() if c.user_id == user_id]

            total_tokens = sum(c.total_tokens for c in user_contexts)
            total_photons = sum(c.total_photons for c in user_contexts)
            total_requests = sum(c.request_count for c in user_contexts)

            return {
                'user_id': user_id,
                'total_conversations': len(user_contexts),
                'total_tokens': total_tokens,
                'total_photons': total_photons,
                'total_requests': total_requests,
                'conversations': [c.get_snapshot() for c in user_contexts]
            }

    def get_global_total_usage(self) -> Dict:
        """
        获取全局使用统计（所有用户、所有对话的聚合）

        Returns:
            全局使用统计
        """
        with self._contexts_lock:
            all_contexts = list(self._contexts.values())

            total_tokens = sum(c.total_tokens for c in all_contexts)
            total_photons = sum(c.total_photons for c in all_contexts)
            total_requests = sum(c.request_count for c in all_contexts)

            # 按用户分组统计
            user_stats = {}
            for context in all_contexts:
                user_id = context.user_id
                if user_id not in user_stats:
                    user_stats[user_id] = {
                        'user_id': user_id,
                        'total_conversations': 0,
                        'total_tokens': 0,
                        'total_photons': 0,
                        'total_requests': 0
                    }
                user_stats[user_id]['total_conversations'] += 1
                user_stats[user_id]['total_tokens'] += context.total_tokens
                user_stats[user_id]['total_photons'] += context.total_photons
                user_stats[user_id]['total_requests'] += context.request_count

            return {
                'total_conversations': len(all_contexts),
                'total_users': len(user_stats),
                'total_tokens': total_tokens,
                'total_photons': total_photons,
                'total_requests': total_requests,
                'user_stats': list(user_stats.values())
            }


# 全局单例
_billing_context_manager: Optional[ConversationBillingContextManager] = None


def get_billing_context_manager() -> ConversationBillingContextManager:
    """获取全局计费隔离上下文管理器实例"""
    global _billing_context_manager
    if _billing_context_manager is None:
        _billing_context_manager = ConversationBillingContextManager()
    return _billing_context_manager

