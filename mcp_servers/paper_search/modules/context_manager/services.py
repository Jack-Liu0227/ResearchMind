"""
Service Management Module
Provides lazy-loaded singleton instances of core services.
"""

import os
import structlog
from typing import Optional
from .chroma_store import ChromaVectorStore
from .embeddings import GoogleEmbeddings
from .vector_store import VectorStore

logger = structlog.get_logger()

# Global service instances
embedding_service = None

# Session-level vector stores
session_vector_stores = {}


def get_embedding_service():
    """Lazy load embedding service"""
    global embedding_service
    if embedding_service is None:
        try:
            embedding_service = GoogleEmbeddings()
        except Exception as e:
            logger.warning(f"Failed to initialize embedding service: {e}")
            embedding_service = None
    return embedding_service


def get_vector_store(session_id: Optional[str] = None):
    """
    Get vector store (ChromaDB) for a session

    Args:
        session_id: Optional session ID for session-level storage

    Returns:
        ChromaVectorStore instance
    """
    global session_vector_stores

    # If no session_id, use global vector store
    if not session_id:
        if 'global' not in session_vector_stores:
            try:
                persist_dir = os.getenv('CHROMA_PERSIST_DIR', './chroma_db')
                session_vector_stores['global'] = ChromaVectorStore(persist_directory=persist_dir)
                session_vector_stores['global'].get_or_create_collection("papers")
                logger.info(f"Global ChromaDB vector store initialized at {persist_dir}")
            except Exception as e:
                logger.error(f"Failed to initialize global vector store: {e}")
                return None
        return session_vector_stores['global']

    # Session-level vector store
    if session_id not in session_vector_stores:
        try:
            session_vector_stores[session_id] = ChromaVectorStore(session_id=session_id)
            session_vector_stores[session_id].get_or_create_collection("papers")
            logger.info(f"Session-level ChromaDB initialized for session {session_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to initialize session vector store: {e}")
            return None

    return session_vector_stores[session_id]




