"""ChromaDB client for vector similarity search."""

import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class ChromaDBClient:
    """ChromaDB client for vector database operations."""

    def __init__(self, persist_directory: str, collection_name: str):
        """Initialize ChromaDB client.
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the ChromaDB collection
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        
        logger.info(f"Initializing ChromaDB at {persist_directory}")
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "FaultMaven Knowledge Base"}
        )
        logger.info(f"ChromaDB collection '{collection_name}' ready")

    async def add_document(
        self, 
        embedding_id: str, 
        embedding: List[float], 
        content: str,
        metadata: Dict[str, Any]
    ):
        """Add a document to the vector database.
        
        Args:
            embedding_id: Unique ID for the embedding
            embedding: Embedding vector
            content: Document content (for retrieval)
            metadata: Document metadata
        """
        self.collection.add(
            ids=[embedding_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )
        logger.debug(f"Added document with embedding_id: {embedding_id}")

    async def search(
        self, 
        query_embedding: List[float], 
        limit: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            limit: Maximum number of results
            where: Optional metadata filters
            
        Returns:
            List of search results with documents and metadata
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        formatted_results = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted_results.append({
                    "embedding_id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity_score": 1.0 - (results["distances"][0][i] / 2.0)  # Convert distance to similarity
                })
        
        return formatted_results

    async def delete_document(self, embedding_id: str):
        """Delete a document from the vector database.
        
        Args:
            embedding_id: Embedding ID to delete
        """
        self.collection.delete(ids=[embedding_id])
        logger.debug(f"Deleted document with embedding_id: {embedding_id}")

    async def update_document(
        self,
        embedding_id: str,
        embedding: List[float],
        content: str,
        metadata: Dict[str, Any]
    ):
        """Update a document in the vector database.
        
        Args:
            embedding_id: Embedding ID to update
            embedding: New embedding vector
            content: New document content
            metadata: New metadata
        """
        self.collection.update(
            ids=[embedding_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[metadata]
        )
        logger.debug(f"Updated document with embedding_id: {embedding_id}")

    def get_collection_count(self) -> int:
        """Get the number of documents in the collection."""
        return self.collection.count()
