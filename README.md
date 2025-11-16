# FM Knowledge Service

Microservice for knowledge base management with Retrieval Augmented Generation (RAG).

## Features

- Document CRUD operations with user authorization
- Semantic search using sentence-transformers embeddings
- Vector similarity search with ChromaDB
- SQLite metadata storage (async with SQLAlchemy 2.0)
- Find similar documents functionality
- Per-user document isolation

## Architecture

```
fm-knowledge-service/
├── src/knowledge_service/
│   ├── api/routes/          # FastAPI endpoints
│   ├── core/                # Business logic
│   ├── infrastructure/      # External integrations
│   │   ├── database/        # SQLite metadata
│   │   └── vectordb/        # ChromaDB + embeddings
│   ├── models/              # Data models
│   └── config/              # Settings
├── chroma_data/             # ChromaDB storage
├── tests/                   # Test suite
└── pyproject.toml          # Dependencies
```

## Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# For development
pip install -e ".[dev]"
```

## Running

```bash
# Start service
python -m knowledge_service.main

# Or with uvicorn
uvicorn knowledge_service.main:app --reload --port 8006
```

## API Endpoints

### Documents
- `POST /api/v1/documents` - Create document
- `GET /api/v1/documents/{document_id}` - Get document
- `PUT /api/v1/documents/{document_id}` - Update document
- `DELETE /api/v1/documents/{document_id}` - Delete document
- `GET /api/v1/documents` - List documents (with pagination)

### Search
- `POST /api/v1/search` - Semantic search
- `GET /api/v1/search/similar/{document_id}` - Find similar documents

### Health
- `GET /health` - Health check

## Configuration

See `.env.example` for all configuration options.

Key settings:
- `PORT`: Service port (default: 8006)
- `DATABASE_URL`: SQLite database URL
- `CHROMA_PERSIST_DIR`: ChromaDB storage directory
- `EMBEDDING_MODEL`: Sentence transformer model (default: all-MiniLM-L6-v2)

## Authentication

This service trusts X-User-* headers from the API gateway (no JWT validation needed).

Required headers:
- `X-User-ID`: User identifier
- `X-User-Email`: User email
- `X-User-Roles`: User roles

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=knowledge_service --cov-report=html
```

## Dependencies

- FastAPI - Web framework
- Uvicorn - ASGI server
- SQLAlchemy 2.0 - ORM (async)
- aiosqlite - Async SQLite driver
- ChromaDB - Vector database
- sentence-transformers - Embedding generation
- Pydantic - Data validation
