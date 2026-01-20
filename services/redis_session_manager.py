"""
Redis Session Manager

Provides Redis-based persistent storage for agent sessions and history.
Integrates with existing SessionManager for fallback support.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError, ConnectionError

logger = logging.getLogger(__name__)


class RedisSessionManager:
    """Manage agent sessions and history using Redis for persistence"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        socket_keepalive: bool = True,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        max_connections: int = 50
    ):
        """
        Initialize Redis connection
        
        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
            decode_responses: Automatically decode responses to strings
            socket_keepalive: Enable socket keepalive
            socket_connect_timeout: Connection timeout in seconds
            retry_on_timeout: Retry on timeout
            max_connections: Max connection pool size
        """
        # Create connection pool
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
            socket_keepalive=socket_keepalive,
            socket_connect_timeout=socket_connect_timeout,
            retry_on_timeout=retry_on_timeout,
            max_connections=max_connections
        )
        
        # Create Redis client
        self.redis_client = redis.Redis(connection_pool=self.pool)
        
        # Test connection
        try:
            self.redis_client.ping()
            logger.info(f"✅ Redis connected to {host}:{port} (db={db})")
        except ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
        
        # Key prefixes for different data types
        self.SESSION_PREFIX = "session:"
        self.HISTORY_PREFIX = "history:"
        self.METADATA_PREFIX = "metadata:"
        self.SESSION_INDEX = "sessions:index"
        
        # Expiration times
        self.SESSION_EXPIRE_SECONDS = 24 * 3600  # 24 hours
        self.HISTORY_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 days

        history_ttl = os.getenv("REDIS_HISTORY_TTL_SECONDS")
        if history_ttl is not None:
            try:
                parsed_ttl = int(history_ttl)
                if parsed_ttl <= 0:
                    self.HISTORY_EXPIRE_SECONDS = None
                else:
                    self.HISTORY_EXPIRE_SECONDS = parsed_ttl
            except ValueError:
                logger.warning(f"Invalid REDIS_HISTORY_TTL_SECONDS: {history_ttl}")
    
    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session data"""
        return f"{self.SESSION_PREFIX}{session_id}"
    
    def _history_key(self, session_id: str) -> str:
        """Generate Redis key for session history"""
        return f"{self.HISTORY_PREFIX}{session_id}"
    
    def _metadata_key(self, session_id: str) -> str:
        """Generate Redis key for session metadata"""
        return f"{self.METADATA_PREFIX}{session_id}"
    
    def create_session(
        self,
        session_id: str,
        client_id: str,
        agent_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new session in Redis
        
        Args:
            session_id: Unique session ID
            client_id: Client ID
            agent_id: Agent ID (optional)
            title: Session title (optional)
        
        Returns:
            Session metadata dict
        """
        try:
            # Create session metadata
            session_data = {
                "session_id": session_id,
                "client_id": client_id,
                "agent_id": agent_id or "",
                "title": title or f"Session {session_id[:8]}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": 0,
            }
            
            # Store session data as JSON
            session_key = self._session_key(session_id)
            self.redis_client.setex(
                session_key,
                self.SESSION_EXPIRE_SECONDS,
                json.dumps(session_data)
            )
            
            # Add to session index (sorted set by creation time)
            timestamp = datetime.now().timestamp()
            self.redis_client.zadd(self.SESSION_INDEX, {session_id: timestamp})
            
            logger.info(f"🆕 Created Redis session: {session_id} (client: {client_id}, agent: {agent_id})")
            
            return session_data
            
        except RedisError as e:
            logger.error(f"❌ Failed to create session in Redis: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata from Redis
        
        Args:
            session_id: Session ID
        
        Returns:
            Session metadata or None
        """
        try:
            session_key = self._session_key(session_id)
            data = self.redis_client.get(session_key)
            
            if data:
                return json.loads(data)
            return None
            
        except RedisError as e:
            logger.error(f"❌ Failed to get session from Redis: {e}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]):
        """
        Update session metadata in Redis
        
        Args:
            session_id: Session ID
            updates: Fields to update
        """
        try:
            session_key = self._session_key(session_id)
            
            # Get current session data
            current_data = self.get_session(session_id)
            if not current_data:
                logger.warning(f"Session {session_id} not found in Redis")
                return
            
            # Update fields
            current_data.update(updates)
            current_data["updated_at"] = datetime.now().isoformat()
            
            # Save back to Redis
            self.redis_client.setex(
                session_key,
                self.SESSION_EXPIRE_SECONDS,
                json.dumps(current_data)
            )
            
            logger.debug(f"📝 Updated Redis session: {session_id}")
            
        except RedisError as e:
            logger.error(f"❌ Failed to update session in Redis: {e}")
    
    def delete_session(self, session_id: str):
        """
        Delete a session and all its data from Redis
        
        Args:
            session_id: Session ID
        """
        try:
            # Delete session data
            session_key = self._session_key(session_id)
            history_key = self._history_key(session_id)
            metadata_key = self._metadata_key(session_id)
            
            self.redis_client.delete(session_key, history_key, metadata_key)
            
            # Remove from session index
            self.redis_client.zrem(self.SESSION_INDEX, session_id)
            
            logger.info(f"🗑️ Deleted Redis session: {session_id}")
            
        except RedisError as e:
            logger.error(f"❌ Failed to delete session from Redis: {e}")
    
    def list_sessions(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all sessions, optionally filtered by client
        
        Args:
            client_id: Optional client ID filter
        
        Returns:
            List of session metadata
        """
        try:
            # Get all session IDs from index (sorted by creation time, newest first)
            session_ids = self.redis_client.zrevrange(self.SESSION_INDEX, 0, -1)
            
            sessions = []
            for session_id in session_ids:
                session_data = self.get_session(session_id)
                if session_data:
                    # Filter by client_id if specified
                    if client_id is None or session_data.get("client_id") == client_id:
                        sessions.append(session_data)
            
            return sessions
            
        except RedisError as e:
            logger.error(f"❌ Failed to list sessions from Redis: {e}")
            return []
    
    def save_history(self, session_id: str, history: List[Any]):
        """
        Save session history to Redis
        
        Args:
            session_id: Session ID
            history: List of message/event objects
        """
        if not history:
            logger.debug(f"📝 No history to save for session {session_id}")
            return
        
        try:
            # Convert to serializable format
            serialized_history = []
            for i, msg in enumerate(history):
                try:
                    if hasattr(msg, 'model_dump'):
                        serialized_history.append(msg.model_dump())
                    elif hasattr(msg, 'to_dict'):
                        serialized_history.append(msg.to_dict())
                    elif hasattr(msg, 'dict'):
                        serialized_history.append(msg.dict())
                    elif isinstance(msg, dict):
                        serialized_history.append(msg)
                    else:
                        # Fallback: convert to dict
                        data = {}
                        for k, v in msg.__dict__.items():
                            if not k.startswith('_'):
                                try:
                                    json.dumps(v)
                                    data[k] = v
                                except (TypeError, ValueError):
                                    data[k] = str(v)
                        serialized_history.append(data)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to serialize message {i}: {e}")
                    continue
            
            if not serialized_history:
                logger.warning(f"⚠️ No messages could be serialized for session {session_id}")
                return
            
            # Save to Redis as JSON
            history_key = self._history_key(session_id)
            payload = json.dumps(serialized_history)
            if self.HISTORY_EXPIRE_SECONDS:
                self.redis_client.setex(
                    history_key,
                    self.HISTORY_EXPIRE_SECONDS,
                    payload
                )
            else:
                self.redis_client.set(history_key, payload)
            
            # Update message count in session
            self.update_session(session_id, {"message_count": len(serialized_history)})
            
            logger.info(f"💾 Saved {len(serialized_history)} messages to Redis for session {session_id}")
            
        except RedisError as e:
            logger.error(f"❌ Failed to save history to Redis: {e}")
    
    def load_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Load session history from Redis
        
        Args:
            session_id: Session ID
        
        Returns:
            List of message dicts
        """
        try:
            history_key = self._history_key(session_id)
            data = self.redis_client.get(history_key)
            
            if data:
                history = json.loads(data)
                logger.info(f"📖 Loaded {len(history)} messages from Redis for session {session_id}")
                return history
            
            return []
            
        except RedisError as e:
            logger.error(f"❌ Failed to load history from Redis: {e}")
            return []
    
    def increment_message_count(self, session_id: str):
        """Increment message count for a session"""
        session = self.get_session(session_id)
        if session:
            count = session.get("message_count", 0) + 1
            self.update_session(session_id, {"message_count": count})
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from the index
        (Redis TTL handles automatic deletion of session data)
        
        Returns:
            Number of cleaned up sessions
        """
        try:
            # Get all session IDs from index
            session_ids = self.redis_client.zrange(self.SESSION_INDEX, 0, -1)
            
            deleted_count = 0
            for session_id in session_ids:
                # Check if session still exists
                if not self.get_session(session_id):
                    # Remove from index
                    self.redis_client.zrem(self.SESSION_INDEX, session_id)
                    deleted_count += 1
                    logger.info(f"🗑️ Cleaned up expired session from index: {session_id}")
            
            return deleted_count
            
        except RedisError as e:
            logger.error(f"❌ Failed to cleanup expired sessions: {e}")
            return 0
    
    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self.redis_client.ping()
        except RedisError:
            return False
    
    def close(self):
        """Close Redis connection"""
        try:
            self.redis_client.close()
            logger.info("✅ Redis connection closed")
        except RedisError as e:
            logger.error(f"❌ Failed to close Redis connection: {e}")


# Singleton instance (initialized when Redis is available)
_redis_manager: Optional[RedisSessionManager] = None


def get_redis_manager() -> Optional[RedisSessionManager]:
    """
    Get or create Redis manager instance
    
    Returns:
        RedisSessionManager instance or None if Redis is not available
    """
    global _redis_manager
    
    if _redis_manager is None:
        try:
            # Try to create Redis manager
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", "6379"))
            password = os.getenv("REDIS_PASSWORD")
            db = int(os.getenv("REDIS_DB", "0"))
            
            _redis_manager = RedisSessionManager(
                host=host,
                port=port,
                db=db,
                password=password
            )
            logger.info("✅ Redis session manager initialized")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, using fallback storage: {e}")
            _redis_manager = None
    
    return _redis_manager


def is_redis_available() -> bool:
    """Check if Redis is available"""
    manager = get_redis_manager()
    return manager is not None and manager.ping()
