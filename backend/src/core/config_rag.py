"""
RAG-specific configuration settings for OceanQuery.

Extends the main configuration with RAG system parameters.
"""

import os
from pathlib import Path
from typing import Optional


class RAGSettings:
    """RAG system configuration settings."""
    
    def __init__(self):
        # Vector database settings
        self.chroma_persist_directory = os.getenv(
            "CHROMA_PERSIST_DIRECTORY", 
            str(Path.cwd() / "data" / "vector_db")
        )
        
        # Embedding settings - Use Sentence Transformers (no OpenAI needed)
        self.use_openai_embeddings = False  # Force disable OpenAI
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Sentence Transformers model
        self.openai_api_key = None  # Explicitly disable
        
        # RAG pipeline settings
        self.rag_max_context_tokens = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "4000"))
        self.rag_relevance_threshold = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.6"))  # Lowered from 0.75 to 0.6
        self.rag_max_chunks = int(os.getenv("RAG_MAX_CHUNKS", "8"))
        
        # Knowledge management
        self.auto_load_knowledge = os.getenv("AUTO_LOAD_KNOWLEDGE", "true").lower() == "true"
        self.knowledge_update_interval = int(os.getenv("KNOWLEDGE_UPDATE_INTERVAL", "86400"))  # 24 hours
        
        # Performance settings
        self.vector_search_timeout = int(os.getenv("VECTOR_SEARCH_TIMEOUT", "30"))  # seconds
        self.embedding_batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
        
    def validate_settings(self) -> bool:
        """Validate RAG configuration settings."""
        
        # No OpenAI validation needed - using Sentence Transformers
        print("ℹ️  Using Sentence Transformers embeddings (offline mode)")
        
        if self.rag_max_context_tokens <= 0:
            raise ValueError("RAG_MAX_CONTEXT_TOKENS must be positive")
        
        if not (0.0 <= self.rag_relevance_threshold <= 1.0):
            raise ValueError("RAG_RELEVANCE_THRESHOLD must be between 0.0 and 1.0")
        
        if self.rag_max_chunks <= 0:
            raise ValueError("RAG_MAX_CHUNKS must be positive")
        
        return True
    
    def get_vector_db_path(self) -> Path:
        """Get the full path to vector database directory."""
        path = Path(self.chroma_persist_directory)
        path.mkdir(parents=True, exist_ok=True)
        return path


# Global RAG settings instance
rag_settings = RAGSettings()