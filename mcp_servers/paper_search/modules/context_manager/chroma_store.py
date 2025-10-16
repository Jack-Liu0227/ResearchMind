"""
ChromaDB-based persistent vector store for paper search.
Provides persistent storage for paper embeddings and metadata.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ChromaVectorStore:
    """ChromaDB-based persistent vector store with session-level storage"""

    def __init__(self, persist_directory: str = "./chroma_db", session_id: Optional[str] = None):
        """
        Initialize ChromaDB vector store

        Args:
            persist_directory: Base directory to persist the database
            session_id: Optional session ID for session-level storage
        """
        # If session_id is provided, use session-level storage
        if session_id:
            from ..shared.session_folder_manager import get_session_folder
            session_folder = get_session_folder(session_id)
            self.persist_directory = Path(session_folder) / "chroma_db"
            logger.info(f"Using session-level ChromaDB for session {session_id[:8]}")
        else:
            self.persist_directory = Path(persist_directory)
            logger.info(f"Using global ChromaDB")

        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # Default collection
        self.collection = None

        logger.info(f"ChromaDB initialized at {self.persist_directory}")
    
    def get_or_create_collection(self, name: str = "papers"):
        """
        Get or create a collection
        
        Args:
            name: Collection name
            
        Returns:
            ChromaDB collection
        """
        try:
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata={"description": "ArXiv papers collection"}
            )
            logger.info(f"Collection '{name}' ready with {self.collection.count()} documents")
            return self.collection
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            return None
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: List[Dict[str, Any]],
        ids: List[str]
    ):
        """
        Add documents to the collection
        
        Args:
            texts: List of text chunks
            embeddings: List of embedding vectors
            metadata: List of metadata dicts
            ids: List of unique IDs
        """
        if not self.collection:
            self.get_or_create_collection()
        
        try:
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadata,
                ids=ids
            )
            
            logger.info(f"Added {len(texts)} documents to ChromaDB")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        collection_name: str = "papers",
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents in a specific collection

        Args:
            query_embedding: Query embedding vector
            collection_name: Name of collection to search (default: "papers")
            top_k: Number of results to return
            filter: Optional metadata filter (e.g., {"source_type": "arxiv"})

        Returns:
            List of search results with content, metadata, and scores
        """
        try:
            # Get or create the collection
            collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"Collection: {collection_name}"}
            )

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter
            )

            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'collection': collection_name
                    })

            logger.info(f"Search completed in collection '{collection_name}': {len(formatted_results)} results")
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching documents in collection '{collection_name}': {e}")
            return []

    def search_multi_collections(
        self,
        query_embedding: List[float],
        collection_names: List[str],
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search across multiple collections

        Args:
            query_embedding: Query embedding vector
            collection_names: List of collection names to search
            top_k: Number of results per collection
            filter: Optional metadata filter

        Returns:
            Dict mapping collection names to search results
        """
        results = {}
        for collection_name in collection_names:
            try:
                collection_results = self.search(
                    query_embedding=query_embedding,
                    collection_name=collection_name,
                    top_k=top_k,
                    filter=filter
                )
                results[collection_name] = collection_results
            except Exception as e:
                logger.error(f"Error searching collection '{collection_name}': {e}")
                results[collection_name] = []

        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics
        
        Returns:
            Dict with statistics
        """
        if not self.collection:
            return {
                'total_documents': 0,
                'persist_directory': str(self.persist_directory)
            }
        
        try:
            count = self.collection.count()
            return {
                'total_documents': count,
                'persist_directory': str(self.persist_directory),
                'collection_name': self.collection.name
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'total_documents': 0,
                'persist_directory': str(self.persist_directory),
                'error': str(e)
            }
    
    def delete_collection(self, name: str = "papers"):
        """
        Delete a collection
        
        Args:
            name: Collection name to delete
        """
        try:
            self.client.delete_collection(name=name)
            logger.info(f"Deleted collection: {name}")
            if self.collection and self.collection.name == name:
                self.collection = None
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
    
    def list_collections(self) -> List[str]:
        """
        List all collections
        
        Returns:
            List of collection names
        """
        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document dict or None
        """
        if not self.collection:
            return None
        
        try:
            result = self.collection.get(ids=[doc_id])
            if result['ids']:
                return {
                    'id': result['ids'][0],
                    'content': result['documents'][0],
                    'metadata': result['metadatas'][0]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            return None
    
    def delete_documents(self, ids: List[str]):
        """
        Delete documents by IDs
        
        Args:
            ids: List of document IDs to delete
        """
        if not self.collection:
            logger.warning("No collection available for deletion")
            return
        
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from ChromaDB")
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")

