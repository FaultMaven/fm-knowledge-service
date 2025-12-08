"""Semantic search business logic."""

import logging
from typing import List, Dict, Any, Optional
from ..infrastructure.vectordb import VectorDBProvider
from ..infrastructure.vectordb.embeddings import EmbeddingGenerator
from ..infrastructure.database.client import DatabaseClient

logger = logging.getLogger(__name__)


class SearchManager:
    """Business logic for semantic search operations."""

    def __init__(
        self,
        db_client: DatabaseClient,
        vector_client: VectorDBProvider,
        embedding_gen: EmbeddingGenerator
    ):
        """Initialize search manager.

        Args:
            db_client: Database client for metadata
            vector_client: Vector database provider (deployment-neutral)
            embedding_gen: Embedding generator
        """
        self.db = db_client
        self.vector_db = vector_client
        self.embeddings = embedding_gen

    async def search(
        self, 
        query: str, 
        user_id: str,
        limit: int = 10,
        document_type: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Perform semantic search.
        
        Args:
            query: Search query text
            user_id: User ID for authorization
            limit: Maximum number of results
            document_type: Optional filter by document type
            tags: Optional filter by tags
            
        Returns:
            List of search results with relevance scores
        """
        # Generate query embedding
        query_embedding = self.embeddings.generate_embedding(query)

        # Build metadata filters
        where_filter = {"user_id": user_id}
        if document_type:
            where_filter["document_type"] = document_type
        # Note: Tag filtering done post-query for provider compatibility

        # Search vector database using provider interface
        vector_results = await self.vector_db.search(
            collection_name="faultmaven_kb",
            query_vector=query_embedding,
            limit=limit * 2,  # Get more results for tag filtering
            filter=where_filter
        )

        # Filter by tags if specified
        if tags:
            filtered_results = []
            for result in vector_results:
                result_tags = result.metadata.get("tags", "").split(",")
                result_tags = [t.strip() for t in result_tags if t.strip()]
                if any(tag in result_tags for tag in tags):
                    filtered_results.append(result)
            vector_results = filtered_results

        # Limit to requested size
        vector_results = vector_results[:limit]

        # Format results (SearchResult model is already normalized)
        search_results = []
        for result in vector_results:
            search_results.append({
                "document_id": result.metadata["document_id"],
                "title": result.metadata["title"],
                "document_type": result.metadata["document_type"],
                "tags": [t.strip() for t in result.metadata.get("tags", "").split(",") if t.strip()],
                "score": result.score,  # Already normalized 0-1 by provider
                "snippet": result.content[:200] + "..." if len(result.content) > 200 else result.content
            })
        
        logger.info(f"Search for '{query}' returned {len(search_results)} results")
        return search_results

    async def find_similar(
        self, document_id: str, user_id: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar documents.
        
        Args:
            document_id: Source document ID
            user_id: User ID for authorization
            limit: Maximum number of results
            
        Returns:
            List of similar documents
        """
        # Get source document
        source_doc = await self.db.get_document(document_id, user_id)
        if not source_doc:
            return []
        
        # Generate embedding for source document
        combined_text = f"{source_doc.title}\n\n{source_doc.content}"
        query_embedding = self.embeddings.generate_embedding(combined_text)
        
        # Search for similar documents using provider interface
        where_filter = {"user_id": user_id}
        vector_results = await self.vector_db.search(
            collection_name="faultmaven_kb",
            query_vector=query_embedding,
            limit=limit + 1,  # +1 to account for source document
            filter=where_filter
        )

        # Filter out source document and format results
        search_results = []
        for result in vector_results:
            if result.metadata["document_id"] != document_id:
                search_results.append({
                    "document_id": result.metadata["document_id"],
                    "title": result.metadata["title"],
                    "document_type": result.metadata["document_type"],
                    "tags": [t.strip() for t in result.metadata.get("tags", "").split(",") if t.strip()],
                    "score": result.score,  # Already normalized 0-1 by provider
                    "snippet": result.content[:200] + "..." if len(result.content) > 200 else result.content
                })
        
        return search_results[:limit]
