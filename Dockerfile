# FaultMaven Knowledge Service - PUBLIC Open Source Version
# Apache 2.0 License

FROM python:3.11-slim

# Build argument for PyTorch device type (cpu or gpu)
# Default: cpu (reduces image from 8.5GB to ~2GB)
# For GPU support: docker build --build-arg DEVICE_TYPE=gpu
ARG DEVICE_TYPE=cpu

WORKDIR /app

# Install system dependencies for ChromaDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy fm-core-lib first (required dependency)
COPY fm-core-lib/ ./fm-core-lib/
RUN pip install --no-cache-dir ./fm-core-lib

# Copy pyproject.toml, source code, and migrations
COPY fm-knowledge-service/pyproject.toml ./
COPY fm-knowledge-service/src/ ./src/
COPY fm-knowledge-service/alembic/ ./alembic/
COPY fm-knowledge-service/alembic.ini ./

# CRITICAL: Install PyTorch FIRST to prevent sentence-transformers from pulling GPU version
# The DEVICE_TYPE build arg controls CPU vs GPU (default: cpu)
#
# Why this works:
# 1. sentence-transformers declares torch as a dependency
# 2. If we install sentence-transformers first, pip pulls the GPU torch (~4.3GB CUDA bloat)
# 3. By installing torch first with --index-url, pip respects the existing install
# 4. Result: Image shrinks from 8.5GB to ~2GB
RUN if [ "$DEVICE_TYPE" = "cpu" ]; then \
      pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu; \
    else \
      pip install --no-cache-dir torch torchvision; \
    fi

# Install dependencies - pip will use pre-installed torch and NOT upgrade it
RUN pip install --no-cache-dir -e .

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
