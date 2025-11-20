# FaultMaven Knowledge Service - PUBLIC Open Source Version
# Apache 2.0 License

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for ChromaDB and git (for fm-core-lib dependency)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and source code
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Create data directories for ChromaDB and SQLite
RUN mkdir -p /data/chromadb /data/sqlite && chmod -R 777 /data

# Set PYTHONPATH to include src directory
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8004/health', timeout=2)"

# Run service
CMD ["python", "-m", "uvicorn", "knowledge_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
