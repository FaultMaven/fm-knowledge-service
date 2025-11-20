"""Document CRUD endpoints."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from ...models.document import DocumentCreate, DocumentUpdate, DocumentResponse
from ...models.requests import DocumentListResponse
from ...core.document_manager import DocumentManager
from ...api.dependencies import get_user_id

router = APIRouter(prefix="/api/v1/knowledge/documents", tags=["documents"])
logger = logging.getLogger(__name__)

# These will be set by main.py after creating the app
doc_manager: DocumentManager = None


def set_doc_manager(manager: DocumentManager):
    """Set the document manager instance (called from main.py)."""
    global doc_manager
    globals()['doc_manager'] = manager


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(doc_data: DocumentCreate, user_id: str = Depends(get_user_id)):
    """Create a new document."""
    try:
        document = await doc_manager.create_document(user_id, doc_data)
        return DocumentResponse.from_document(document)
    except Exception as e:
        logger.error(f"Failed to create document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, user_id: str = Depends(get_user_id)):
    """Get document by ID."""
    document = await doc_manager.get_document(document_id, user_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_document(document)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(document_id: str, updates: DocumentUpdate, user_id: str = Depends(get_user_id)):
    """Update document."""
    document = await doc_manager.update_document(document_id, user_id, updates)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.from_document(document)


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, user_id: str = Depends(get_user_id)):
    """Delete document."""
    deleted = await doc_manager.delete_document(document_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.get("", response_model=DocumentListResponse)
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

@router.get("/stats", summary="Get knowledge base statistics")
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


@router.post("/bulk-update", summary="Bulk update documents")
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

@router.post("/search", summary="Search knowledge base")
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


@router.get("/collections", summary="List document collections")
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


@router.post("/collections", summary="Create document collection")
async def create_collection(
    collection_data: dict,
    user_id: str = Depends(get_user_id)
):
    """Create a new document collection."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Collection creation not yet implemented"
    )


@router.post("/batch-delete", summary="Batch delete documents")
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
