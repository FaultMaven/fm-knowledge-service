#!/usr/bin/env python3
"""Auto-generate README.md from OpenAPI specification.

This script reads the OpenAPI spec generated from FastAPI and creates
a comprehensive README with endpoint documentation, examples, and statistics.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any


def load_openapi_spec() -> Dict[str, Any]:
    """Load OpenAPI spec from docs/api/openapi.json"""
    spec_path = Path(__file__).parent.parent / "docs" / "api" / "openapi.json"

    if not spec_path.exists():
        raise FileNotFoundError(
            f"OpenAPI spec not found at {spec_path}. "
            "Run the app to generate it first."
        )

    with open(spec_path, 'r') as f:
        return json.load(f)


def generate_endpoint_table(spec: Dict[str, Any]) -> str:
    """Generate markdown table of endpoints"""
    endpoints = []

    for path, methods in spec.get('paths', {}).items():
        for method, details in methods.items():
            if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                # Extract summary or use path as fallback
                summary = details.get('summary', path)

                endpoints.append({
                    'method': method.upper(),
                    'path': path,
                    'summary': summary
                })

    # Sort endpoints: health first, then by path
    def sort_key(e):
        if e['path'] == '/health':
            return (0, '')
        return (1, e['path'])

    endpoints.sort(key=sort_key)

    # Build markdown table
    table = "| Method | Endpoint | Description |\n"
    table += "|--------|----------|-------------|\n"

    for endpoint in endpoints:
        table += f"| {endpoint['method']} | `{endpoint['path']}` | {endpoint['summary']} |\n"

    return table


def extract_response_codes(spec: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Extract unique response codes and their descriptions across all endpoints"""
    response_info = {}

    for path, methods in spec.get('paths', {}).items():
        for method, details in methods.items():
            if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                for code, response_details in details.get('responses', {}).items():
                    desc = response_details.get('description', 'No description')
                    if code not in response_info:
                        response_info[code] = set()
                    response_info[code].add(desc)

    return response_info


def generate_response_codes_section(spec: Dict[str, Any]) -> str:
    """Generate response codes documentation"""
    response_info = extract_response_codes(spec)

    if not response_info:
        return ""

    section = "\n## Common Response Codes\n\n"

    # Sort codes numerically
    for code in sorted(response_info.keys(), key=lambda x: int(x)):
        descriptions = list(response_info[code])
        section += f"- **{code}**: {descriptions[0]}\n"

    return section


def count_endpoints(spec: Dict[str, Any]) -> int:
    """Count total number of endpoints"""
    count = 0
    for path, methods in spec.get('paths', {}).items():
        for method in methods.keys():
            if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
                count += 1
    return count


