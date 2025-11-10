"""
Session Manager

Manages chat sessions, data isolation, and persistence.
Ensures data (structures, images, messages) are isolated per session.

集成 Bohrium 计费功能：
- 每个会话独立追踪 token 使用和光子消耗
- 仅使用用户配置的 AccessKey（不再提供开发者默认 AK）
- 会话结束时可选择性扣费
"""

import os
import json
import logging
import shutil
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage chat sessions and data isolation"""

    # Base directories
    BASE_DATA_DIR = Path("session_data")
    STRUCTURES_DIR = BASE_DATA_DIR / "structures"
    IMAGES_DIR = BASE_DATA_DIR / "images"
    METADATA_DIR = BASE_DATA_DIR / "metadata"

    # Session registry
    _sessions: Dict[str, Dict[str, Any]] = {}
    _session_registry_file = BASE_DATA_DIR / "session_registry.json"
    _initialized: bool = False

    # 线程安全锁，保护会话数据
    _sessions_lock = threading.RLock()

    # Session cleanup configuration
    SESSION_TIMEOUT = timedelta(hours=24)  # 24小时超时
    
    @classmethod
    def initialize(cls):
        """Initialize session manager and create base directories"""
        # Prevent duplicate initialization
        if cls._initialized:
            logger.debug("Session Manager already initialized, skipping")
            return
        
        # Create directories with retry logic to handle race conditions
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Create base directory first
                if not cls.BASE_DATA_DIR.exists():
                    cls.BASE_DATA_DIR.mkdir(exist_ok=True)
                
                # Create subdirectories
                for directory in [cls.STRUCTURES_DIR, cls.IMAGES_DIR, cls.METADATA_DIR]:
                    if not directory.exists():
                        directory.mkdir(parents=True, exist_ok=True)
                
                break  # Success, exit retry loop
                
            except FileExistsError:
                # Directory was created by another process, which is fine
                logger.debug(f"Directory already exists (attempt {attempt + 1}/{max_retries})")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Failed to create directories (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(0.1)  # Brief delay before retry
                else:
                    logger.error(f"Failed to create directories after {max_retries} attempts: {e}")
                    return
        
        # Load session registry
        cls._load_session_registry()
        
        cls._initialized = True
        logger.info(f"✅ Session Manager initialized")
        logger.info(f"📁 Base data directory: {cls.BASE_DATA_DIR.absolute()}")
    
    @classmethod
    def _load_session_registry(cls):
        """Load session registry from file"""
        with cls._sessions_lock:
            if cls._session_registry_file.exists():
                try:
                    with open(cls._session_registry_file, 'r', encoding='utf-8') as f:
                        cls._sessions = json.load(f)
                    logger.info(f"📖 Loaded {len(cls._sessions)} sessions from registry")
                except Exception as e:
                    logger.error(f"Failed to load session registry: {e}")
                    cls._sessions = {}
            else:
                cls._sessions = {}

    @classmethod
    def _save_session_registry(cls):
        """Save session registry to file"""
        with cls._sessions_lock:
            try:
                with open(cls._session_registry_file, 'w', encoding='utf-8') as f:
                    json.dump(cls._sessions, f, indent=2, ensure_ascii=False)
                logger.debug(f"💾 Saved session registry ({len(cls._sessions)} sessions)")
            except Exception as e:
                logger.error(f"Failed to save session registry: {e}")
    
    @classmethod
    def create_session(
        cls,
        session_id: str,
        client_id: str,
        agent_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new session

        Args:
            session_id: Unique session ID
            client_id: Client ID
            agent_id: Agent ID (optional)
            title: Session title (optional)

        Returns:
            Session metadata
        """
        with cls._sessions_lock:
            if session_id in cls._sessions:
                logger.warning(f"Session {session_id} already exists")
                return cls._sessions[session_id]

            # Create session metadata
            session_data = {
                "session_id": session_id,
                "client_id": client_id,
                "agent_id": agent_id,
                "title": title or f"Session {session_id[:8]}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": 0,
                "structure_count": 0,
                "image_count": 0,
                # Bohrium 计费相关
                "billing": {
                    "total_tokens": 0,
                    "total_photons": 0.0,
                    "requests_count": 0,
                    "charged": False,  # 是否已扣费
                    "charge_result": None,  # 扣费结果
                    "user_access_key": None,  # 用户自定义 AK（可选）
                    "user_sku_id": None  # 用户自定义 SKU ID（可选）
                }
            }

            # Create session directories
            session_structures_dir = cls.STRUCTURES_DIR / session_id
            session_images_dir = cls.IMAGES_DIR / session_id
            session_metadata_file = cls.METADATA_DIR / f"{session_id}.json"

            session_structures_dir.mkdir(parents=True, exist_ok=True)
            session_images_dir.mkdir(parents=True, exist_ok=True)

            # Save session metadata
            try:
                with open(session_metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to save session metadata: {e}")

            # Register session
            cls._sessions[session_id] = session_data
            cls._save_session_registry()

            logger.info(f"🆕 Created session: {session_id} (client: {client_id}, agent: {agent_id})")

            return session_data
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata
        
        Args:
            session_id: Session ID
        
        Returns:
            Session metadata or None
        """
        return cls._sessions.get(session_id)
    
    @classmethod
    def update_session(cls, session_id: str, updates: Dict[str, Any]):
        """
        Update session metadata

        Args:
            session_id: Session ID
            updates: Fields to update
        """
        with cls._sessions_lock:
            if session_id not in cls._sessions:
                logger.warning(f"Session {session_id} not found")
                return

            cls._sessions[session_id].update(updates)
            cls._sessions[session_id]["updated_at"] = datetime.now().isoformat()

            # Save to file
            session_metadata_file = cls.METADATA_DIR / f"{session_id}.json"
            try:
                with open(session_metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(cls._sessions[session_id], f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"Failed to update session metadata: {e}")

            cls._save_session_registry()

    @classmethod
    def delete_session(cls, session_id: str):
        """
        Delete a session and all its data

        Args:
            session_id: Session ID
        """
        with cls._sessions_lock:
            if session_id not in cls._sessions:
                logger.warning(f"Session {session_id} not found")
                return

            # Delete session directories
            session_structures_dir = cls.STRUCTURES_DIR / session_id
            session_images_dir = cls.IMAGES_DIR / session_id
            session_metadata_file = cls.METADATA_DIR / f"{session_id}.json"

            try:
                if session_structures_dir.exists():
                    shutil.rmtree(session_structures_dir)
                if session_images_dir.exists():
                    shutil.rmtree(session_images_dir)
                if session_metadata_file.exists():
                    session_metadata_file.unlink()
            except Exception as e:
                logger.error(f"Failed to delete session files: {e}")

            # Remove from registry
            del cls._sessions[session_id]
            cls._save_session_registry()

            logger.info(f"🗑️ Deleted session: {session_id}")
    
    @classmethod
    def get_session_structures_dir(cls, session_id: str) -> Path:
        """
        Get structures directory for a session.
        Creates the directory if it doesn't exist.
        """
        structures_dir = cls.STRUCTURES_DIR / session_id
        structures_dir.mkdir(parents=True, exist_ok=True)
        return structures_dir

    @classmethod
    def get_session_images_dir(cls, session_id: str) -> Path:
        """
        Get images directory for a session.
        Creates the directory if it doesn't exist.
        """
        images_dir = cls.IMAGES_DIR / session_id
        images_dir.mkdir(parents=True, exist_ok=True)
        return images_dir
    
    @classmethod
    def get_session_phonon_dir(cls, session_id: str) -> Path:
        """Get phonon results directory for a session"""
        phonon_dir = cls.get_session_images_dir(session_id) / "phonon_results"
        phonon_dir.mkdir(parents=True, exist_ok=True)  # ⭐ 添加 parents=True
        return phonon_dir
    
    @classmethod
    def list_sessions(cls, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all sessions, optionally filtered by client
        
        Args:
            client_id: Optional client ID filter
        
        Returns:
            List of session metadata
        """
        sessions = list(cls._sessions.values())
        
        if client_id:
            sessions = [s for s in sessions if s.get("client_id") == client_id]
        
        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        
        return sessions
    
    @classmethod
    def increment_message_count(cls, session_id: str):
        """Increment message count for a session"""
        if session_id in cls._sessions:
            cls._sessions[session_id]["message_count"] = cls._sessions[session_id].get("message_count", 0) + 1
            cls.update_session(session_id, {})
    
    @classmethod
    def increment_structure_count(cls, session_id: str):
        """Increment structure count for a session"""
        if session_id in cls._sessions:
            cls._sessions[session_id]["structure_count"] = cls._sessions[session_id].get("structure_count", 0) + 1
            cls.update_session(session_id, {})
    
    @classmethod
    def increment_image_count(cls, session_id: str):
        """Increment image count for a session"""
        if session_id in cls._sessions:
            cls._sessions[session_id]["image_count"] = cls._sessions[session_id].get("image_count", 0) + 1
            cls.update_session(session_id, {})

    @classmethod
    def cleanup_expired_sessions(cls) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        with cls._sessions_lock:
            now = datetime.now()
            expired_sessions = []

            for session_id, session_data in cls._sessions.items():
                try:
                    # 解析 updated_at 时间戳
                    updated_at_str = session_data.get('updated_at')
                    if not updated_at_str:
                        continue

                    # 支持 ISO 格式时间戳
                    updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))

                    # 检查是否过期
                    if now - updated_at > cls.SESSION_TIMEOUT:
                        expired_sessions.append(session_id)
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ 无法解析会话 {session_id} 的时间戳: {e}")
                    continue

            # 删除过期会话
            for session_id in expired_sessions:
                try:
                    del cls._sessions[session_id]
                    logger.info(f"🗑️ 清理过期会话: {session_id}")
                except Exception as e:
                    logger.error(f"❌ 清理会话 {session_id} 失败: {e}")

            # 保存更新后的注册表
            if expired_sessions:
                cls._save_session_registry()

            return len(expired_sessions)

    # ==========================================
    # Bohrium 计费相关方法（已废弃，保留用于向后兼容）
    # ==========================================
    # ⚠️ 注意：这些方法已废弃，计费功能现在由 ConversationBillingContext 管理
    # 保留这些方法仅为向后兼容，新代码应使用 ConversationBillingContext

    @classmethod
    def set_user_billing_config(cls, session_id: str, access_key: str, sku_id: str):
        """
        ⚠️ 已废弃：设置会话的用户计费配置

        用户配置现在直接存储在数据库中，不需要通过 SessionManager 设置
        """
        logger.warning(f"⚠️ set_user_billing_config 已废弃，用户配置现在存储在数据库中")
        # 保留空实现以避免破坏现有代码

    @classmethod
    def update_billing_usage(cls, session_id: str, tokens: int, photons: float):
        """
        ⚠️ 已废弃：更新会话的计费使用情况

        计费统计现在由 ConversationBillingContext 管理，此方法保留仅为向后兼容
        """
        logger.debug(f"⚠️ update_billing_usage 已废弃，计费由 ConversationBillingContext 管理")
        # 保留空实现以避免破坏现有代码

    @classmethod
    def get_billing_summary(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """
        ⚠️ 已废弃：获取会话的计费摘要

        计费统计现在由 ConversationBillingContext 管理
        保留此方法仅为向后兼容，返回空摘要
        """
        logger.debug(f"⚠️ get_billing_summary 已废弃，请使用 ConversationBillingContext")
        return {
            "session_id": session_id,
            "total_tokens": 0,
            "total_photons": 0.0,
            "requests_count": 0,
            "avg_tokens_per_request": 0,
            "charged": False,
            "has_user_config": False,
            "billing_source": "已废弃"
        }

    @classmethod
    def charge_session(cls, session_id: str) -> Dict[str, Any]:
        """
        对会话进行实际扣费（调用 Bohrium API）

        Args:
            session_id: 会话 ID

        Returns:
            扣费结果
        """
        with cls._sessions_lock:
            if session_id not in cls._sessions:
                return {
                    "success": False,
                    "message": "会话不存在"
                }

            billing = cls._sessions[session_id]["billing"]

            # 检查是否已扣费
            if billing["charged"]:
                logger.warning(f"⚠️ 会话 {session_id[:8]}... 已经扣费，跳过")
                return {
                    "success": False,
                    "message": "会话已扣费",
                    "previous_result": billing["charge_result"]
                }

            # 检查是否有消耗
            if billing["total_photons"] <= 0:
                logger.info(f"ℹ️ 会话 {session_id[:8]}... 无光子消耗，跳过扣费")
                return {
                    "success": True,
                    "message": "无需扣费",
                    "photons": 0
                }

        # 调用计费服务（在锁外执行，避免长时间持有锁）
        try:
            from .photon_billing import get_billing_service
            billing_service = get_billing_service()

            # 使用用户 AK（不再提供开发者默认 AK）
            result = billing_service.charge_photons(
                photons=billing["total_photons"],
                session_id=session_id,
                user_access_key=billing["user_access_key"],
                user_sku_id=billing["user_sku_id"]
            )

            # 记录扣费结果（需要重新获取锁）
            with cls._sessions_lock:
                if session_id in cls._sessions:
                    billing = cls._sessions[session_id]["billing"]
                    billing["charged"] = result.get("success", False)
                    billing["charge_result"] = result
                    cls.update_session(session_id, {})

            if result.get("success"):
                logger.info(f"✅ 会话 {session_id[:8]}... 扣费成功: {billing['total_photons']:.4f} 光子")
            else:
                logger.error(f"❌ 会话 {session_id[:8]}... 扣费失败: {result.get('message')}")

            return result

        except Exception as e:
            logger.error(f"❌ 会话 {session_id[:8]}... 扣费异常: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"扣费异常: {str(e)}"
            }


# Initialize on module import
SessionManager.initialize()

