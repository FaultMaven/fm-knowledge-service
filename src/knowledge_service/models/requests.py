"""Request and response models for API endpoints."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., min_length=1, max_length=1000)
    limit: int = Field(default=10, ge=1, le=50)
    document_type: Optional[str] = None
    tags: Optional[List[str]] = None


class SearchResultItem(BaseModel):
    """Single search result item."""
    document_id: str
    title: str
    document_type: str
    tags: List[str]
    score: float = Field(..., description="Similarity score")
    snippet: str = Field(..., description="Content snippet")


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    results: List[SearchResultItem]
    total_found: int


class DocumentListResponse(BaseModel):
    """Response model for listing documents."""
    documents: List[Dict[str, Any]]
    total_count: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str
    chroma_connected: bool
    database_connected: bool
