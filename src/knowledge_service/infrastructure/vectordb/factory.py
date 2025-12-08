"""Vector Database Provider Factory

Factory pattern for deployment-neutral vector database selection.
Chooses between local ChromaDB and managed cloud providers based on configuration.
"""

import logging
import os
from typing import Optional

from .provider import VectorDBProvider
from .chroma_local import ChromaLocalProvider
from .pinecone_provider import PineconeProvider, PINECONE_AVAILABLE

logger = logging.getLogger(__name__)

# Singleton instance to avoid recreating connections
_vector_provider_instance: Optional[VectorDBProvider] = None


def get_vector_provider() -> VectorDBProvider:
    """Get or create the global vector database provider instance.

    Uses VECTOR_DB_PROVIDER environment variable to determine provider type:
    - "chroma" (default): Local/persistent ChromaDB
    - "pinecone": Managed Pinecone cloud service

    Returns:
        VectorDBProvider instance (ChromaLocalProvider or PineconeProvider)

    Environment Variables:
        VECTOR_DB_PROVIDER: "chroma" or "pinecone" (default: "chroma")

        For ChromaDB:
            CHROMA_PERSIST_DIR: Persistent storage directory (default: "./data/chroma")
            CHROMA_COLLECTION_NAME: Collection name (default: "faultmaven_kb")

        For Pinecone:
            PINECONE_API_KEY: Pinecone API key (required)
            PINECONE_ENVIRONMENT: Cloud environment (default: "us-east-1-aws")
            PINECONE_INDEX_NAME: Index name (default: "faultmaven-kb")
            VECTOR_DIMENSION: Vector dimension (default: 384)

    Example:
        ```python
        # Self-hosted deployment (docker-compose)
        VECTOR_DB_PROVIDER=chroma
        CHROMA_PERSIST_DIR=/data/chroma

        # Enterprise K8s with Pinecone
        VECTOR_DB_PROVIDER=pinecone
        PINECONE_API_KEY=pk-...
        PINECONE_ENVIRONMENT=us-west1-gcp
        PINECONE_INDEX_NAME=faultmaven-prod
        ```

    Raises:
        ValueError: If provider type is invalid or required config is missing
        ImportError: If provider library is not installed
    """
    global _vector_provider_instance

    if _vector_provider_instance is not None:
        return _vector_provider_instance

    provider_type = os.getenv("VECTOR_DB_PROVIDER", "chroma").lower()

    logger.info(f"Initializing vector database provider: {provider_type}")

    if provider_type == "pinecone":
        # Pinecone managed cloud for enterprise scale
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError(
                "PINECONE_API_KEY environment variable is required "
                "when VECTOR_DB_PROVIDER=pinecone"
            )

        if not PINECONE_AVAILABLE:
            raise ImportError(
                "Pinecone library not installed. "
                "Install with: pip install pinecone-client"
            )

        environment = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
        index_name = os.getenv("PINECONE_INDEX_NAME", "faultmaven-kb")
        dimension = int(os.getenv("VECTOR_DIMENSION", "384"))

        _vector_provider_instance = PineconeProvider(
            api_key=api_key,
            environment=environment,
            index_name=index_name,
            dimension=dimension
        )

        logger.info(
            f"Pinecone provider initialized: "
            f"env={environment}, "
            f"index={index_name}, "
            f"dimension={dimension}"
        )

    elif provider_type == "chroma":
        # Local ChromaDB for development and self-hosted
        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "faultmaven_kb")

        _vector_provider_instance = ChromaLocalProvider(
            persist_directory=persist_dir,
            collection_name=collection_name
        )

        logger.info(
            f"ChromaDB local provider initialized: "
            f"persist_dir={persist_dir}, "
            f"collection={collection_name}"
        )

    else:
        raise ValueError(
            f"Invalid VECTOR_DB_PROVIDER: {provider_type}. "
            f"Must be 'chroma' or 'pinecone'"
        )

    return _vector_provider_instance


def reset_vector_provider():
    """Reset the global vector provider instance.

    Used for testing or reconfiguration. Should not be called in production code.
    """
    global _vector_provider_instance
    _vector_provider_instance = None
    logger.warning("Vector provider instance reset")
