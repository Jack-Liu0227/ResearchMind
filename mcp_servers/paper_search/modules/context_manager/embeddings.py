"""
Google Embedding Service using Google Generative AI
"""
import os
from typing import List, Optional
from abc import ABC, abstractmethod
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingService(ABC):
    """Abstract base class for embedding services."""

    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the text embedding
        """
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one for each input text
        """
        pass

    @property
    @abstractmethod
    def vector_size(self) -> int:
        """
        Get the size of the embedding vectors.

        Returns:
            Dimension size of the embedding vectors
        """
        pass


class GoogleEmbeddings(EmbeddingService):
    """Google embedding service for generating text embeddings."""

    def __init__(self, model_name: str = 'models/text-embedding-004', api_key: Optional[str] = None) -> None:
        """
        Initialize Google embedding service.

        Args:
            model_name: Name of the Google embedding model to use
            api_key: Google API key (if None, will use environment variable)
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        self._client = None
        logger.debug(f'Initialized Google embedding service with model: {model_name}')

    @property
    def client(self):
        """
        Lazy initialization of Google GenAI client.

        Returns:
            Google GenAI client instance

        Raises:
            ImportError: If google-generativeai package is not installed
        """
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise ImportError(
                    'google-generativeai is required for Google embeddings. '
                    'Install with: pip install google-generativeai',
                )
        return self._client

    def _truncate_text(self, text: str, max_bytes: int = 30000) -> str:
        """
        Truncate text to fit within byte limit.

        Args:
            text: Input text
            max_bytes: Maximum bytes allowed (default: 30000, leaving buffer for 36000 limit)

        Returns:
            Truncated text
        """
        # Encode to bytes
        text_bytes = text.encode('utf-8')

        # If within limit, return as is
        if len(text_bytes) <= max_bytes:
            return text

        # Truncate to max_bytes
        truncated_bytes = text_bytes[:max_bytes]

        # Decode, ignoring errors at the end
        try:
            return truncated_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # If decode fails, try removing last few bytes
            for i in range(1, 5):
                try:
                    return truncated_bytes[:-i].decode('utf-8')
                except UnicodeDecodeError:
                    continue
            # Fallback: decode with errors='ignore'
            return truncated_bytes.decode('utf-8', errors='ignore')

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using Google.

        Args:
            text: Input text to embed

        Returns:
            List of float values representing the text embedding

        Raises:
            Exception: If embedding generation fails
        """
        try:
            # Truncate text if too long
            truncated_text = self._truncate_text(text)

            result = self.client.embed_content(
                model=self.model_name,
                content=truncated_text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f'Error generating embedding for text: {e}', exc_info=True)
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Automatically truncates texts that exceed byte limit.

        Args:
            texts: List of input texts to embed

        Returns:
            List of embedding vectors, one for each input text

        Raises:
            Exception: If embedding generation fails
        """
        try:
            embeddings = []
            for i, text in enumerate(texts):
                try:
                    # Truncate text if too long
                    truncated_text = self._truncate_text(text)

                    result = self.client.embed_content(
                        model=self.model_name,
                        content=truncated_text,
                        task_type="retrieval_document"
                    )
                    embeddings.append(result['embedding'])
                except Exception as e:
                    logger.error(f'Error embedding text {i}: {e}')
                    # Re-raise to let caller handle
                    raise
            return embeddings
        except Exception as e:
            logger.error(f'Error generating embeddings for {len(texts)} texts: {e}', exc_info=True)
            raise

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query text.

        Args:
            query: Query text to embed

        Returns:
            List of float values representing the query embedding
        """
        try:
            result = self.client.embed_content(
                model=self.model_name,
                content=query,
                task_type="retrieval_query"
            )
            return result['embedding']
        except Exception as e:
            logger.error(f'Error generating query embedding: {e}', exc_info=True)
            raise

    @property
    def vector_size(self) -> int:
        """
        Get the size of the embedding vectors.

        Returns:
            Dimension size of the embedding vectors (768 for text-embedding-004)
        """
        # text-embedding-004 produces 768-dimensional vectors
        return 768

