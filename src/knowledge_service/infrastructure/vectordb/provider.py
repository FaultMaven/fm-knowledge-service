"""Vector Database Provider Interface

Deployment-neutral abstraction for vector similarity search.
Supports multiple backends:
- ChromaDB (local/persistent or remote server)
- Pinecone (managed cloud)
- Weaviate (self-hosted or cloud)
- Qdrant (self-hosted or cloud)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    """Vector search result with score and metadata."""

    id: str
    score: float
    content: str
    metadata: Dict[str, Any]


class VectorDBProvider(ABC):
    """Abstract base class for vector database providers.

    Provides deployment-neutral interface for vector operations:
    - Collection/index management
    - Document upsert (insert or update)
    - Semantic search
    - Document deletion
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the vector database connection.

        Performs startup checks:
        - Verify connection/authentication
        - Create default collections if needed
        - Apply retry logic for K8s volume mounts

        Raises:
            ConnectionError: If unable to connect after retries
        """
        pass

    @abstractmethod
    async def create_collection(
        self,
        name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create or verify a collection/index exists.

        Args:
            name: Collection/index name
            dimension: Vector dimension (e.g., 384 for all-MiniLM-L6-v2)
            metadata: Optional collection metadata

        Note:
            Should be idempotent - no-op if collection already exists
        """
        pass

    @abstractmethod
    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]]
    ) -> None:
        """Insert or update vectors in the collection.

        Args:
            collection_name: Target collection name
            vectors: List of vector records, each containing:
                - id (str): Unique identifier
                - values (List[float]): Embedding vector
                - content (str): Original document content
                - metadata (Dict[str, Any]): Document metadata

        Example:
            await provider.upsert_vectors("kb_docs", [
                {
                    "id": "emb_doc1",
                    "values": [0.1, 0.2, ...],
                    "content": "The quick brown fox...",
                    "metadata": {
                        "document_id": "doc1",
                        "user_id": "user123",
                        "title": "Introduction"
                    }
                }
            ])
        """
        pass

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Perform semantic search against the vector index.

        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            limit: Maximum number of results
            filter: Optional metadata filters (e.g., {"user_id": "user123"})

        Returns:
            List of search results ordered by relevance (highest score first)

        Note:
            Score normalization:
            - 1.0 = perfect match
            - 0.0 = orthogonal/unrelated
            - Higher is better
        """
        pass

    @abstractmethod
    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> None:
        """Delete vectors from the collection.

        Args:
            collection_name: Target collection name
            vector_ids: List of vector IDs to delete
        """
        pass

    @abstractmethod
    async def get_collection_count(self, collection_name: str) -> int:
        """Get the number of vectors in a collection.

        Args:
            collection_name: Collection to count

        Returns:
            Number of vectors in the collection
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the vector database is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        pass
