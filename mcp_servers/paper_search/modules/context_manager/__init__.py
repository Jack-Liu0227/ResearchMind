"""
Context Manager Package

上下文管理模块：
1. chroma_store - ChromaDB 向量存储服务
2. vector_store - 向量存储接口
3. embeddings - 嵌入服务
4. ingestion - 文档摄取服务
5. utils - 数据处理工具
6. services - 服务管理（全局单例）
7. cache - 缓存管理
"""

from .chroma_store import ChromaVectorStore
from .vector_store import VectorStore
from .embeddings import GoogleEmbeddings
from .ingestion import DocumentIngestion, ingest_papers_to_vector_store
from .utils import chunk_text
from .services import get_embedding_service, get_vector_store

__all__ = [
    'ChromaVectorStore',
    'VectorStore',
    'GoogleEmbeddings',
    'DocumentIngestion',
    'ingest_papers_to_vector_store',
    'chunk_text',
    'get_embedding_service',
    'get_vector_store',
]

