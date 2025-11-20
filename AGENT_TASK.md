# Agent Task: Port Missing Knowledge Endpoints

## Overview

Port **5 missing endpoints** from the proven monolith to fm-knowledge-service to achieve 100% OpenAPI compliance.

**Current Status**: 6/11 endpoints (54.5%)
**Target**: 11/11 endpoints (100%)
**Estimated Time**: 3-5 hours

## Branch

- **Repository**: https://github.com/FaultMaven/fm-knowledge-service
- **Branch**: `feature/port-knowledge-endpoints`
- **Target File**: `src/knowledge_service/api/routes/documents.py` (or create new route file if needed)

## Reference Materials

All source code and specifications are in the `reference/` directory:

1. **`reference/monolith/knowledge.py`** - Source of truth (proven, tested code from monolith)
2. **`reference/openapi.locked.yaml`** - Authoritative API specification

## Missing Endpoints (5)

| Method | Path | Monolith Line | Summary |
|--------|------|---------------|---------|
| POST | `/api/v1/knowledge/search` | 305 | Search Documents |
| POST | `/api/v1/knowledge/documents/bulk-delete` | 443 | Bulk Delete Documents |
| GET | `/api/v1/knowledge/stats` | 473 | Get Knowledge Stats |
| GET | `/api/v1/knowledge/analytics/search` | 493 | Get Search Analytics |
| GET | `/api/v1/knowledge/jobs/{job_id}` | 274 | Get Job Status |

## Porting Process

### Step 1: Identify Source Code

For each endpoint, locate the implementation in `reference/monolith/knowledge.py`:

```python
# Example: POST /api/v1/knowledge/search at line 305
@router.post("/search")
async def search_documents(...):
    # Implementation here
```

### Step 2: Adapt Code

Convert monolith patterns to microservice patterns:

```python
# MONOLITH PATTERN
from faultmaven.models import KnowledgeBaseDocument
from faultmaven.api.v1.dependencies import get_knowledge_service
from faultmaven.services.domain.knowledge_service import KnowledgeService

knowledge_service: KnowledgeService = Depends(get_knowledge_service)

# MICROSERVICE PATTERN
from fm_core_lib.models import KnowledgeBaseDocument
from knowledge_service.core import DocumentManager, SearchManager
from knowledge_service.api.dependencies import get_document_manager, get_search_manager

doc_manager: DocumentManager = Depends(get_document_manager)
search_manager: SearchManager = Depends(get_search_manager)
```

### Step 3: Add to Routes File

Choose the appropriate route file:
- Document operations → `src/knowledge_service/api/routes/documents.py`
- Search operations → `src/knowledge_service/api/routes/search.py`
- Or create new file if needed

### Step 4: Test Imports

Ensure all imports work:
```bash
cd /path/to/fm-knowledge-service
python3 -c "from knowledge_service.api.routes import documents"
```

### Step 5: Verify Compliance

Run verification script:
```bash
python3 verify_compliance.py
```

Expected output:
```
SPEC ENDPOINTS:        11
IMPLEMENTED:           11
MISSING:               0
COVERAGE:              100.0%
```

## Key Adaptation Rules

### 1. Import Paths

| Monolith | Microservice |
|----------|--------------|
| `from faultmaven.models import X` | `from fm_core_lib.models import X` |
| `from faultmaven.api.v1.dependencies import get_knowledge_service` | `from knowledge_service.api.dependencies import get_document_manager` |
| `from faultmaven.services.domain.knowledge_service import KnowledgeService` | `from knowledge_service.core import DocumentManager, SearchManager` |

### 2. Dependency Injection

**Monolith**:
```python
knowledge_service: KnowledgeService = Depends(get_knowledge_service)
result = await knowledge_service.search_documents(query)
```

**Microservice**:
```python
search_manager: SearchManager = Depends(get_search_manager)
result = await search_manager.search(query)
```

### 3. Authorization

**Monolith**:
```python
from faultmaven.api.v1.role_dependencies import require_admin
current_user: DevUser = Depends(require_admin)
```

**Microservice**:
```python
from knowledge_service.api.dependencies import get_user_id
user_id: str = Depends(get_user_id)  # From X-User-ID header
```

## Endpoint Details

### 1. POST /api/v1/knowledge/search

**Source**: Line 305 in monolith
**Target**: `src/knowledge_service/api/routes/search.py`
**Purpose**: Semantic search across knowledge base documents
**Key Changes**:
- Use `SearchManager.search()` instead of `KnowledgeService.search_documents()`
- Return results in same format as monolith

### 2. POST /api/v1/knowledge/documents/bulk-delete

**Source**: Line 443 in monolith
**Target**: `src/knowledge_service/api/routes/documents.py`
**Purpose**: Delete multiple documents in one request
**Note**: Current service has `batch-delete` (extra endpoint) - this is the spec-compliant version

### 3. GET /api/v1/knowledge/stats

**Source**: Line 473 in monolith
**Target**: `src/knowledge_service/api/routes/documents.py`
**Purpose**: Get knowledge base statistics
**Note**: Current service has `/documents/stats` - this should be at `/stats`

### 4. GET /api/v1/knowledge/analytics/search

**Source**: Line 493 in monolith
**Target**: Create new file `src/knowledge_service/api/routes/analytics.py` or add to existing
**Purpose**: Get search analytics and usage patterns

### 5. GET /api/v1/knowledge/jobs/{job_id}

**Source**: Line 274 in monolith
**Target**: Create new file `src/knowledge_service/api/routes/jobs.py` or add to documents
**Purpose**: Get status of background document processing jobs

## Verification Checklist

- [ ] All 5 endpoints added to appropriate route files
- [ ] Imports adapted to microservice structure
- [ ] Dependencies use DocumentManager/SearchManager instead of KnowledgeService
- [ ] Authorization uses X-User-ID header pattern
- [ ] `python3 verify_compliance.py` shows 11/11 (100%)
- [ ] No syntax errors: `python3 -c "from knowledge_service.api.routes import documents"`
- [ ] Code matches monolith business logic
- [ ] Response models match OpenAPI spec

## Success Criteria

✅ `python3 verify_compliance.py` output:
```
SPEC ENDPOINTS:        11
IMPLEMENTED:           11
MISSING:               0
COVERAGE:              100.0%
```

✅ All imports work without errors
✅ Code follows microservice patterns (not monolith patterns)
✅ Endpoints match monolith functionality

## Questions?

Review these files for patterns:
- `src/knowledge_service/api/routes/documents.py` - Existing endpoint examples
- `src/knowledge_service/core/document_manager.py` - Service layer
- `reference/monolith/knowledge.py` - Source code to port
