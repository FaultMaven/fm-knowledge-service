"""Vector database infrastructure.

Deployment-neutral vector database abstraction supporting:
- ChromaDB (local/persistent for development and self-hosted)
- Pinecone (managed cloud for enterprise scale)
"""

from .factory import get_vector_provider, reset_vector_provider
from .provider import VectorDBProvider, SearchResult
from .chroma_local import ChromaLocalProvider
from .pinecone_provider import PineconeProvider

__all__ = [
    "get_vector_provider",
    "reset_vector_provider",
    "VectorDBProvider",
    "SearchResult",
    "ChromaLocalProvider",
    "PineconeProvider",
]
