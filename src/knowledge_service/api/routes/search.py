"""Search endpoints."""

import logging
from fastapi import APIRouter, Depends
from typing import Optional, List
from ...models.requests import SearchRequest, SearchResponse, SearchResultItem
from ...core.search_manager import SearchManager
from ...api.dependencies import get_user_id

router = APIRouter(prefix="/api/v1/search", tags=["search"])
logger = logging.getLogger(__name__)

# These will be set by main.py
search_manager: SearchManager = None


def set_search_manager(manager: SearchManager):
    """Set the search manager instance (called from main.py)."""
    global search_manager
    globals()['search_manager'] = manager


@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic Search",
    description="""
Perform semantic/vector search across knowledge documents using AI embeddings.

**Workflow**:
1. Convert search query to vector embedding using sentence transformer
2. Query ChromaDB vector database for similar embeddings
3. Apply user_id filter for isolation
4. Apply optional document_type and tags filters
5. Rank results by semantic similarity
6. Return top matching documents with relevance scores

**Request Example**:
```json
{
  "query": "How do I troubleshoot slow database queries?",
  "limit": 10,
  "document_type": "kb_article",
  "tags": ["database", "performance"]
}
```

**Response Example**:
```json
{
  "query": "How do I troubleshoot slow database queries?",
  "results": [
    {
      "document_id": "doc_abc123",
      "title": "PostgreSQL Query Performance Tuning",
      "content": "When troubleshooting slow queries...",
      "similarity_score": 0.87,
      "document_type": "kb_article"
    }
  ],
  "total_found": 5
}
```

**How It Works**:
- Uses sentence transformers (all-MiniLM-L6-v2, 384 dimensions)
- Finds semantically similar content, not just keyword matches
- Understands context and meaning (e.g., "slow queries" matches "performance tuning")

**Storage**:
- SQLite: Retrieves document metadata for results
- ChromaDB: Performs vector similarity search on embeddings

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only searches documents owned by authenticated user
    """,
    responses={
        200: {"description": "Semantic search completed successfully"},
        401: {"description": "Missing or invalid authentication"},
        422: {"description": "Invalid search request"},
        500: {"description": "Internal server error during search"}
    }
)
async def search_documents(request: SearchRequest, user_id: str = Depends(get_user_id)):
    """Semantic search across documents."""
    results = await search_manager.search(
        query=request.query,
        user_id=user_id,
        limit=request.limit,
        document_type=request.document_type,
        tags=request.tags
    )

    return SearchResponse(
        query=request.query,
        results=[SearchResultItem(**r) for r in results],
        total_found=len(results)
    )


@router.get(
    "/similar/{document_id}",
    response_model=SearchResponse,
    summary="Find Similar Documents",
    description="""
Find documents semantically similar to a given document using vector similarity.

**Workflow**:
1. Retrieve source document from SQLite
2. Get document's embedding from ChromaDB
3. Query ChromaDB for similar embeddings
4. Apply user_id filter for isolation
5. Exclude source document from results
6. Rank by semantic similarity
7. Return top similar documents

**Query Parameters**:
- `document_id`: ID of source document (path parameter)
- `limit`: Max similar documents to return (default: 5)

**Response Example**:
```json
{
  "query": "Similar to doc_abc123",
  "results": [
    {
      "document_id": "doc_def456",
      "title": "Database Connection Optimization",
      "similarity_score": 0.82,
      "document_type": "kb_article"
    },
    {
      "document_id": "doc_ghi789",
      "title": "PostgreSQL Performance Best Practices",
      "similarity_score": 0.78,
      "document_type": "runbook"
    }
  ],
  "total_found": 2
}
```

**Use Cases**:
- "Related documents" feature
- Content recommendations
- Duplicate detection
- Knowledge base exploration

**Storage**:
- SQLite: Retrieves document metadata
- ChromaDB: Performs vector similarity search

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only searches documents owned by authenticated user
    """,
    responses={
        200: {"description": "Similar documents found successfully"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Source document not found or access denied"},
        500: {"description": "Internal server error during similarity search"}
    }
)
async def find_similar_documents(document_id: str, limit: int = 5, user_id: str = Depends(get_user_id)):
    """Find documents similar to a given document."""
    results = await search_manager.find_similar(
        document_id=document_id,
        user_id=user_id,
        limit=limit
    )

    return SearchResponse(
        query=f"Similar to {document_id}",
        results=[SearchResultItem(**r) for r in results],
        total_found=len(results)
    )
