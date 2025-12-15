"""Document CRUD endpoints."""

import logging
import time
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from ...models.document import DocumentCreate, DocumentUpdate, DocumentResponse
from ...models.requests import (
    DocumentListResponse,
    UnifiedSearchRequest,
    UnifiedSearchResponse,
    SearchResultItem,
    BulkDeleteRequest,
    BulkDeleteResponse,
    KnowledgeStatsResponse,
    SearchAnalyticsResponse,
    JobStatus
)
from ...core.document_manager import DocumentManager
from ...core.search_manager import SearchManager
from ...core.job_manager import JobManager
from ...core.analytics_manager import AnalyticsManager
from ...api.dependencies import get_user_id

router = APIRouter(prefix="/api/v1/knowledge/documents", tags=["documents"])
logger = logging.getLogger(__name__)

# These will be set by main.py after creating the app
doc_manager: DocumentManager = None
search_manager: SearchManager = None
job_manager: JobManager = None
analytics_manager: AnalyticsManager = None


def set_managers(doc_mgr: DocumentManager, search_mgr: SearchManager = None,
                 job_mgr: JobManager = None, analytics_mgr: AnalyticsManager = None):
    """Set the manager instances (called from main.py)."""
    global doc_manager, search_manager, job_manager, analytics_manager
    globals()['doc_manager'] = doc_mgr
    if search_mgr:
        globals()['search_manager'] = search_mgr
    if job_mgr:
        globals()['job_manager'] = job_mgr
    if analytics_mgr:
        globals()['analytics_manager'] = analytics_mgr


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=201,
    summary="Create Document",
    description="""
Create a new knowledge document with semantic embeddings.

**Workflow**:
1. Validate document data (title, content, type)
2. Generate unique document_id
3. Create embeddings from document content using sentence transformers
4. Store metadata in SQLite database
5. Store embeddings in ChromaDB for semantic search
6. Return created document with metadata

**Request Example**:
```json
{
  "title": "PostgreSQL Connection Pooling Guide",
  "content": "Connection pooling is essential for database performance...",
  "document_type": "kb_article",
  "tags": ["postgresql", "performance", "database"],
  "metadata": {"difficulty": "intermediate"}
}
```

**Response Example**:
```json
{
  "document_id": "doc_abc123",
  "user_id": "user_123",
  "title": "PostgreSQL Connection Pooling Guide",
  "document_type": "kb_article",
  "created_at": "2025-12-15T10:30:00Z"
}
```

**Storage**:
- SQLite: Document metadata and relationships
- ChromaDB: Vector embeddings for semantic search (384 dimensions)

**Authorization**: Required (X-User-ID header)
**Rate Limits**: None
    """,
    responses={
        201: {"description": "Document created successfully"},
        401: {"description": "Missing or invalid authentication"},
        422: {"description": "Invalid document data"},
        500: {"description": "Internal server error during document creation"}
    }
)
async def create_document(doc_data: DocumentCreate, user_id: str = Depends(get_user_id)):
    """Create a new document."""
    try:
        document = await doc_manager.create_document(user_id, doc_data)
        return DocumentResponse.from_document(document)
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get Document",
    description="""
Retrieve a specific knowledge document by ID.

**Workflow**:
1. Validate document_id format
2. Query SQLite database for document metadata
3. Verify user ownership (user_id match)
4. Return document details

**Response Example**:
```json
{
  "document_id": "doc_abc123",
  "user_id": "user_123",
  "title": "PostgreSQL Connection Pooling Guide",
  "content": "Connection pooling is essential...",
  "document_type": "kb_article",
  "tags": ["postgresql", "performance"],
  "created_at": "2025-12-15T10:30:00Z",
  "updated_at": "2025-12-15T14:20:00Z"
}
```

**Storage**:
- SQLite: Reads document metadata
- ChromaDB: Not accessed for single document retrieval

**Authorization**: Required (X-User-ID header)
**User Isolation**: Returns 404 if document belongs to different user
    """,
    responses={
        200: {"description": "Document retrieved successfully"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Document not found or access denied"},
        500: {"description": "Internal server error"}
    }
)
async def get_document(document_id: str, user_id: str = Depends(get_user_id)):
    """Get document by ID."""
    document = await doc_manager.get_document(document_id, user_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_document(document)


@router.put(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update Document",
    description="""
Update an existing knowledge document's metadata or content.

**Workflow**:
1. Validate document_id and user ownership
2. Update document metadata in SQLite
3. If content changed, regenerate embeddings
4. Update embeddings in ChromaDB if content modified
5. Update updated_at timestamp
6. Return updated document

**Request Example**:
```json
{
  "title": "PostgreSQL Connection Pooling - Updated",
  "tags": ["postgresql", "performance", "production"],
  "metadata": {"difficulty": "advanced"}
}
```

**Response Example**:
```json
{
  "document_id": "doc_abc123",
  "title": "PostgreSQL Connection Pooling - Updated",
  "updated_at": "2025-12-15T15:45:00Z"
}
```

**Storage**:
- SQLite: Updates document metadata
- ChromaDB: Updates embeddings if content changed

**Authorization**: Required (X-User-ID header)
**User Isolation**: Returns 404 if document belongs to different user
    """,
    responses={
        200: {"description": "Document updated successfully"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Document not found or access denied"},
        422: {"description": "Invalid update data"},
        500: {"description": "Internal server error during update"}
    }
)
async def update_document(document_id: str, updates: DocumentUpdate, user_id: str = Depends(get_user_id)):
    """Update document."""
    document = await doc_manager.update_document(document_id, user_id, updates)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_document(document)


@router.delete(
    "/{document_id}",
    status_code=204,
    summary="Delete Document",
    description="""
Permanently delete a knowledge document and its embeddings.

**Workflow**:
1. Validate document_id and user ownership
2. Delete embeddings from ChromaDB vector store
3. Delete document metadata from SQLite database
4. Return 204 No Content on success

**Storage**:
- SQLite: Removes document record
- ChromaDB: Removes vector embeddings

**Authorization**: Required (X-User-ID header)
**User Isolation**: Returns 404 if document belongs to different user
**Warning**: This operation is irreversible
    """,
    responses={
        204: {"description": "Document deleted successfully"},
        401: {"description": "Missing or invalid authentication"},
        404: {"description": "Document not found or access denied"},
        500: {"description": "Internal server error during deletion"}
    }
)
async def delete_document(document_id: str, user_id: str = Depends(get_user_id)):
    """Delete document."""
    deleted = await doc_manager.delete_document(document_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List Documents",
    description="""
List knowledge documents with pagination and optional filtering.

**Workflow**:
1. Apply user_id filter for isolation
2. Apply optional document_type filter
3. Query SQLite database with limit/offset pagination
4. Return documents and total count

**Query Parameters**:
- `limit`: Max documents to return (default: 50)
- `offset`: Number of documents to skip (default: 0)
- `document_type`: Filter by type (optional: runbook, kb_article, diagnostic, etc.)

**Response Example**:
```json
{
  "documents": [
    {
      "document_id": "doc_abc123",
      "title": "PostgreSQL Pooling",
      "document_type": "kb_article"
    }
  ],
  "total_count": 42,
  "limit": 50,
  "offset": 0
}
```

**Storage**:
- SQLite: Queries document metadata with filters
- ChromaDB: Not accessed for listing

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only returns documents owned by authenticated user
    """,
    responses={
        200: {"description": "Document list retrieved successfully"},
        401: {"description": "Missing or invalid authentication"},
        422: {"description": "Invalid query parameters"},
        500: {"description": "Internal server error"}
    }
)
async def list_documents(
    user_id: str = Depends(get_user_id),
    limit: int = 50,
    offset: int = 0,
    document_type: Optional[str] = None
):
    """List documents with pagination."""
    documents, total_count = await doc_manager.list_documents(
        user_id=user_id,
        limit=limit,
        offset=offset,
        document_type=document_type
    )

    return DocumentListResponse(
        documents=[DocumentResponse.from_document(doc).dict() for doc in documents],
        total_count=total_count,
        limit=limit,
        offset=offset
    )


# =============================================================================
# Bulk Operations & Statistics (Phase 4)
# =============================================================================

@router.get(
    "/stats",
    summary="Get Knowledge Base Statistics",
    description="""
Retrieve comprehensive statistics about the user's knowledge base.

**Workflow**:
1. Query all user documents from SQLite
2. Calculate total document count
3. Group documents by type
4. Calculate total storage size
5. Return aggregated statistics

**Response Example**:
```json
{
  "total_documents": 127,
  "by_type": {
    "kb_article": 45,
    "runbook": 32,
    "diagnostic": 25,
    "solution": 25
  },
  "total_size_bytes": 2548736
}
```

**Use Cases**:
- Dashboard statistics display
- Storage usage monitoring
- Knowledge base health checks
- User analytics

**Storage**:
- SQLite: Queries all user documents for aggregation
- ChromaDB: Not accessed

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only counts documents owned by authenticated user
    """,
    responses={
        200: {"description": "Statistics retrieved successfully"},
        401: {"description": "Missing or invalid authentication"},
        500: {"description": "Internal server error"}
    }
)
async def get_knowledge_stats(user_id: str = Depends(get_user_id)):
    """Get knowledge base statistics for the user."""
    try:
        # Count documents by type
        all_docs, total = await doc_manager.list_documents(user_id=user_id, limit=10000, offset=0)
        
        stats = {
            "total_documents": total,
            "by_type": {},
            "total_size_bytes": 0,
        }
        
        for doc in all_docs:
            doc_type = doc.document_type or "unknown"
            stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1
            if hasattr(doc, "size_bytes") and doc.size_bytes:
                stats["total_size_bytes"] += doc.size_bytes
        
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/bulk-update",
    summary="Bulk Update Documents",
    description="""
Update multiple documents in a single batch operation.

**Workflow**:
1. Validate each update request in the batch
2. For each document:
   - Verify user ownership
   - Apply updates to SQLite metadata
   - Regenerate embeddings if content changed
   - Update ChromaDB if needed
3. Return results for each document

**Request Example**:
```json
[
  {"document_id": "doc_123", "tags": ["updated", "reviewed"]},
  {"document_id": "doc_456", "metadata": {"status": "archived"}}
]
```

**Response Example**:
```json
{
  "updated": 2,
  "failed": 0,
  "results": [
    {"document_id": "doc_123", "success": true},
    {"document_id": "doc_456", "success": true}
  ]
}
```

**Storage**:
- SQLite: Updates multiple document records
- ChromaDB: Updates embeddings for modified documents

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only updates documents owned by authenticated user
    """,
    responses={
        200: {"description": "Bulk update completed (check results for individual status)"},
        401: {"description": "Missing or invalid authentication"},
        422: {"description": "Invalid bulk update request"},
        500: {"description": "Internal server error during bulk update"}
    }
)
async def bulk_update_documents(
    updates: list[dict],
    user_id: str = Depends(get_user_id)
):
    """Bulk update multiple documents.

    Request format:
    [
        {"document_id": "doc_123", "tags": ["updated"]},
        {"document_id": "doc_456", "status": "archived"}
    ]
    """
    try:
        results = []
        for update_data in updates:
            doc_id = update_data.get("document_id")
            if not doc_id:
                results.append({"error": "Missing document_id"})
                continue
            
            # Remove document_id from updates
            updates_dict = {k: v for k, v in update_data.items() if k != "document_id"}
            
            from knowledge_service.models.document import DocumentUpdate
            doc_update = DocumentUpdate(**updates_dict)
            
            updated_doc = await doc_manager.update_document(doc_id, user_id, doc_update)
            if updated_doc:
                results.append({"document_id": doc_id, "success": True})
            else:
                results.append({"document_id": doc_id, "success": False, "error": "Not found"})
        
        return {
            "updated": sum(1 for r in results if r.get("success")),
            "failed": sum(1 for r in results if not r.get("success")),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Failed to bulk update documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Search & Collections (Phase 6.3)
# =============================================================================

@router.post(
    "/search",
    summary="Search Knowledge Base",
    description="""
Search documents using full-text search with optional filtering.

**Workflow**:
1. Apply user_id filter for isolation
2. Apply optional document_type filter
3. Query SQLite database for matching documents
4. Perform full-text search on title and content
5. Apply pagination limits
6. Return matching documents

**Request Example**:
```json
{
  "query": "PostgreSQL connection timeout",
  "document_type": "kb_article",
  "limit": 20
}
```

**Response Example**:
```json
{
  "query": "PostgreSQL connection timeout",
  "results": [
    {
      "document_id": "doc_abc123",
      "title": "PostgreSQL Connection Pooling",
      "document_type": "kb_article",
      "created_at": "2025-12-15T10:30:00Z"
    }
  ],
  "total_results": 1,
  "returned": 1
}
```

**Note**: For semantic/vector search, use `/api/v1/search` endpoint instead.

**Storage**:
- SQLite: Full-text search on document metadata
- ChromaDB: Not used (this is text search, not semantic)

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only searches documents owned by authenticated user
    """,
    responses={
        200: {"description": "Search completed successfully"},
        401: {"description": "Missing or invalid authentication"},
        422: {"description": "Invalid search parameters"},
        500: {"description": "Internal server error during search"}
    }
)
async def search_documents(
    search_params: dict,
    user_id: str = Depends(get_user_id)
):
    """Search knowledge base with filters and full-text search."""
    try:
        query = search_params.get("query", "")
        document_type = search_params.get("document_type")
        limit = search_params.get("limit", 50)
        
        # Get all documents and filter
        all_docs, total = await doc_manager.list_documents(
            user_id=user_id,
            limit=1000,
            offset=0,
            document_type=document_type
        )
        
        # Apply text search if query provided
        if query:
            query_lower = query.lower()
            filtered = [
                doc for doc in all_docs
                if query_lower in doc.title.lower() or 
                   (doc.content and query_lower in doc.content.lower())
            ]
        else:
            filtered = all_docs
        
        results = filtered[:limit]
        
        return {
            "query": query,
            "results": [
                {
                    "document_id": doc.document_id,
                    "title": doc.title,
                    "document_type": doc.document_type,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                }
                for doc in results
            ],
            "total_results": len(filtered),
            "returned": len(results)
        }
    
    except Exception as e:
        logger.error(f"Failed to search documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/collections",
    summary="List Document Collections",
    description="""
List all document collections (pseudo-collections based on document types).

**Workflow**:
1. Query all user documents from SQLite
2. Group documents by document_type
3. Count documents in each collection
4. Return collection metadata

**Response Example**:
```json
{
  "collections": [
    {
      "collection_id": "kb_article",
      "name": "Kb Article",
      "document_count": 45
    },
    {
      "collection_id": "runbook",
      "name": "Runbook",
      "document_count": 32
    }
  ],
  "total": 2
}
```

**Note**: Currently implements pseudo-collections using document_type. Full collection system planned for future release.

**Storage**:
- SQLite: Queries document metadata for grouping
- ChromaDB: Not accessed

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only includes documents owned by authenticated user
    """,
    responses={
        200: {"description": "Collections retrieved successfully"},
        401: {"description": "Missing or invalid authentication"},
        500: {"description": "Internal server error"}
    }
)
async def list_collections(user_id: str = Depends(get_user_id)):
    """List all document collections for user."""
    try:
        # TODO: Implement actual collections system
        # For now, return document types as pseudo-collections
        all_docs, _ = await doc_manager.list_documents(user_id=user_id, limit=1000, offset=0)
        
        types = {}
        for doc in all_docs:
            doc_type = doc.document_type or "uncategorized"
            types[doc_type] = types.get(doc_type, 0) + 1
        
        collections = [
            {
                "collection_id": doc_type,
                "name": doc_type.replace("_", " ").title(),
                "document_count": count
            }
            for doc_type, count in types.items()
        ]
        
        return {
            "collections": collections,
            "total": len(collections)
        }
    
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/collections",
    summary="Create Document Collection",
    description="""
Create a new document collection.

**Status**: Not yet implemented

**Planned Workflow**:
1. Validate collection name and metadata
2. Create collection record in SQLite
3. Associate collection with user_id
4. Return collection metadata

**Planned Request**:
```json
{
  "name": "Production Runbooks",
  "description": "Runbooks for production environment",
  "metadata": {"environment": "production"}
}
```

**Storage**:
- SQLite: Will store collection metadata
- ChromaDB: No impact

**Authorization**: Required (X-User-ID header)
    """,
    responses={
        201: {"description": "Collection created successfully (not implemented)"},
        401: {"description": "Missing or invalid authentication"},
        422: {"description": "Invalid collection data"},
        501: {"description": "Not yet implemented"}
    }
)
async def create_collection(
    collection_data: dict,
    user_id: str = Depends(get_user_id)
):
    """Create a new document collection."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Collection creation not yet implemented"
    )


@router.post(
    "/batch-delete",
    summary="Batch Delete Documents",
    description="""
Delete multiple documents in a single batch operation.

**Workflow**:
1. Validate document_ids list
2. For each document:
   - Verify user ownership
   - Delete embeddings from ChromaDB
   - Delete metadata from SQLite
3. Return deletion results

**Request Example**:
```json
["doc_abc123", "doc_def456", "doc_ghi789"]
```

**Response Example**:
```json
{
  "deleted": 2,
  "failed": 1,
  "failed_ids": ["doc_ghi789"]
}
```

**Storage**:
- SQLite: Removes multiple document records
- ChromaDB: Removes vector embeddings for all documents

**Authorization**: Required (X-User-ID header)
**User Isolation**: Only deletes documents owned by authenticated user
**Warning**: This operation is irreversible
    """,
    responses={
        200: {"description": "Batch deletion completed (check results for details)"},
        401: {"description": "Missing or invalid authentication"},
        422: {"description": "Invalid document IDs list"},
        500: {"description": "Internal server error during batch deletion"}
    }
)
async def batch_delete_documents(
    document_ids: list[str],
    user_id: str = Depends(get_user_id)
):
    """Delete multiple documents in batch."""
    try:
        deleted = 0
        failed = []
        
        for doc_id in document_ids:
            success = await doc_manager.delete_document(doc_id, user_id)
            if success:
                deleted += 1
            else:
                failed.append(doc_id)
        
        return {
            "deleted": deleted,
            "failed": len(failed),
            "failed_ids": failed
        }
    
    except Exception as e:
        logger.error(f"Failed to batch delete documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
