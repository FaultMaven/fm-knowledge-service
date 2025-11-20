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
