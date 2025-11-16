"""Document data models."""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class DocumentBase(BaseModel):
    """Base document model with common fields."""
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    document_type: str = Field(..., description="Type: guide, article, troubleshooting, faq, other")
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentCreate(DocumentBase):
    """Model for creating a new document."""
    pass


class DocumentUpdate(BaseModel):
    """Model for updating a document."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    document_type: Optional[str] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Document(DocumentBase):
    """Full document model with database fields."""
    document_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    embedding_id: str

    class Config:
        from_attributes = True


class DocumentResponse(BaseModel):
    """API response model for a single document."""
    document_id: str
    user_id: str
    title: str
    content: str
    document_type: str
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str

    @classmethod
    def from_document(cls, doc: Document):
        """Convert Document to DocumentResponse."""
        return cls(
            document_id=doc.document_id,
            user_id=doc.user_id,
            title=doc.title,
            content=doc.content,
            document_type=doc.document_type,
            tags=doc.tags,
            metadata=doc.metadata,
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
        )
