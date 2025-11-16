# fm-knowledge-service

**FaultMaven Knowledge Management Microservice** - Open source RAG-powered knowledge base for troubleshooting documentation.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/r/faultmaven/fm-knowledge-service)

## Overview

The Knowledge Service implements a Retrieval-Augmented Generation (RAG) system for FaultMaven, allowing users to upload and search through troubleshooting documentation. Documents are chunked, embedded using BGE-M3 embeddings, and stored in ChromaDB for fast semantic search.

**Features:**
- **Document Upload**: Support for TXT, MD, PDF, DOC, DOCX, RTF formats
- **Automatic Chunking**: Intelligent text splitting with overlap
- **Semantic Search**: BGE-M3 embeddings with ChromaDB vector store
- **Metadata Tracking**: SQLite metadata database for documents
- **User Isolation**: Each user only accesses their own documents
- **Persistent Storage**: ChromaDB data persists to disk
- **Full-text + Vector**: Hybrid search capabilities

## Quick Start

### Using Docker (Recommended)

```bash
# Run with persistent storage
docker run -d -p 8004:8004 \
  -v ./data/chromadb:/data/chromadb \
  -v ./data/sqlite:/data/sqlite \
  faultmaven/fm-knowledge-service:latest
```

The service will be available at `http://localhost:8004`.

### Using Docker Compose

See [faultmaven-deploy](https://github.com/FaultMaven/faultmaven-deploy) for complete deployment with all FaultMaven services.

### Development Setup

```bash
# Clone repository
git clone https://github.com/FaultMaven/fm-knowledge-service.git
cd fm-knowledge-service

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Run service
uvicorn knowledge_service.main:app --reload --port 8004
```

## API Endpoints

### Document Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/documents/upload` | Upload document (multipart/form-data) |
| GET | `/api/v1/documents` | List user's documents |
| GET | `/api/v1/documents/{document_id}` | Get document metadata |
| DELETE | `/api/v1/documents/{document_id}` | Delete document |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/search` | Semantic search across documents |
| POST | `/api/v1/search/hybrid` | Hybrid full-text + vector search |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

## Configuration

Configuration via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `fm-knowledge-service` |
| `ENVIRONMENT` | Deployment environment | `development` |
| `PORT` | Service port | `8004` |
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:////data/sqlite/fm_knowledge.db` |
| `CHROMADB_PATH` | ChromaDB data directory | `/data/chromadb` |
| `EMBEDDING_MODEL` | Embeddings model name | `BAAI/bge-m3` |
| `CHUNK_SIZE` | Text chunk size | `1000` |
| `CHUNK_OVERLAP` | Chunk overlap size | `200` |
| `MAX_UPLOAD_SIZE_MB` | Maximum file size | `10` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Document Upload

Upload documents via multipart/form-data:

```bash
curl -X POST http://localhost:8004/api/v1/documents/upload \
  -H "X-User-ID: user_123" \
  -F "file=@troubleshooting_guide.pdf" \
  -F "title=Database Troubleshooting Guide" \
  -F "description=Common database issues and solutions" \
  -F "tags=database,performance,errors"
```

Response:
```json
{
    "document_id": "doc_abc123",
    "user_id": "user_123",
    "filename": "troubleshooting_guide.pdf",
    "title": "Database Troubleshooting Guide",
    "description": "Common database issues and solutions",
    "file_type": "pdf",
    "file_size": 245678,
    "chunk_count": 42,
    "tags": ["database", "performance", "errors"],
    "created_at": "2025-11-16T10:30:00Z"
}
```

## Semantic Search

Search documents using natural language queries:

```bash
curl -X POST http://localhost:8004/api/v1/search \
  -H "X-User-ID: user_123" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How to fix database connection timeouts?",
    "limit": 5,
    "min_relevance": 0.7
  }'
```

Response:
```json
{
    "results": [
        {
            "chunk_id": "chunk_001",
            "document_id": "doc_abc123",
            "document_title": "Database Troubleshooting Guide",
            "content": "Connection timeouts typically occur when...",
            "relevance_score": 0.92,
            "metadata": {
                "page": 15,
                "section": "Connection Issues"
            }
        }
    ],
    "query": "How to fix database connection timeouts?",
    "total_results": 5
}
```

## Supported File Types

| Extension | Format | Processing |
|-----------|--------|------------|
| `.txt` | Plain text | Direct chunking |
| `.md` | Markdown | Direct chunking |
| `.pdf` | PDF | PyPDF2 extraction |
| `.doc`, `.docx` | Word | python-docx extraction |
| `.rtf` | Rich Text | striprtf extraction |

## Data Model

### Document Metadata (SQLite)

```python
{
    "document_id": str,        # Unique identifier
    "user_id": str,            # Owner user ID
    "filename": str,           # Original filename
    "title": str,              # Document title
    "description": str,        # Optional description
    "file_type": str,          # File extension
    "file_size": int,          # Size in bytes
    "chunk_count": int,        # Number of chunks
    "tags": List[str],         # Searchable tags
    "created_at": datetime,    # Upload timestamp
    "updated_at": datetime     # Last modification
}
```

### Vector Embeddings (ChromaDB)

```python
{
    "chunk_id": str,           # Unique chunk identifier
    "document_id": str,        # Parent document
    "content": str,            # Chunk text
    "embedding": List[float],  # BGE-M3 vector (1024-dim)
    "metadata": {
        "user_id": str,
        "document_title": str,
        "chunk_index": int,
        "file_type": str,
        "tags": List[str]
    }
}
```

## Authorization

This service uses **trusted header authentication** from the FaultMaven API Gateway:

- `X-User-ID` (required): Identifies the user making the request
- `X-User-Email` (optional): User's email address
- `X-User-Roles` (optional): User's roles

All document operations are scoped to the user specified in `X-User-ID`. Users can only access their own documents.

**Important**: This service should run behind the [fm-api-gateway](https://github.com/FaultMaven/faultmaven) which handles authentication and sets these headers. Never expose this service directly to the internet.

## Architecture

```
┌─────────────────┐
│  API Gateway    │ (Handles authentication)
└────────┬────────┘
         │ X-User-ID header
         ↓
┌─────────────────┐
│ Knowledge Svc   │ (Document processing)
└────┬───────┬────┘
     │       │
     ↓       ↓
┌─────────┐ ┌──────────────┐
│ SQLite  │ │  ChromaDB    │
│Metadata │ │Vector Store  │
└─────────┘ └──────────────┘
```

## Document Processing Pipeline

1. **Upload**: User uploads document via API
2. **Validation**: Check file type and size
3. **Extraction**: Extract text from file format
4. **Chunking**: Split text into overlapping chunks
5. **Embedding**: Generate BGE-M3 embeddings
6. **Storage**: Store vectors in ChromaDB, metadata in SQLite
7. **Indexing**: Add to search index

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=knowledge_service

# Run specific test file
pytest tests/test_documents.py -v
```

## Related Projects

- [faultmaven](https://github.com/FaultMaven/faultmaven) - Main backend with API Gateway
- [faultmaven-copilot](https://github.com/FaultMaven/faultmaven-copilot) - Browser extension UI
- [faultmaven-deploy](https://github.com/FaultMaven/faultmaven-deploy) - Docker Compose deployment

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read our contributing guidelines and code of conduct.
