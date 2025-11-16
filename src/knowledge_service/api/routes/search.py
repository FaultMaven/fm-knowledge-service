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


@router.post("", response_model=SearchResponse)
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


@router.get("/similar/{document_id}", response_model=SearchResponse)
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
