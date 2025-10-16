"""
Document Ingestion Module
Handles ingestion of documents from various sources into vector store.
"""

from typing import List, Dict, Any, Optional, Callable
import structlog
from .utils import chunk_text

logger = structlog.get_logger(__name__)


class DocumentIngestion:
    """
    Handles document ingestion into vector store.
    Supports multiple document sources (ArXiv, Google Scholar, CNKI, etc.)
    """

    def __init__(self, embedding_service, vector_store):
        """
        Initialize document ingestion service.

        Args:
            embedding_service: Embedding service instance
            vector_store: Vector store instance
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def ingest_documents(
        self,
        document_ids: List[str],
        content_fetcher: Callable[[str], Dict[str, Any]],
        collection_name: str = "default",
        source_type: str = "unknown",
        max_chunk_bytes: int = 25000,
        min_chunk_chars: int = 200,
        metadata_fetcher: Optional[Callable[[str], Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Ingest documents into vector store with enhanced metadata support.

        Args:
            document_ids: List of document IDs to ingest
            content_fetcher: Function to fetch document content by ID
                            Should return dict with 'status' and 'content' keys
            collection_name: Name of the collection (default: "default")
            source_type: Type of source (arxiv, tavily, scholar, cnki, etc.)
            max_chunk_bytes: Maximum bytes per chunk
            min_chunk_chars: Minimum characters per chunk
            metadata_fetcher: Optional function to fetch additional metadata (title, authors, url, abstract, etc.)

        Returns:
            Dict containing ingestion status
        """
        if not self.embedding_service or not self.vector_store:
            return {
                'status': 'error',
                'error': 'Embedding service or vector store not available'
            }

        # Ensure collection exists
        self.vector_store.get_or_create_collection(collection_name)

        ingested_count = 0
        failed_documents = []

        for doc_id in document_ids:
            try:
                # Fetch document content
                result = content_fetcher(doc_id)

                # Check if result is valid
                if isinstance(result, dict):
                    if result.get('status') == 'error':
                        failed_documents.append({
                            'id': doc_id,
                            'error': result.get('error', 'Unknown error')
                        })
                        continue

                    # Extract content from dict
                    content = result.get('content', '')
                else:
                    # Fallback: treat as string (backward compatibility)
                    content = str(result)

                # Validate content
                if not content or len(content) < 100:
                    # Try to use abstract as fallback
                    if metadata_fetcher:
                        meta = metadata_fetcher(doc_id)
                        content = meta.get('abstract', '') or meta.get('summary', '')
                        if not content or len(content) < 100:
                            failed_documents.append({
                                'id': doc_id,
                                'error': 'No content to ingest or content too short'
                            })
                            continue
                    else:
                        failed_documents.append({
                            'id': doc_id,
                            'error': 'No content to ingest or content too short'
                        })
                        continue

                # Fetch additional metadata
                extra_metadata = {}
                if metadata_fetcher:
                    try:
                        extra_metadata = metadata_fetcher(doc_id) or {}
                    except Exception as e:
                        logger.warning(f"Failed to fetch metadata for {doc_id}: {e}")

                # Split content into chunks
                chunks = chunk_text(
                    content,
                    max_chunk_bytes=max_chunk_bytes,
                    min_chunk_chars=min_chunk_chars
                )

                if not chunks:
                    failed_documents.append({
                        'id': doc_id,
                        'error': 'No valid chunks found'
                    })
                    continue

                # Generate embeddings
                embeddings = await self.embedding_service.embed_texts(chunks)

                # Prepare enhanced metadata
                metadata = []
                for i in range(len(chunks)):
                    chunk_meta = {
                        'document_id': doc_id,
                        'collection': collection_name,
                        'source_type': source_type,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        # Add extra metadata
                        'title': extra_metadata.get('title', ''),
                        'authors': str(extra_metadata.get('authors', [])),
                        'url': extra_metadata.get('url', '') or extra_metadata.get('pdf_url', ''),
                        'published': extra_metadata.get('published', ''),
                        'abstract': extra_metadata.get('abstract', '') or extra_metadata.get('summary', ''),
                    }
                    metadata.append(chunk_meta)

                # Generate IDs
                ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

                # Add to vector store
                self.vector_store.add_documents(
                    texts=chunks,
                    embeddings=embeddings,
                    metadata=metadata,
                    ids=ids
                )

                ingested_count += 1
                logger.info(
                    f"Ingested document {doc_id} from {source_type} "
                    f"with {len(chunks)} chunks to collection '{collection_name}'"
                )

            except Exception as e:
                logger.error(f"Error ingesting document {doc_id}: {e}")
                failed_documents.append({'id': doc_id, 'error': str(e)})

        return {
            'status': 'completed',
            'ingested_documents': ingested_count,
            'failed_documents': failed_documents,
            'total_documents': self.vector_store.get_stats()['total_documents'],
            'source_type': source_type,
            'collection_name': collection_name
        }

    async def ingest_arxiv_papers(
        self,
        paper_ids: List[str],
        content_fetcher: Callable[[str], Dict[str, Any]],
        collection_name: str = "default",
        metadata_fetcher: Optional[Callable[[str], Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Ingest ArXiv papers into vector store.

        Args:
            paper_ids: List of ArXiv paper IDs
            content_fetcher: Function to fetch paper content
            collection_name: Collection name
            metadata_fetcher: Optional function to fetch paper metadata

        Returns:
            Dict containing ingestion status
        """
        return await self.ingest_documents(
            document_ids=paper_ids,
            content_fetcher=content_fetcher,
            collection_name=collection_name,
            source_type="arxiv",
            metadata_fetcher=metadata_fetcher
        )

    async def ingest_tavily_papers(
        self,
        paper_ids: List[str],
        content_fetcher: Callable[[str], Dict[str, Any]],
        collection_name: str = "default",
        metadata_fetcher: Optional[Callable[[str], Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Ingest Tavily search results into vector store.

        Args:
            paper_ids: List of paper IDs
            content_fetcher: Function to fetch paper content
            collection_name: Collection name
            metadata_fetcher: Optional function to fetch paper metadata

        Returns:
            Dict containing ingestion status
        """
        return await self.ingest_documents(
            document_ids=paper_ids,
            content_fetcher=content_fetcher,
            collection_name=collection_name,
            source_type="tavily",
            metadata_fetcher=metadata_fetcher
        )

    async def ingest_multi_source_papers(
        self,
        papers: List[Dict[str, Any]],
        collection_name: str = "default"
    ) -> Dict[str, Any]:
        """
        Ingest papers from multiple sources into vector store.

        Args:
            papers: List of paper dicts with 'id', 'content', 'source', and metadata
            collection_name: Collection name

        Returns:
            Dict containing ingestion status
        """
        if not self.embedding_service or not self.vector_store:
            return {
                'status': 'error',
                'error': 'Embedding service or vector store not available'
            }

        # Ensure collection exists
        self.vector_store.get_or_create_collection(collection_name)

        ingested_count = 0
        failed_documents = []

        for paper in papers:
            try:
                doc_id = paper.get('id') or paper.get('paper_id') or paper.get('url', 'unknown')
                content = paper.get('content', '') or paper.get('abstract', '') or paper.get('summary', '')
                source_type = paper.get('source', 'unknown')

                # Validate content
                if not content or len(content) < 100:
                    failed_documents.append({
                        'id': doc_id,
                        'error': 'No content to ingest or content too short'
                    })
                    continue

                # Split content into chunks
                chunks = chunk_text(content, max_chunk_bytes=25000, min_chunk_chars=200)

                if not chunks:
                    failed_documents.append({
                        'id': doc_id,
                        'error': 'No valid chunks found'
                    })
                    continue

                # Generate embeddings
                embeddings = await self.embedding_service.embed_texts(chunks)

                # Prepare enhanced metadata
                metadata = []
                for i in range(len(chunks)):
                    chunk_meta = {
                        'document_id': doc_id,
                        'collection': collection_name,
                        'source_type': source_type,
                        'chunk_index': i,
                        'total_chunks': len(chunks),
                        'title': paper.get('title', ''),
                        'authors': str(paper.get('authors', [])),
                        'url': paper.get('url', '') or paper.get('pdf_url', ''),
                        'published': paper.get('published', ''),
                        'abstract': paper.get('abstract', '') or paper.get('summary', ''),
                    }
                    metadata.append(chunk_meta)

                # Generate IDs
                ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]

                # Add to vector store
                self.vector_store.add_documents(
                    texts=chunks,
                    embeddings=embeddings,
                    metadata=metadata,
                    ids=ids
                )

                ingested_count += 1
                logger.info(f"Ingested {doc_id} from {source_type} to collection '{collection_name}'")

            except Exception as e:
                logger.error(f"Error ingesting paper: {e}")
                failed_documents.append({'id': paper.get('id', 'unknown'), 'error': str(e)})

        return {
            'status': 'completed',
            'ingested_documents': ingested_count,
            'failed_documents': failed_documents,
            'total_documents': self.vector_store.get_stats()['total_documents'],
            'collection_name': collection_name
        }


# Convenience function for backward compatibility
async def ingest_papers_to_vector_store(
    embedding_service,
    vector_store,
    paper_ids: List[str],
    content_fetcher: Callable[[str], Dict[str, Any]],
    collection_name: str = "default",
    source_type: str = "arxiv",
    metadata_fetcher: Optional[Callable[[str], Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Convenience function to ingest papers into vector store.

    Args:
        embedding_service: Embedding service instance
        vector_store: Vector store instance
        paper_ids: List of paper IDs
        content_fetcher: Function to fetch paper content
        collection_name: Collection name
        source_type: Source type (arxiv, tavily, etc.)
        metadata_fetcher: Optional function to fetch paper metadata

    Returns:
        Dict containing ingestion status
    """
    ingestion = DocumentIngestion(embedding_service, vector_store)
    return await ingestion.ingest_documents(
        document_ids=paper_ids,
        content_fetcher=content_fetcher,
        collection_name=collection_name,
        source_type=source_type,
        metadata_fetcher=metadata_fetcher
    )