def main():
    """Generate README.md from OpenAPI specification"""
    print("🚀 Generating README.md from OpenAPI specification...")

    # Load spec
    spec = load_openapi_spec()

    # Extract metadata
    info = spec.get('info', {})
    title = info.get('title', 'fm-knowledge-service')
    version = info.get('version', '1.0.0')
    description = info.get('description', 'Microservice for knowledge base management with RAG')

    # Generate sections
    endpoint_table = generate_endpoint_table(spec)
    response_codes = generate_response_codes_section(spec)
    total_endpoints = count_endpoints(spec)
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

    # Build README content
    readme_content = f"""# {title}

> **🤖 This README is auto-generated** from code on every commit.
> Last updated: **{timestamp}** | Total endpoints: **{total_endpoints}**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/r/faultmaven/fm-knowledge-service)
[![Auto-Docs](https://img.shields.io/badge/docs-auto--generated-success.svg)](.github/workflows/generate-docs.yml)

## Overview

**{description}** - Part of the FaultMaven troubleshooting platform.

The Knowledge Service provides semantic search and RAG (Retrieval-Augmented Generation) capabilities for troubleshooting documentation. It stores and indexes documents using ChromaDB vector database, enabling intelligent retrieval of relevant knowledge during investigations.

**Key Features:**
- **Document Management**: Create, read, update, and delete knowledge documents
- **Semantic Search**: Find relevant documents using vector similarity search
- **Vector Storage**: ChromaDB integration for efficient embedding storage and retrieval
- **RAG Support**: Provides context for AI-powered troubleshooting assistance
- **User Isolation**: Each user only sees their own documents (enforced via X-User-ID header)
- **Document Types**: Support for various document types (runbook, kb_article, diagnostic, solution, etc.)
- **Metadata & Tags**: Rich metadata and tagging for better organization
- **Bulk Operations**: Batch updates and deletions for efficient management
- **Analytics**: Search analytics and knowledge base statistics

## Quick Start

### Using Docker (Recommended)

```bash
docker run -p 8002:8002 \\
  -v ./data:/data \\
  -v ./chromadb:/chromadb \\
  faultmaven/fm-knowledge-service:latest
```

The service will be available at `http://localhost:8002`. Data persists in the `./data` and `./chromadb` directories.

### Using Docker Compose

See [faultmaven-deploy](https://github.com/FaultMaven/faultmaven-deploy) for complete deployment with all FaultMaven services.

### Development Setup

```bash
# Clone repository
git clone https://github.com/FaultMaven/fm-knowledge-service.git
cd fm-knowledge-service

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install dependencies
pip install -e .

# Run service
uvicorn knowledge_service.main:app --reload --port 8002
```

The service creates a SQLite database at `./fm_knowledge.db` and ChromaDB storage at `./chromadb` on first run.

## API Endpoints

{endpoint_table}

**OpenAPI Documentation**: See [docs/api/openapi.json](docs/api/openapi.json) or [docs/api/openapi.yaml](docs/api/openapi.yaml) for complete API specification.
{response_codes}

## Configuration

Configuration via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_NAME` | Service identifier | `fm-knowledge-service` |
| `ENVIRONMENT` | Deployment environment | `development` |
| `HOST` | Service host | `0.0.0.0` |
| `PORT` | Service port | `8002` |
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./fm_knowledge.db` |
| `CHROMA_HOST` | ChromaDB host | `localhost` |
| `CHROMA_PORT` | ChromaDB port | `8000` |
| `CHROMA_COLLECTION_NAME` | Vector collection name | `knowledge_base` |
| `EMBEDDING_MODEL` | Sentence transformer model | `all-MiniLM-L6-v2` |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` |

Example `.env` file:

```env
ENVIRONMENT=production
PORT=8002
DATABASE_URL=sqlite+aiosqlite:///./data/fm_knowledge.db
CHROMA_HOST=chromadb
CHROMA_PORT=8000
LOG_LEVEL=INFO
```

## Document Data Model

Example Document Object:

```json
{{
    "document_id": "doc_abc123def456",
    "user_id": "user_123",
    "title": "PostgreSQL Connection Pooling Best Practices",
    "content": "When configuring PostgreSQL connection pools...",
    "document_type": "kb_article",
    "metadata": {{"category": "database", "difficulty": "intermediate"}},
    "tags": ["postgresql", "connection-pooling", "performance"],
    "source_url": "https://docs.example.com/postgres-pooling",
    "created_at": "2025-11-15T10:30:00Z",
    "updated_at": "2025-11-15T12:45:00Z"
}}
```

### Document Types
- `runbook` - Step-by-step operational procedures
- `kb_article` - Knowledge base articles
- `diagnostic` - Diagnostic guides and flowcharts
- `solution` - Documented solutions to known issues
- `reference` - Reference documentation
- `other` - Uncategorized documents

## Authorization

This service uses **trusted header authentication** from the FaultMaven API Gateway:

**Required Headers:**

- `X-User-ID` (required): Identifies the user making the request

**Optional Headers:**

- `X-User-Email`: User's email address
- `X-User-Roles`: User's roles (comma-separated)

All document operations are scoped to the user specified in `X-User-ID`. Users can only access their own documents.

**Security Model:**

- ✅ User isolation enforced at database query level
- ✅ All endpoints validate X-User-ID header presence
- ✅ Cross-user access attempts return 404 (not 403) to prevent enumeration
- ⚠️ Service trusts headers set by upstream gateway

**Important**: This service should run behind the [fm-api-gateway](https://github.com/FaultMaven/faultmaven) which handles authentication and sets these headers. Never expose this service directly to the internet.

## Architecture

```
┌─────────────────────────┐
│  FaultMaven API Gateway │  Handles authentication (Clerk)
│  (Port 8000)            │  Sets X-User-ID header
└───────────┬─────────────┘
            │ Trusted headers (X-User-ID)
            ↓
┌─────────────────────────┐
│  fm-knowledge-service   │  Trusts gateway headers
│  (Port 8002)            │  Enforces user isolation
└───────────┬─────────────┘
            │ SQLAlchemy ORM + Embedding API
            ↓
┌─────────────────────────┐
│  SQLite Database        │  fm_knowledge.db
│  (Local file)           │  Document metadata
└─────────────────────────┘
            ↓
┌─────────────────────────┐
│  ChromaDB               │  Vector embeddings
│  (Port 8000)            │  Semantic search index
└─────────────────────────┘
```

**Related Services:**
- fm-session-service (8001) - Investigation sessions
- fm-case-service (8003) - Case management
- fm-evidence-service (8004) - Evidence artifacts

**Storage Details:**

- **Metadata Database**: SQLite with aiosqlite async driver
- **Location**: `./fm_knowledge.db` (configurable via DATABASE_URL)
- **Vector Database**: ChromaDB for embeddings and semantic search
- **Embeddings**: Sentence transformers (all-MiniLM-L6-v2, 384 dimensions)
- **Schema**: Auto-created on startup via SQLAlchemy
- **Indexes**: Optimized for user_id and document_type lookups
- **Migrations**: Not required (schema auto-managed)

## Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage report
pytest --cov=knowledge_service --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_documents.py -v

# Run with debug output
pytest -vv -s
```

**Test Coverage Goals:**

- Unit tests: Core business logic (DocumentManager, SearchManager)
- Integration tests: Database and vector DB operations
- API tests: Endpoint behavior and validation
- Target coverage: >80%

## Development Workflow

```bash
# Format code with black
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type check with mypy
mypy src/

# Run all quality checks
black src/ tests/ && flake8 src/ tests/ && mypy src/ && pytest
```

## Related Projects

- [faultmaven](https://github.com/FaultMaven/faultmaven) - Main backend with API Gateway and orchestration
- [faultmaven-copilot](https://github.com/FaultMaven/faultmaven-copilot) - Browser extension UI for troubleshooting
- [faultmaven-deploy](https://github.com/FaultMaven/faultmaven-deploy) - Docker Compose deployment configurations
- [fm-session-service](https://github.com/FaultMaven/fm-session-service) - Investigation session management
- [fm-case-service](https://github.com/FaultMaven/fm-case-service) - Case management
- [fm-evidence-service](https://github.com/FaultMaven/fm-evidence-service) - Evidence artifact storage

## CI/CD

This repository uses **GitHub Actions** for automated documentation generation:

**Trigger**: Every push to `main` or `develop` branches

**Process**:
1. Generate OpenAPI spec (JSON + YAML)
2. Validate documentation completeness (fails if endpoints lack descriptions)
3. Auto-generate this README from code
4. Commit changes back to repository (if on main)

See [.github/workflows/generate-docs.yml](.github/workflows/generate-docs.yml) for implementation details.

**Documentation Guarantee**: This README is always in sync with the actual code. Any endpoint changes automatically trigger documentation updates.

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and quality checks (`pytest && black . && flake8`)
5. Commit with clear messages (`git commit -m 'feat: Add amazing feature'`)
6. Push to your fork (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Code Style**: Black formatting, flake8 linting, mypy type checking
**Commit Convention**: Conventional Commits (feat/fix/docs/refactor/test/chore)

---

**📊 Documentation Statistics**
- Total endpoints: {total_endpoints}
- Last generated: {timestamp}
- OpenAPI spec version: {version}
- Generator: scripts/generate_readme.py
- CI/CD: GitHub Actions

*This README is automatically updated on every commit to ensure zero documentation drift.*
"""

    # Write README
    readme_path = Path(__file__).parent.parent / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print(f"✅ README.md generated successfully")
    print(f"   Location: {readme_path}")
    print(f"   Total endpoints documented: {total_endpoints}")
    print(f"   Timestamp: {timestamp}")


if __name__ == "__main__":
    main()
