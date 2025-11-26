"""Knowledge service unified API endpoints - Ported from monolith."""

import logging
import time
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, Depends

from ...models.requests import (
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

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
logger = logging.getLogger(__name__)

# Global instances - will be set by main.py
doc_manager: DocumentManager = None
search_manager: SearchManager = None
job_manager: JobManager = None
analytics_manager: AnalyticsManager = None


def set_managers(doc_mgr: DocumentManager, search_mgr: SearchManager,
                 job_mgr: JobManager, analytics_mgr: AnalyticsManager):
    """Set manager instances (called from main.py)."""
    global doc_manager, search_manager, job_manager, analytics_manager
    globals()['doc_manager'] = doc_mgr
    globals()['search_manager'] = search_mgr
    globals()['job_manager'] = job_mgr
    globals()['analytics_manager'] = analytics_mgr


# =============================================================================
# Endpoint 1: POST /api/v1/knowledge/search (Line 305 from reference)
# =============================================================================

@router.post("/search")
async def search_documents(
    request: UnifiedSearchRequest,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Search knowledge base documents.

    Supports semantic, keyword, and hybrid search modes.
    """
    logger.info(f"Search request: query='{request.query}', mode={request.search_mode}")

    try:
        start_time = time.time()

        # Validate query length
        if len(request.query.strip()) > 1000:
            logger.warning("Search query too long")
            raise HTTPException(status_code=422, detail="Query cannot exceed 1000 characters")

        query = request.query.strip()

        if request.search_mode == "semantic":
            # Use semantic search via search_manager
            if search_manager is None:
                logger.warning("Search manager not initialized - returning empty results")
                search_results = []
            else:
                results = await search_manager.search(
                    query=query,
                    user_id=user_id,
                    limit=request.limit,
                    document_type=request.document_type,
                    tags=request.tags
                )
                search_results = [SearchResultItem(**r) for r in results]

        elif request.search_mode == "keyword":
            # Use keyword search via document_manager
            if doc_manager is None:
                logger.warning("Document manager not initialized - returning empty results")
                search_results = []
            else:
                all_docs, total = await doc_manager.list_documents(
                    user_id=user_id,
                    limit=1000,
                    offset=0,
                    document_type=request.document_type
                )

                # Filter by query text
                query_lower = query.lower()
                filtered = [
                    doc for doc in all_docs
                    if query_lower in doc.title.lower() or
                       (doc.content and query_lower in doc.content.lower())
                ]

                # Apply tag filtering if specified
                if request.tags:
                    filtered = [
                        doc for doc in filtered
                        if any(tag in doc.tags for tag in request.tags)
                    ]

                # Paginate results
                paginated = filtered[request.offset:request.offset + request.limit]

                search_results = [
                    SearchResultItem(
                        document_id=doc.document_id,
                        title=doc.title,
                        document_type=doc.document_type or "unknown",
                        tags=doc.tags or [],
                        score=1.0,
                        snippet=doc.content[:200] if doc.content else ""
                    )
                    for doc in paginated
                ]

        elif request.search_mode == "hybrid":
            # Hybrid mode - combine both approaches (simplified for now)
            logger.warning("Hybrid search mode not fully implemented, falling back to semantic")
            results = await search_manager.search(
                query=query,
                user_id=user_id,
                limit=request.limit,
                document_type=request.document_type,
                tags=request.tags
            )
            search_results = [SearchResultItem(**r) for r in results]

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search_mode: {request.search_mode}. Use 'semantic', 'keyword', or 'hybrid'"
            )

        execution_time_ms = (time.time() - start_time) * 1000

        # Track analytics
        analytics_manager.track_search(
            query=query,
            result_count=len(search_results),
            execution_time_ms=execution_time_ms,
            user_id=user_id,
            search_mode=request.search_mode
        )

        return {
            "query": query,
            "search_mode": request.search_mode,
            "results": [r.dict() for r in search_results],
            "total_found": len(search_results),
            "returned": len(search_results),
            "execution_time_ms": round(execution_time_ms, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


# =============================================================================
# Endpoint 2: GET /api/v1/knowledge/jobs/{job_id} (Line 274 from reference)
# =============================================================================

@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Get the status of a knowledge base ingestion job.

    Returns job status, progress, and results for async operations.
    """
    logger.info(f"Getting job status for job_id={job_id}")

    try:
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return job.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


# =============================================================================
# Endpoint 3: POST /api/v1/knowledge/documents/bulk-delete (Line 443 from reference)
# =============================================================================

@router.post("/documents/bulk-delete")
async def bulk_delete_documents(
    request: Dict[str, List[str]],
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Bulk delete documents.

    Deletes multiple documents in a single operation.
    """
    logger.info(f"Bulk delete request from user {user_id}")

    try:
        document_ids = request.get("document_ids", [])

        if not document_ids:
            raise HTTPException(status_code=400, detail="Document IDs are required")

        # Create a job for tracking
        job_id = job_manager.create_job("bulk_delete")
        job_manager.update_job(job_id, "processing", progress=0.0)

        deleted_count = 0
        failed_ids = []

        total = len(document_ids)
        for idx, doc_id in enumerate(document_ids):
            try:
                success = await doc_manager.delete_document(doc_id, user_id)
                if success:
                    deleted_count += 1
                else:
                    failed_ids.append(doc_id)
            except Exception as e:
                logger.error(f"Failed to delete document {doc_id}: {e}")
                failed_ids.append(doc_id)

            # Update progress
            progress = ((idx + 1) / total) * 100
            job_manager.update_job(job_id, "processing", progress=progress)

        result = {
            "deleted_count": deleted_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids,
            "job_id": job_id
        }

        # Mark job as completed
        job_manager.update_job(job_id, "completed", progress=100.0, result=result)

        logger.info(f"Bulk deleted {deleted_count} documents")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk delete failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Bulk delete failed: {str(e)}"
        )


# =============================================================================
# Endpoint 4: GET /api/v1/knowledge/stats (Line 473 from reference)
# =============================================================================

@router.get("/stats")
async def get_knowledge_stats(
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Get knowledge base statistics.

    Returns document counts, sizes, and metadata.
    """
    logger.info(f"Getting knowledge stats for user {user_id}")

    try:
        # Get all documents for the user
        all_docs, total = await doc_manager.list_documents(
            user_id=user_id,
            limit=10000,
            offset=0
        )

        stats = {
            "total_documents": total,
            "by_type": {},
            "total_size_bytes": 0,
            "total_users": 1,
            "last_updated": None
        }

        # Calculate statistics
        for doc in all_docs:
            doc_type = doc.document_type or "unknown"
            stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1

            # Calculate size (rough estimate based on content length)
            if doc.content:
                stats["total_size_bytes"] += len(doc.content.encode('utf-8'))

            # Track last updated
            if doc.updated_at:
                doc_updated = doc.updated_at.isoformat()
                if stats["last_updated"] is None or doc_updated > stats["last_updated"]:
                    stats["last_updated"] = doc_updated

        logger.info("Retrieved knowledge base statistics")
        return stats

    except Exception as e:
        logger.error(f"Failed to get knowledge stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


# =============================================================================
# Endpoint 5: GET /api/v1/knowledge/analytics/search (Line 493 from reference)
# =============================================================================

@router.get("/analytics/search")
async def get_search_analytics(
    user_id: str = Depends(get_user_id)
) -> Dict[str, Any]:
    """
    Get search analytics and insights.

    Returns information about search patterns, popular queries, and trends.
    """
    logger.info(f"Getting search analytics for user {user_id}")

    try:
        analytics = analytics_manager.get_analytics()

        logger.info("Retrieved search analytics")
        return analytics

    except Exception as e:
        logger.error(f"Failed to get search analytics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics: {str(e)}"
        )
