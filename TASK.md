# Task: Port 5 Missing Knowledge Endpoints

## Goal
Add 5 missing endpoints to achieve **100% OpenAPI compliance** (6/11 → 11/11)

## Branch
**Repository**: https://github.com/FaultMaven/fm-knowledge-service
**Branch**: `feature/port-knowledge-endpoints`

## What to Do

Copy these 5 endpoint implementations from `reference/monolith/knowledge.py`:

1. **Line 305**: `POST /api/v1/knowledge/search` → Add to `src/knowledge_service/api/routes/search.py`
2. **Line 443**: `POST /api/v1/knowledge/documents/bulk-delete` → Add to `src/knowledge_service/api/routes/documents.py`
3. **Line 473**: `GET /api/v1/knowledge/stats` → Add to `src/knowledge_service/api/routes/documents.py`
4. **Line 493**: `GET /api/v1/knowledge/analytics/search` → Create new `src/knowledge_service/api/routes/analytics.py`
5. **Line 274**: `GET /api/v1/knowledge/jobs/{job_id}` → Create new `src/knowledge_service/api/routes/jobs.py`

## Key Changes Needed

When copying code, update imports:
```python
# OLD (monolith)
from faultmaven.models import KnowledgeBaseDocument
from faultmaven.api.v1.dependencies import get_knowledge_service

# NEW (microservice)
from fm_core_lib.models import KnowledgeBaseDocument
from knowledge_service.api.dependencies import get_document_manager
```

## Verify Success

Run: `python3 verify_compliance.py`

Expected output:
```
IMPLEMENTED:           11
MISSING:               0
COVERAGE:              100.0%
```

## That's It

Just copy the 5 functions, update imports, and verify. The monolith code is proven and tested - minimal changes needed.
