"""Settings module using pydantic-settings for configuration management."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    service_name: str = Field(default="fm-knowledge-service", env="SERVICE_NAME")
    environment: str = Field(default="development", env="ENVIRONMENT")
    port: int = Field(default=8006, env="PORT")
    host: str = Field(default="0.0.0.0", env="HOST")

    # Database Configuration (SQLite for metadata)
    database_url: str = Field(
        default="sqlite+aiosqlite:///./fm_knowledge.db",
        env="DATABASE_URL"
    )

    # ChromaDB Configuration
    chroma_persist_dir: str = Field(default="./chroma_data", env="CHROMA_PERSIST_DIR")
    chroma_collection_name: str = Field(
        default="faultmaven_kb",
        env="CHROMA_COLLECTION_NAME"
    )

    # Embedding Model Configuration
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",  # Lightweight for dev
        env="EMBEDDING_MODEL"
    )

    # Search Configuration
    default_search_limit: int = Field(default=10, env="DEFAULT_SEARCH_LIMIT")
    max_search_limit: int = Field(default=50, env="MAX_SEARCH_LIMIT")

    # Pagination Configuration
    default_page_size: int = Field(default=50, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
