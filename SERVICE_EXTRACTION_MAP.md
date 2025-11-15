# Knowledge Service Extraction Map

## Source Files (from FaultMaven monolith)

| Monolith File | Destination | Action |
|---------------|-------------|--------|
| faultmaven/services/domain/knowledge_service.py | src/knowledge_service/domain/services/knowledge_service.py | Extract KB operations |
| faultmaven/core/knowledge/ingestion.py | src/knowledge_service/domain/services/ingestion.py | Extract document ingestion |
| faultmaven/core/knowledge/advanced_retrieval.py | src/knowledge_service/domain/services/retrieval.py | Extract hybrid RAG |
| faultmaven/api/v1/routes/knowledge.py | src/knowledge_service/api/routes/knowledge.py | Extract API endpoints |
| faultmaven/api/v1/routes/user_kb.py | src/knowledge_service/api/routes/user_kb.py | Extract user KB endpoints |
| faultmaven/infrastructure/persistence/chromadb*.py | src/knowledge_service/infrastructure/persistence/ | Extract vector storage |
| faultmaven/tools/knowledge_base.py | src/knowledge_service/domain/tools/ | Extract KB tools |

## Database Tables (exclusive ownership)

| Table Name | Source Schema | Action |
|------------|---------------|--------|
| kb_documents | 001_initial_hybrid_schema.sql | MIGRATE to fm_knowledge database |
| kb_document_shares | 001_initial_hybrid_schema.sql | MIGRATE to fm_knowledge database |

## ChromaDB Collections

| Collection Name | Purpose |
|-----------------|---------|
| global_kb | Global knowledge base (shared runbooks) |
| user_kb_{user_id} | User-specific knowledge base |
| case_evidence_{case_id} | Case-specific evidence embeddings |

## Events Published

| Event Name | AsyncAPI Schema | Trigger |
|------------|-----------------|---------|
| knowledge.document.ingested.v1 | contracts/asyncapi/knowledge-events.yaml | POST /v1/knowledge/documents |
| knowledge.document.updated.v1 | contracts/asyncapi/knowledge-events.yaml | PUT /v1/knowledge/documents/{id} |
| knowledge.document.deleted.v1 | contracts/asyncapi/knowledge-events.yaml | DELETE /v1/knowledge/documents/{id} |
| knowledge.search.completed.v1 | contracts/asyncapi/knowledge-events.yaml | POST /v1/knowledge/search |

## Events Consumed

| Event Name | Source Service | Action |
|------------|----------------|--------|
| auth.user.deleted.v1 | Auth Service | Delete user's KB documents |
| case.deleted.v1 | Case Service | Delete case evidence collection |

## API Dependencies

| Dependency | Purpose | Fallback Strategy |
|------------|---------|-------------------|
| Auth Service | Validate user tokens | Circuit breaker (deny if down) |
| Case Service | Verify case ownership | Circuit breaker (return 403) |

## Migration Checklist

- [ ] Extract domain models (KBDocument, DocumentMetadata)
- [ ] Extract business logic (ingestion pipeline, hybrid RAG retrieval)
- [ ] Extract API routes (document upload, search, management)
- [ ] Extract repository (PostgreSQL metadata + ChromaDB vectors)
- [ ] Create database migration scripts (001_initial_schema.sql)
- [ ] Implement event publishing (outbox pattern)
- [ ] Implement event consumption (inbox pattern)
- [ ] Add circuit breakers for dependencies
- [ ] Write unit tests (80%+ coverage)
- [ ] Write integration tests (DB + ChromaDB)
- [ ] Write contract tests (provider verification)
