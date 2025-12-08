"""Document management business logic."""

import logging
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional, List
from ..infrastructure.database.client import DatabaseClient
from ..infrastructure.database.models import DocumentModel
from ..infrastructure.vectordb import VectorDBProvider
from ..infrastructure.vectordb.embeddings import EmbeddingGenerator
from ..models.document import DocumentCreate, DocumentUpdate, Document

logger = logging.getLogger(__name__)


class DocumentManager:
    """Business logic for document CRUD operations."""

    def __init__(
        self,
        db_client: DatabaseClient,
        vector_client: VectorDBProvider,
        embedding_gen: EmbeddingGenerator
    ):
        """Initialize document manager.

        Args:
            db_client: Database client for metadata
            vector_client: Vector database provider (deployment-neutral)
            embedding_gen: Embedding generator
        """
        self.db = db_client
        self.vector_db = vector_client
        self.embeddings = embedding_gen

    async def create_document(self, user_id: str, doc_data: DocumentCreate) -> Document:
        """Create a new document.
        
        Args:
            user_id: User ID from gateway headers
            doc_data: Document creation data
            
        Returns:
            Created document
        """
        # Generate unique IDs
        document_id = str(uuid4())
        embedding_id = f"emb_{document_id}"
        
        # Generate embedding from title + content
        combined_text = f"{doc_data.title}\n\n{doc_data.content}"
        embedding = self.embeddings.generate_embedding(combined_text)
        
        # Create database record
        db_doc = DocumentModel(
            document_id=document_id,
            user_id=user_id,
            title=doc_data.title,
            content=doc_data.content,
            document_type=doc_data.document_type,
            tags=doc_data.tags,
            doc_metadata=doc_data.metadata,  # Use doc_metadata column
            embedding_id=embedding_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        created_doc = await self.db.create_document(db_doc)
        
        # Add to vector database using provider interface
        vector_metadata = {
            "document_id": document_id,
            "user_id": user_id,
            "title": doc_data.title,
            "document_type": doc_data.document_type,
            "tags": ",".join(doc_data.tags),
        }

        await self.vector_db.upsert_vectors(
            collection_name="faultmaven_kb",
            vectors=[{
                "id": embedding_id,
                "values": embedding,
                "content": doc_data.content,
                "metadata": vector_metadata
            }]
        )
        
        logger.info(f"Created document {document_id} for user {user_id}")
        
        return Document(
            document_id=created_doc.document_id,
            user_id=created_doc.user_id,
            title=created_doc.title,
            content=created_doc.content,
            document_type=created_doc.document_type,
            tags=created_doc.tags,
            metadata=created_doc.doc_metadata,  # Access doc_metadata column
            embedding_id=created_doc.embedding_id,
            created_at=created_doc.created_at,
            updated_at=created_doc.updated_at
        )

    async def get_document(self, document_id: str, user_id: str) -> Optional[Document]:
        """Get document by ID.
        
        Args:
            document_id: Document ID
            user_id: User ID for authorization
            
        Returns:
            Document if found, None otherwise
        """
        db_doc = await self.db.get_document(document_id, user_id)
        if not db_doc:
            return None
        
        return Document(
            document_id=db_doc.document_id,
            user_id=db_doc.user_id,
            title=db_doc.title,
            content=db_doc.content,
            document_type=db_doc.document_type,
            tags=db_doc.tags,
            metadata=db_doc.doc_metadata,  # Access doc_metadata column
            embedding_id=db_doc.embedding_id,
            created_at=db_doc.created_at,
            updated_at=db_doc.updated_at
        )

    async def update_document(
        self, document_id: str, user_id: str, updates: DocumentUpdate
    ) -> Optional[Document]:
        """Update document.
        
        Args:
            document_id: Document ID
            user_id: User ID for authorization
            updates: Fields to update
            
        Returns:
            Updated document if found, None otherwise
        """
        # Get current document
        current_doc = await self.db.get_document(document_id, user_id)
        if not current_doc:
            return None
        
        # Prepare updates
        update_dict = {}
        if updates.title is not None:
            update_dict["title"] = updates.title
        if updates.content is not None:
            update_dict["content"] = updates.content
        if updates.document_type is not None:
            update_dict["document_type"] = updates.document_type
        if updates.tags is not None:
            update_dict["tags"] = updates.tags
        if updates.metadata is not None:
            update_dict["doc_metadata"] = updates.metadata  # Update doc_metadata column
        
        # Update database
        updated_doc = await self.db.update_document(document_id, user_id, **update_dict)
        if not updated_doc:
            return None
        
        # If content or title changed, regenerate embedding
        if updates.content is not None or updates.title is not None:
            combined_text = f"{updated_doc.title}\n\n{updated_doc.content}"
            embedding = self.embeddings.generate_embedding(combined_text)
            
            vector_metadata = {
                "document_id": document_id,
                "user_id": user_id,
                "title": updated_doc.title,
                "document_type": updated_doc.document_type,
                "tags": ",".join(updated_doc.tags),
            }
            
            await self.vector_db.upsert_vectors(
                collection_name="faultmaven_kb",
                vectors=[{
                    "id": updated_doc.embedding_id,
                    "values": embedding,
                    "content": updated_doc.content,
                    "metadata": vector_metadata
                }]
            )
        
        logger.info(f"Updated document {document_id}")
        
        return Document(
            document_id=updated_doc.document_id,
            user_id=updated_doc.user_id,
            title=updated_doc.title,
            content=updated_doc.content,
            document_type=updated_doc.document_type,
            tags=updated_doc.tags,
            metadata=updated_doc.doc_metadata,  # Access doc_metadata column
            embedding_id=updated_doc.embedding_id,
            created_at=updated_doc.created_at,
            updated_at=updated_doc.updated_at
        )

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete document.
        
        Args:
            document_id: Document ID
            user_id: User ID for authorization
            
        Returns:
            True if deleted, False if not found
        """
        # Get document to find embedding_id
        doc = await self.db.get_document(document_id, user_id)
        if not doc:
            return False
        
        # Delete from vector database using provider interface
        await self.vector_db.delete_vectors(
            collection_name="faultmaven_kb",
            vector_ids=[doc.embedding_id]
        )
        
        # Delete from metadata database
        deleted = await self.db.delete_document(document_id, user_id)
        
        if deleted:
            logger.info(f"Deleted document {document_id}")
        
        return deleted

    async def list_documents(
        self, 
        user_id: str, 
        limit: int = 50, 
        offset: int = 0,
        document_type: Optional[str] = None
    ) -> tuple[List[Document], int]:
        """List documents with pagination.
        
        Args:
            user_id: User ID for authorization
            limit: Maximum number of documents
            offset: Number of documents to skip
            document_type: Optional filter by document type
            
        Returns:
            Tuple of (documents list, total count)
        """
        db_docs, total_count = await self.db.list_documents(
            user_id=user_id,
            limit=limit,
            offset=offset,
            document_type=document_type
        )
        
        documents = [
            Document(
                document_id=doc.document_id,
                user_id=doc.user_id,
                title=doc.title,
                content=doc.content,
                document_type=doc.document_type,
                tags=doc.tags,
                metadata=doc.doc_metadata,  # Access doc_metadata column
                embedding_id=doc.embedding_id,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            for doc in db_docs
        ]
        
        return documents, total_count
