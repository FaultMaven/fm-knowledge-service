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
