"""Pinecone Vector Database Provider

Managed cloud vector database for enterprise-scale deployments.
Supports serverless indexes with automatic scaling.
"""

import logging
from typing import List, Dict, Any, Optional
from fm_core_lib.utils import service_startup_retry

from .provider import VectorDBProvider, SearchResult

logger = logging.getLogger(__name__)

# Pinecone import with graceful fallback
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning(
        "Pinecone library not installed. "
        "Install with: pip install pinecone-client"
    )


class PineconeProvider(VectorDBProvider):
    """Pinecone managed vector database provider.

    Deployment scenarios:
    - Enterprise production: Fully managed, auto-scaling
    - Multi-region: Global deployment with low latency
    - High scale: Millions+ vectors with sub-100ms queries

    Environment Variables:
        PINECONE_API_KEY: Pinecone API key (required)
        PINECONE_ENVIRONMENT: Cloud environment (e.g., "us-west1-gcp")
        PINECONE_INDEX_NAME: Index name (default: faultmaven-kb)

    Pricing Note:
        Pinecone serverless charges based on:
        - Read/write operations
        - Storage (per GB)
        - No idle costs for serverless indexes
    """

    def __init__(
        self,
        api_key: str,
        environment: str = "us-east-1-aws",
        index_name: str = "faultmaven-kb",
        dimension: int = 384  # Default for all-MiniLM-L6-v2
    ):
        """Initialize Pinecone provider.

        Args:
            api_key: Pinecone API key
            environment: Pinecone cloud environment
            index_name: Default index name
            dimension: Vector dimension for new indexes

        Raises:
            ImportError: If pinecone library not installed
        """
        if not PINECONE_AVAILABLE:
            raise ImportError(
                "Pinecone library not installed. "
                "Install with: pip install pinecone-client"
            )

        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.dimension = dimension

        self.client: Optional[Pinecone] = None
        self.index = None

        logger.info(
            f"Pinecone provider created (env={environment}, index={index_name})"
        )

    @service_startup_retry
    async def initialize(self) -> None:
        """Initialize Pinecone connection with retry logic.

        Handles temporary network issues and API rate limits.

        Raises:
            ConnectionError: If unable to connect after retries
        """
        logger.info("Initializing Pinecone client")

        try:
            # Initialize Pinecone client
            self.client = Pinecone(api_key=self.api_key)

            # Get or create index
            existing_indexes = [idx.name for idx in self.client.list_indexes()]

            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: {self.index_name}")
                self.client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.environment.split("-")[0]  # Extract region
                    )
                )

            # Connect to index
            self.index = self.client.Index(self.index_name)

            # Verify connection
            stats = self.index.describe_index_stats()
            logger.info(
                f"Pinecone initialized successfully: "
                f"index={self.index_name}, "
                f"vectors={stats.total_vector_count}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise ConnectionError(f"Pinecone initialization failed: {e}")

    async def create_collection(
        self,
        name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create or verify a Pinecone index exists.

        Args:
            name: Index name
            dimension: Vector dimension
            metadata: Optional index metadata (not used by Pinecone)

        Note:
            Pinecone uses "indexes" instead of "collections".
            Index creation can take 1-2 minutes for serverless.
        """
        if not self.client:
            raise RuntimeError("Pinecone not initialized. Call initialize() first.")

        existing_indexes = [idx.name for idx in self.client.list_indexes()]

        if name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {name} (dimension={dimension})")

            self.client.create_index(
                name=name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.environment.split("-")[0]
                )
            )

            logger.info(f"Index '{name}' created successfully")
        else:
            logger.debug(f"Index '{name}' already exists")

    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]]
    ) -> None:
        """Insert or update vectors in Pinecone index.

        Args:
            collection_name: Target index name
            vectors: List of vector records with id, values, content, metadata

        Note:
            Pinecone automatically batches large upserts.
            Metadata is stored with vectors for filtering.
        """
        if not self.client:
            raise RuntimeError("Pinecone not initialized. Call initialize() first.")

        # Get index
        index = self.client.Index(collection_name)

        # Format vectors for Pinecone
        pinecone_vectors = []
        for v in vectors:
            # Store content in metadata since Pinecone doesn't have a separate content field
            metadata = v.get("metadata", {}).copy()
            metadata["content"] = v.get("content", "")

            pinecone_vectors.append({
                "id": v["id"],
                "values": v["values"],
                "metadata": metadata
            })

        # Upsert to Pinecone (automatically batched)
        index.upsert(vectors=pinecone_vectors)

        logger.debug(
            f"Upserted {len(vectors)} vectors to index '{collection_name}'"
        )

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Perform semantic search using Pinecone.

        Args:
            collection_name: Index to search
            query_vector: Query embedding
            limit: Maximum number of results (top_k)
            filter: Optional metadata filters

        Returns:
            List of search results ordered by relevance

        Note:
            Pinecone returns cosine similarity (0-1 range, higher is better).
            Metadata filters use Pinecone's filter syntax.
        """
        if not self.client:
            raise RuntimeError("Pinecone not initialized. Call initialize() first.")

        # Get index
        index = self.client.Index(collection_name)

        # Query Pinecone
        try:
            results = index.query(
                vector=query_vector,
                top_k=limit,
                filter=filter,
                include_metadata=True
            )

            # Format results
            search_results = []
            for match in results.matches:
                # Extract content from metadata
                content = match.metadata.pop("content", "")

                search_results.append(SearchResult(
                    id=match.id,
                    score=match.score,  # Cosine similarity (0-1)
                    content=content,
                    metadata=match.metadata
                ))

            logger.debug(
                f"Search in '{collection_name}' returned {len(search_results)} results"
            )

            return search_results

        except Exception as e:
            logger.error(f"Pinecone search failed: {e}")
            return []

    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> None:
        """Delete vectors from Pinecone index.

        Args:
            collection_name: Target index name
            vector_ids: List of vector IDs to delete
        """
        if not self.client:
            raise RuntimeError("Pinecone not initialized. Call initialize() first.")

        try:
            index = self.client.Index(collection_name)
            index.delete(ids=vector_ids)
            logger.debug(
                f"Deleted {len(vector_ids)} vectors from '{collection_name}'"
            )
        except Exception as e:
            logger.error(f"Failed to delete vectors from '{collection_name}': {e}")
            raise

    async def get_collection_count(self, collection_name: str) -> int:
        """Get the number of vectors in a Pinecone index.

        Args:
            collection_name: Index to count

        Returns:
            Number of vectors in the index
        """
        if not self.client:
            raise RuntimeError("Pinecone not initialized. Call initialize() first.")

        try:
            index = self.client.Index(collection_name)
            stats = index.describe_index_stats()
            return stats.total_vector_count
        except Exception:
            return 0

    async def health_check(self) -> bool:
        """Check if Pinecone is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        if not self.client or not self.index:
            return False

        try:
            # Try to get index stats as health check
            self.index.describe_index_stats()
            return True
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            return False
