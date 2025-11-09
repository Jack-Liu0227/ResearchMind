"""
用户计费配置管理

允许每个用户配置自己的 Bohrium AccessKey 和 SKU ID
支持每个对话的计费隔离，防止多用户并发时的数据混乱
"""

import os
import logging
from typing import Dict, Optional
from pathlib import Path
import json
import threading
from dataclasses import dataclass, field
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

    def mark_charged(self, result: Dict) -> None:
        """
        线程安全地标记已扣费

        Args:
            result: 扣费结果
        """
        with self._lock:
            self.charged = True
            self.charge_result = result
            self.updated_at = datetime.now().isoformat()

    def get_snapshot(self) -> Dict:
        """
        获取当前计费状态的快照（线程安全）

        Returns:
            计费状态快照
        """
        with self._lock:
            return {
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


class UserBillingConfigManager:
    """用户计费配置管理器"""
    
    def __init__(self, config_dir: str = "user_configs"):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件存储目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        # 🔧 移除开发者默认 AccessKey 后备机制
        # 强制所有用户必须配置自己的 Bohrium AccessKey
        self.default_config = {
            'access_key': '',  # 不再从环境变量读取开发者 AK
            'sku_id': os.getenv('BOHRIUM_SKU_ID', '10048'),  # SKU ID 可以保留默认值
            'client_name': 'ResearchMind'  # 客户端名称保留默认值
        }

        # 🔒 生产模式：简化日志
        verbose = os.getenv('PHOTON_BILLING_VERBOSE', 'false').lower() == 'true'
        if verbose:
            logger.info(f"💎 用户计费配置管理器已初始化 - 配置目录: {self.config_dir}")
            logger.info("⚠️ 已禁用开发者默认 AccessKey 后备机制，所有用户必须配置自己的 AK")
        else:
            logger.info("💎 用户计费配置管理器已初始化")
    
    def save_user_config(self, user_id: str, access_key: str, sku_id: str,
                        client_name: str = "ResearchMind") -> bool:
        """
        保存用户的 Bohrium 配置

        Args:
            user_id: 用户 ID（可以是 session_id 或真实用户 ID）
            access_key: Bohrium AccessKey
            sku_id: Bohrium SKU ID
            client_name: 客户端名称

        Returns:
            是否保存成功
        """
        try:
            # 🔧 验证 access_key 格式（防止保存错误数据）
            if not access_key or not isinstance(access_key, str):
                logger.error(f"❌ 无效的 access_key: 类型={type(access_key)}, 值={access_key[:50] if access_key else 'None'}")
                return False

            # 检查 access_key 是否包含异常字符（如换行符、日志前缀等）
            if '\n' in access_key or '[后端]' in access_key or 'Traceback' in access_key:
                logger.error(f"❌ access_key 包含异常字符，拒绝保存: {access_key[:100]}")
                return False

            # 检查 access_key 长度（Bohrium AccessKey 通常是 32 位十六进制字符串）
            if len(access_key) < 16 or len(access_key) > 128:
                logger.warning(f"⚠️ access_key 长度异常: {len(access_key)} 字符")

            config = {
                'access_key': access_key.strip(),  # 去除首尾空格
                'sku_id': sku_id,
                'client_name': client_name,
                'updated_at': str(Path(__file__).stat().st_mtime)
            }

            config_file = self.config_dir / f"{user_id}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # 🔒 生产模式：简化日志
            verbose = os.getenv('PHOTON_BILLING_VERBOSE', 'false').lower() == 'true'
            if verbose:
                logger.info(f"✅ 已保存用户 {user_id[:8]}... 的计费配置 (AK: {access_key[:8]}...{access_key[-4:]})")
            else:
                logger.info(f"✅ 已保存用户计费配置 (AK: {access_key[:8]}...{access_key[-4:]})")
            return True

        except Exception as e:
            logger.error(f"❌ 保存用户配置失败: {e}", exc_info=True)
            return False
    
    def get_user_config(self, user_id: str) -> Dict[str, str]:
        """
        获取用户的 Bohrium 配置

        Args:
            user_id: 用户 ID

        Returns:
            用户配置，如果不存在则返回空配置（access_key 为空字符串）
        """
        config_file = self.config_dir / f"{user_id}.json"

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    logger.debug(f"📖 读取用户 {user_id[:8]}... 的配置")
                    return config
            except Exception as e:
                logger.error(f"❌ 读取用户配置失败: {e}", exc_info=True)

        # 🔧 返回空配置（不再提供开发者 AK 作为后备）
        logger.warning(f"⚠️ 用户 {user_id[:8]}... 未配置 Bohrium AccessKey，请前往设置页面配置")
        return self.default_config.copy()  # access_key 为空字符串

    def has_user_config(self, user_id: str) -> bool:
        """检查用户是否已配置"""
        return (self.config_dir / f"{user_id}.json").exists()

    def delete_user_config(self, user_id: str) -> bool:
        """
        删除用户配置

        Args:
            user_id: 用户 ID

        Returns:
            是否删除成功
        """
        try:
            config_file = self.config_dir / f"{user_id}.json"
            if config_file.exists():
                config_file.unlink()
                logger.info(f"🗑️ 已删除用户 {user_id[:8]}... 的配置")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 删除用户配置失败: {e}", exc_info=True)
            return False


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


# 全局单例
_config_manager: Optional[UserBillingConfigManager] = None
_billing_context_manager: Optional[ConversationBillingContextManager] = None


def get_config_manager() -> UserBillingConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = UserBillingConfigManager()
    return _config_manager


def get_billing_context_manager() -> ConversationBillingContextManager:
    """获取全局计费隔离上下文管理器实例"""
    global _billing_context_manager
    if _billing_context_manager is None:
        _billing_context_manager = ConversationBillingContextManager()
    return _billing_context_manager

