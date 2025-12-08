"""ChromaDB Local Provider

Local/persistent ChromaDB implementation for development and self-hosted deployments.
Uses embedded ChromaDB with persistent disk storage.
"""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from fm_core_lib.utils import service_startup_retry

from .provider import VectorDBProvider, SearchResult

logger = logging.getLogger(__name__)


class ChromaLocalProvider(VectorDBProvider):
    """ChromaDB local provider with persistent storage.

    Deployment scenarios:
    - Development: Local disk persistence
    - Self-hosted Docker: Docker volume mounts
    - K8s: Persistent volume claims (PVC)

    Note:
        This provider uses embedded ChromaDB which runs in-process.
        For high-scale deployments, consider using a remote Chroma server
        or a managed service like Pinecone.
    """

    def __init__(self, persist_directory: str, collection_name: str):
        """Initialize ChromaDB local provider.

        Args:
            persist_directory: Directory for persistent storage
            collection_name: Default collection name

        Note:
            Actual initialization happens in initialize() to support retry logic
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.client: Optional[chromadb.Client] = None
        self.collection: Optional[chromadb.Collection] = None

        logger.info(
            f"ChromaDB local provider created "
            f"(persist_dir={persist_directory}, collection={collection_name})"
        )

    @service_startup_retry
    async def initialize(self) -> None:
        """Initialize ChromaDB with retry logic.

        Handles cases where persist directory might not be immediately available:
        - K8s persistent volume mounts
        - NFS mount delays
        - Docker volume initialization

        Raises:
            ConnectionError: If unable to initialize after retries
        """
        logger.info(f"Initializing ChromaDB at {self.persist_directory}")

        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False
                )
            )

            # Verify connection works
            self.client.heartbeat()

            # Get or create default collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "FaultMaven Knowledge Base"}
            )

            logger.info(
                f"ChromaDB initialized successfully: "
                f"collection='{self.collection_name}', "
                f"vectors={self.collection.count()}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise ConnectionError(f"ChromaDB initialization failed: {e}")

    async def create_collection(
        self,
        name: str,
        dimension: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create or verify a collection exists.

        Args:
            name: Collection name
            dimension: Vector dimension (not used by ChromaDB, inferred from data)
            metadata: Optional collection metadata

        Note:
            ChromaDB automatically creates collections on first use.
            This method is idempotent.
        """
        if not self.client:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

        collection_metadata = metadata or {}
        collection_metadata.setdefault("description", "FaultMaven Knowledge Base")

        collection = self.client.get_or_create_collection(
            name=name,
            metadata=collection_metadata
        )

        logger.info(f"Collection '{name}' ready (count={collection.count()})")

    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[Dict[str, Any]]
    ) -> None:
        """Insert or update vectors in ChromaDB.

        Args:
            collection_name: Target collection name
            vectors: List of vector records with id, values, content, metadata

        Note:
            ChromaDB's upsert automatically handles both insert and update
        """
        if not self.client:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

        # Get or create collection
        collection = self.client.get_or_create_collection(name=collection_name)

        # Extract components for ChromaDB API
        ids = [v["id"] for v in vectors]
        embeddings = [v["values"] for v in vectors]
        documents = [v.get("content", "") for v in vectors]
        metadatas = [v.get("metadata", {}) for v in vectors]

        # Upsert to ChromaDB
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )

        logger.debug(
            f"Upserted {len(vectors)} vectors to collection '{collection_name}'"
        )

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Perform semantic search using ChromaDB.

        Args:
            collection_name: Collection to search
            query_vector: Query embedding
            limit: Maximum number of results
            filter: Optional metadata filters (where clause)

        Returns:
            List of search results ordered by relevance

        Note:
            ChromaDB returns L2 distance. We convert to similarity score:
            similarity = 1.0 - (distance / 2.0)
        """
        if not self.client:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

        # Get collection
        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception as e:
            logger.warning(f"Collection '{collection_name}' not found: {e}")
            return []

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=limit,
            where=filter,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        search_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                # Convert L2 distance to similarity score (0-1 range, higher is better)
                distance = results["distances"][0][i]
                similarity_score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))

                search_results.append(SearchResult(
                    id=results["ids"][0][i],
                    score=similarity_score,
                    content=results["documents"][0][i],
                    metadata=results["metadatas"][0][i]
                ))

        logger.debug(
            f"Search in '{collection_name}' returned {len(search_results)} results"
        )

        return search_results

    async def delete_vectors(
        self,
        collection_name: str,
        vector_ids: List[str]
    ) -> None:
        """Delete vectors from ChromaDB collection.

        Args:
            collection_name: Target collection name
            vector_ids: List of vector IDs to delete
        """
        if not self.client:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

        try:
            collection = self.client.get_collection(name=collection_name)
            collection.delete(ids=vector_ids)
            logger.debug(
                f"Deleted {len(vector_ids)} vectors from '{collection_name}'"
            )
        except Exception as e:
            logger.error(f"Failed to delete vectors from '{collection_name}': {e}")
            raise

    async def get_collection_count(self, collection_name: str) -> int:
        """Get the number of vectors in a collection.

        Args:
            collection_name: Collection to count

        Returns:
            Number of vectors in the collection
        """
        if not self.client:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

        try:
            collection = self.client.get_collection(name=collection_name)
            return collection.count()
        except Exception:
            return 0

    async def health_check(self) -> bool:
        """Check if ChromaDB is healthy and responsive.

        Returns:
            True if healthy, False otherwise
        """
        if not self.client:
            return False

        try:
            self.client.heartbeat()
            return True
        except Exception as e:
            logger.error(f"ChromaDB health check failed: {e}")
            return False
