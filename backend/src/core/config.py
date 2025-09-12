"""
Configuration management for OceanQuery backend.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = Field(default="OceanQuery API", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    workers: int = Field(default=1, alias="WORKERS")
    reload: bool = Field(default=False, alias="RELOAD")

    # CORS
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:8080",
            "http://localhost:5173",
            "https://oceanquery.app",
        ],
        alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        alias="CORS_ALLOW_METHODS",
    )
    cors_allow_headers: List[str] = Field(
        default=["*"], alias="CORS_ALLOW_HEADERS"
    )

    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/oceanquery",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    # AI/ML Services
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", alias="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=1000, alias="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, alias="OPENAI_TEMPERATURE")

    # Vector Database
    chroma_persist_directory: str = Field(
        default="./chroma_db", alias="CHROMA_PERSIST_DIRECTORY"
    )
    chroma_collection_name: str = Field(
        default="argo_metadata", alias="CHROMA_COLLECTION_NAME"
    )
    
    faiss_index_path: str = Field(
        default="./faiss_index", alias="FAISS_INDEX_PATH"
    )
    embedding_model: str = Field(
        default="text-embedding-ada-002", alias="EMBEDDING_MODEL"
    )
    
    # RAG System Settings
    rag_max_context_tokens: int = Field(default=4000, alias="RAG_MAX_CONTEXT_TOKENS")
    rag_relevance_threshold: float = Field(default=0.75, alias="RAG_RELEVANCE_THRESHOLD")
    rag_max_chunks: int = Field(default=8, alias="RAG_MAX_CHUNKS")
    auto_load_knowledge: bool = Field(default=True, alias="AUTO_LOAD_KNOWLEDGE")

    # Firebase Authentication
    firebase_project_id: Optional[str] = Field(default=None, alias="FIREBASE_PROJECT_ID")
    firebase_service_account_key: Optional[str] = Field(
        default=None, alias="FIREBASE_SERVICE_ACCOUNT_KEY"
    )
    firebase_web_api_key: Optional[str] = Field(default=None, alias="FIREBASE_WEB_API_KEY")

    # Data Processing
    max_file_size_mb: int = Field(default=100, alias="MAX_FILE_SIZE_MB")
    max_concurrent_ingests: int = Field(default=3, alias="MAX_CONCURRENT_INGESTS")
    data_cache_ttl_seconds: int = Field(default=3600, alias="DATA_CACHE_TTL_SECONDS")

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(
        default=60, alias="RATE_LIMIT_REQUESTS_PER_MINUTE"
    )
    rate_limit_burst: int = Field(default=100, alias="RATE_LIMIT_BURST")

    # Monitoring
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_endpoint: str = Field(default="/metrics", alias="METRICS_ENDPOINT")
    health_check_endpoint: str = Field(default="/health", alias="HEALTH_CHECK_ENDPOINT")

    # Development/Testing
    mock_external_apis: bool = Field(default=False, alias="MOCK_EXTERNAL_APIS")
    enable_test_endpoints: bool = Field(default=False, alias="ENABLE_TEST_ENDPOINTS")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or self.log_level.upper() == "DEBUG"

    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL."""
        return self.database_url.replace("postgresql://", "postgresql://")

    @property
    def database_url_async(self) -> str:
        """Get asynchronous database URL."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")

    def get_cors_origins(self) -> List[str]:
        """Get CORS origins, parsing from string if needed."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins

    def get_firebase_service_account_path(self) -> Optional[str]:
        """Get Firebase service account JSON file path."""
        if self.firebase_service_account_key:
            # If it's a file path, return as-is
            if os.path.exists(self.firebase_service_account_key):
                return self.firebase_service_account_key
            
            # If it's a JSON string, write to temp file and return path
            import tempfile
            import json
            
            try:
                service_account_dict = json.loads(self.firebase_service_account_key)
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.json', delete=False
                )
                json.dump(service_account_dict, temp_file, indent=2)
                temp_file.close()
                return temp_file.name
            except json.JSONDecodeError:
                return None
                
        return None


@lru_cache
def get_settings() -> Settings:
    """Get application settings (cached)."""
    return Settings()


# Global settings instance
settings = get_settings()
