"""Database client for metadata storage."""

import logging
from typing import Optional, List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, delete
from fm_core_lib.utils import service_startup_retry
from .models import Base, DocumentModel

logger = logging.getLogger(__name__)


class DatabaseClient:
    """Async database client for document metadata."""

    def __init__(self, database_url: str):
        """Initialize database client.
        
        Args:
            database_url: SQLAlchemy database URL (e.g., sqlite+aiosqlite:///./db.sqlite)
        """
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    @service_startup_retry
    async def verify_connection(self):
        """Verify database connection with retry logic.

        This is called before migrations/table creation to ensure the database
        is ready. Retries with exponential backoff for K8s/scale-to-zero scenarios.
        """
        async with self.engine.begin() as conn:
            await conn.execute("SELECT 1")
        logger.info("Database connection verified")

    async def initialize(self):
        """Create database tables."""
        # Verify connection first (with retry logic)
        await self.verify_connection()

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")

    async def create_document(self, document: DocumentModel) -> DocumentModel:
        """Create a new document."""
        async with self.async_session() as session:
            session.add(document)
            await session.commit()
            await session.refresh(document)
            return document

    async def get_document(self, document_id: str, user_id: str) -> Optional[DocumentModel]:
        """Get document by ID (with user authorization check)."""
        async with self.async_session() as session:
            result = await session.execute(
                select(DocumentModel).where(
                    DocumentModel.document_id == document_id,
                    DocumentModel.user_id == user_id
                )
            )
            return result.scalar_one_or_none()

    async def list_documents(
        self, user_id: str, limit: int = 50, offset: int = 0, document_type: Optional[str] = None
    ) -> tuple[List[DocumentModel], int]:
        """List documents for a user with pagination."""
        async with self.async_session() as session:
            # Build query
            query = select(DocumentModel).where(DocumentModel.user_id == user_id)
            if document_type:
                query = query.where(DocumentModel.document_type == document_type)
            
            # Get total count
            count_query = select(DocumentModel.document_id).where(DocumentModel.user_id == user_id)
            if document_type:
                count_query = count_query.where(DocumentModel.document_type == document_type)
            count_result = await session.execute(count_query)
            total_count = len(count_result.all())
            
            # Get paginated results
            query = query.limit(limit).offset(offset)
            result = await session.execute(query)
            documents = result.scalars().all()
            
            return documents, total_count

    async def update_document(self, document_id: str, user_id: str, **updates) -> Optional[DocumentModel]:
        """Update document metadata."""
        async with self.async_session() as session:
            result = await session.execute(
                select(DocumentModel).where(
                    DocumentModel.document_id == document_id,
                    DocumentModel.user_id == user_id
                )
            )
            document = result.scalar_one_or_none()
            
            if not document:
                return None
            
            for key, value in updates.items():
                if hasattr(document, key) and value is not None:
                    setattr(document, key, value)
            
            await session.commit()
            await session.refresh(document)
            return document

    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """Delete document."""
        async with self.async_session() as session:
            result = await session.execute(
                delete(DocumentModel).where(
                    DocumentModel.document_id == document_id,
                    DocumentModel.user_id == user_id
                )
            )
            await session.commit()
            return result.rowcount > 0

    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
