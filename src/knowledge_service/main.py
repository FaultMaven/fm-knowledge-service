"""Main FastAPI application for Knowledge Service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import get_settings, Settings
from .infrastructure.database.client import DatabaseClient
from .infrastructure.vectordb import get_vector_provider, VectorDBProvider
from .infrastructure.vectordb.embeddings import EmbeddingGenerator
from .core.document_manager import DocumentManager
from .core.search_manager import SearchManager
from .core.job_manager import JobManager
from .core.analytics_manager import AnalyticsManager
from .api.routes import documents, search, knowledge_endpoints
from .models.requests import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
db_client: DatabaseClient = None
vector_client: VectorDBProvider = None
embedding_gen: EmbeddingGenerator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global db_client, vector_client, embedding_gen

    settings = get_settings()
    logger.info(f"Starting {settings.service_name} v1.0.0")

    # Initialize components
    logger.info("Initializing database...")
    db_client = DatabaseClient(settings.database_url)
    await db_client.initialize()

    logger.info("Initializing vector database provider...")
    # Use factory pattern for deployment-neutral vector DB
    vector_client = get_vector_provider()
    await vector_client.initialize()

    # Create default collection
    await vector_client.create_collection(
        name=settings.chroma_collection_name,
        dimension=384  # all-MiniLM-L6-v2 dimension
    )

    logger.info("Loading embedding model...")
    embedding_gen = EmbeddingGenerator(settings.embedding_model)

    logger.info(f"{settings.service_name} is ready")

    yield

    # Cleanup
    logger.info("Shutting down...")
    await db_client.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="FM Knowledge Service",
    description="Microservice for knowledge base management with RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(knowledge_endpoints.router)


# Set up managers after including routers
@app.on_event("startup")
async def setup_managers():
    """Set up managers after startup."""
    doc_mgr = DocumentManager(db_client, vector_client, embedding_gen)
    search_mgr = SearchManager(db_client, vector_client, embedding_gen)
    job_mgr = JobManager()
    analytics_mgr = AnalyticsManager()

    # Start background cleanup task for jobs
    await job_mgr.start_cleanup_task()

    # Set managers in route modules
    documents.set_managers(doc_mgr, search_mgr, job_mgr, analytics_mgr)
    search.set_search_manager(search_mgr)
    knowledge_endpoints.set_managers(doc_mgr, search_mgr, job_mgr, analytics_mgr)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    
    db_connected = db_client is not None
    chroma_connected = vector_client is not None and vector_client.get_collection_count() >= 0
    
    return HealthResponse(
        status="healthy" if (db_connected and chroma_connected) else "degraded",
        service=settings.service_name,
        version="1.0.0",
        chroma_connected=chroma_connected,
        database_connected=db_connected
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "fm-knowledge-service",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "knowledge_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
