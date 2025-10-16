"""
Simple in-memory vector store for paper content
"""
import numpy as np
from typing import List, Dict, Any, Tuple
import structlog

logger = structlog.get_logger(__name__)


class VectorStore:
    """Simple in-memory vector store using cosine similarity."""

    def __init__(self):
        """Initialize the vector store."""
        self.vectors: List[np.ndarray] = []
        self.metadata: List[Dict[str, Any]] = []
        self.ids: List[str] = []
        logger.debug('Initialized VectorStore')

    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: List[str]
    ) -> None:
        """
        Add documents to the vector store.

        Args:
            texts: List of text content
            embeddings: List of embedding vectors
            metadata: List of metadata dictionaries
            ids: List of document IDs
        """
        for i, (text, embedding, meta, doc_id) in enumerate(zip(texts, embeddings, metadata, ids)):
            self.vectors.append(np.array(embedding))
            self.metadata.append({**meta, 'text': text})
            self.ids.append(doc_id)
        
        logger.info(f'Added {len(texts)} documents to vector store. Total: {len(self.vectors)}')

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using cosine similarity.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            filter_metadata: Optional metadata filter

        Returns:
            List of search results with metadata and scores
        """
        if not self.vectors:
            logger.warning('Vector store is empty')
            return []

        query_vec = np.array(query_embedding)
        
        # Calculate cosine similarities
        similarities = []
        for i, vec in enumerate(self.vectors):
            # Apply metadata filter if provided
            if filter_metadata:
                match = all(
                    self.metadata[i].get(k) == v
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue
            
            # Cosine similarity
            similarity = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec))
            similarities.append((i, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get top k results
        results = []
        for idx, score in similarities[:top_k]:
            results.append({
                'id': self.ids[idx],
                'score': float(score),
                'metadata': self.metadata[idx],
                'text': self.metadata[idx].get('text', '')
            })
        
        logger.info(f'Search returned {len(results)} results')
        return results

    def clear(self) -> None:
        """Clear all documents from the vector store."""
        self.vectors = []
        self.metadata = []
        self.ids = []
        logger.info('Cleared vector store')

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        return {
            'total_documents': len(self.vectors),
            'vector_dimension': len(self.vectors[0]) if self.vectors else 0
        }

