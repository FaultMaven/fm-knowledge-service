"""SQLAlchemy ORM models for document metadata."""

from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class DocumentModel(Base):
    """Document metadata stored in SQLite."""
    __tablename__ = "documents"

    document_id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    document_type = Column(String(50), nullable=False, index=True)
    tags = Column(JSON, nullable=False, default=list)
    doc_metadata = Column(JSON, nullable=False, default=dict)  # Renamed to avoid SQLAlchemy reserved word
    embedding_id = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<DocumentModel(document_id={self.document_id}, title={self.title})>"
