"""
Hybrid Session Manager

Integrates Redis-based persistent storage with file-based fallback.
Automatically switches between Redis and file storage based on availability.
"""

import logging
from typing import Dict, Any, Optional, List

from services.session_manager import SessionManager
from services.redis_session_manager import get_redis_manager, is_redis_available

logger = logging.getLogger(__name__)


class HybridSessionManager:
    """
    Hybrid session manager that uses Redis when available,
    falls back to file-based storage otherwise
    """
    
    @classmethod
    def initialize(cls):
        """Initialize both Redis and file-based storage"""
        # Initialize file-based storage
        SessionManager.initialize()
        
        # Try to initialize Redis
        if is_redis_available():
            logger.info("✅ Redis available - using Redis for session storage")
        else:
            logger.warning("⚠️ Redis not available - using file-based storage")
    
    @classmethod
    def _use_redis(cls) -> bool:
        """Check if Redis should be used"""
        return is_redis_available()
    
    @classmethod
    def create_session(
        cls,
        session_id: str,
        client_id: str,
        agent_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new session"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                result = redis_manager.create_session(session_id, client_id, agent_id, title)
                logger.debug(f"📝 Created session in Redis: {session_id}")
                return result
            except Exception as e:
                logger.warning(f"⚠️ Redis create_session failed, falling back to file: {e}")
        
        # Fallback to file-based storage
        return SessionManager.create_session(session_id, client_id, agent_id, title)
    
    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session metadata"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                result = redis_manager.get_session(session_id)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Redis get_session failed, falling back to file: {e}")
        
        # Fallback to file-based storage
        return SessionManager.get_session(session_id)
    
    @classmethod
    def update_session(cls, session_id: str, updates: Dict[str, Any]):
        """Update session metadata"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                redis_manager.update_session(session_id, updates)
                logger.debug(f"📝 Updated session in Redis: {session_id}")
                return
            except Exception as e:
                logger.warning(f"⚠️ Redis update_session failed, falling back to file: {e}")
        
        # Fallback to file-based storage
        SessionManager.update_session(session_id, updates)
    
    @classmethod
    def delete_session(cls, session_id: str):
        """Delete a session"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                redis_manager.delete_session(session_id)
                logger.debug(f"🗑️ Deleted session from Redis: {session_id}")
                return
            except Exception as e:
                logger.warning(f"⚠️ Redis delete_session failed, falling back to file: {e}")
        
        # Fallback to file-based storage
        SessionManager.delete_session(session_id)
    
    @classmethod
    def list_sessions(cls, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                return redis_manager.list_sessions(client_id)
            except Exception as e:
                logger.warning(f"⚠️ Redis list_sessions failed, falling back to file: {e}")
        
        # Fallback to file-based storage
        return SessionManager.list_sessions(client_id)
    
    @classmethod
    def save_history(cls, session_id: str, history: List[Any]):
        """Save session history"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                redis_manager.save_history(session_id, history)
                logger.debug(f"💾 Saved history to Redis: {session_id}")
                return
            except Exception as e:
                logger.warning(f"⚠️ Redis save_history failed, falling back to file: {e}")
        
        # Fallback to file-based storage
        SessionManager.save_history(session_id, history)
    
    @classmethod
    def load_history(cls, session_id: str) -> List[Dict[str, Any]]:
        """Load session history"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                result = redis_manager.load_history(session_id)
                if result:
                    return result
            except Exception as e:
                logger.warning(f"⚠️ Redis load_history failed, falling back to file: {e}")
        
        # Fallback to file-based storage
        return SessionManager.load_history(session_id)
    
    @classmethod
    def increment_message_count(cls, session_id: str):
        """Increment message count"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                redis_manager.increment_message_count(session_id)
                return
            except Exception as e:
                logger.warning(f"⚠️ Redis increment_message_count failed, falling back to file: {e}")
        
        SessionManager.increment_message_count(session_id)
    
    @classmethod
    def cleanup_expired_sessions(cls) -> int:
        """Clean up expired sessions"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                return redis_manager.cleanup_expired_sessions()
            except Exception as e:
                logger.warning(f"⚠️ Redis cleanup failed, falling back to file: {e}")
        
        return SessionManager.cleanup_expired_sessions()
    
    # Delegate other SessionManager methods
    @classmethod
    def get_session_structures_dir(cls, session_id: str):
        """Get structures directory (always use file system)"""
        return SessionManager.get_session_structures_dir(session_id)
    
    @classmethod
    def get_session_phonon_dir(cls, session_id: str):
        """Get phonon directory (always use file system)"""
        return SessionManager.get_session_phonon_dir(session_id)
    
    @classmethod
    def increment_structure_count(cls, session_id: str):
        """Increment structure count"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                session = redis_manager.get_session(session_id)
                if session:
                    count = session.get("structure_count", 0) + 1
                    redis_manager.update_session(session_id, {"structure_count": count})
                    return
            except Exception as e:
                logger.warning(f"⚠️ Redis increment_structure_count failed: {e}")
        
        SessionManager.increment_structure_count(session_id)
    
    @classmethod
    def increment_image_count(cls, session_id: str):
        """Increment image count"""
        if cls._use_redis():
            try:
                redis_manager = get_redis_manager()
                session = redis_manager.get_session(session_id)
                if session:
                    count = session.get("image_count", 0) + 1
                    redis_manager.update_session(session_id, {"image_count": count})
                    return
            except Exception as e:
                logger.warning(f"⚠️ Redis increment_image_count failed: {e}")
        
        SessionManager.increment_image_count(session_id)


# Initialize on module import
HybridSessionManager.initialize()
