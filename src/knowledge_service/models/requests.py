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


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations."""
    document_ids: List[str] = Field(..., min_items=1, description="List of document IDs to delete")


class BulkDeleteResponse(BaseModel):
    """Response model for bulk delete operations."""
    deleted: int
    failed: int
    failed_ids: List[str] = Field(default_factory=list)


class KnowledgeStatsResponse(BaseModel):
    """Response model for knowledge base statistics."""
    total_documents: int
    by_type: Dict[str, int]
    total_size_bytes: int
    total_users: int = Field(default=0, description="Total unique users")
    last_updated: Optional[str] = Field(None, description="Last document update timestamp")


class SearchAnalyticsResponse(BaseModel):
    """Response model for search analytics."""
    total_searches: int
    top_queries: List[Dict[str, Any]] = Field(default_factory=list)
    avg_results_per_query: float
    search_trends: Dict[str, int] = Field(default_factory=dict)


class JobStatus(BaseModel):
    """Job status response model."""
    job_id: str
    status: str = Field(..., description="Status: pending, processing, completed, failed")
    job_type: str = Field(..., description="Type: bulk_delete, bulk_update, ingestion, etc.")
    created_at: str
    updated_at: str
    progress: Optional[float] = Field(None, ge=0, le=100, description="Progress percentage")
    result: Optional[Dict[str, Any]] = Field(None, description="Job result data")
    error: Optional[str] = Field(None, description="Error message if failed")


class UnifiedSearchRequest(BaseModel):
    """Unified search request with multiple search modes."""
    query: str = Field(..., min_length=1, max_length=1000)
    search_mode: str = Field(default="semantic", description="Mode: semantic, keyword, or hybrid")
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)
    document_type: Optional[str] = None
    tags: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UnifiedSearchResponse(BaseModel):
    """Unified search response with enhanced metadata."""
    query: str
    search_mode: str
    results: List[SearchResultItem]
    total_found: int
    returned: int
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
