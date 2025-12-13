# FaultMaven Knowledge Service - PUBLIC Open Source Version
# Apache 2.0 License

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Build argument for PyTorch device type (cpu or gpu)
ARG DEVICE_TYPE=cpu

WORKDIR /app

# Install system dependencies for ChromaDB and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Copy fm-core-lib first (required dependency)
COPY fm-core-lib/ ./fm-core-lib/

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# CRITICAL: Install PyTorch FIRST to prevent sentence-transformers from pulling GPU version
# This reduces image size from 8.5GB to ~2GB
RUN if [ "$DEVICE_TYPE" = "cpu" ]; then \
      pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    else \
      pip install --no-cache-dir torch torchvision; \
    fi

# Export dependencies to requirements.txt (no dev dependencies)
# Fallback to manual list if poetry export fails due to path dependencies
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --without dev || \
    echo "fastapi>=0.109.0\nuvicorn[standard]>=0.27.0\npydantic>=2.5.0\npydantic-settings>=2.1.0\npython-dotenv>=1.0.0\nsqlalchemy[asyncio]>=2.0.25\naiosqlite>=0.19.0\nalembic>=1.13.0\nasyncpg>=0.29.0\nhttpx>=0.28.1\nchromadb>=0.5.3\nsentence-transformers>=3.0.1\npypdf>=4.2.0\npython-docx>=1.1.2\npython-multipart>=0.0.6\ntenacity>=8.3.0" > requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Build argument for PyTorch device type
ARG DEVICE_TYPE=cpu

WORKDIR /app

# Install system dependencies for ChromaDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch (must match builder stage)
RUN if [ "$DEVICE_TYPE" = "cpu" ]; then \
      pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    else \
      pip install --no-cache-dir torch torchvision; \
    fi

# Copy requirements and install
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install fm-core-lib
COPY --from=builder /app/fm-core-lib/ ./fm-core-lib/
RUN pip install --no-cache-dir ./fm-core-lib

# Copy source code and migrations
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create data directories for ChromaDB and SQLite
RUN mkdir -p /data/chromadb /data/sqlite && chmod -R 777 /data

# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health', timeout=2)"

# Run migrations then start service
CMD ["sh", "-c", "alembic upgrade head && python -m uvicorn knowledge_service.main:app --host 0.0.0.0 --port 8000"]
