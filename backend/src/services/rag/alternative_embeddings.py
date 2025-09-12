"""
Alternative embedding providers for the RAG system.

Provides fallback options when OpenAI embeddings are not available.
"""

import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

class HuggingFaceEmbeddingFunction:
    """
    Hugging Face embedding function as alternative to OpenAI.
    
    Uses sentence-transformers for generating embeddings locally.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize Hugging Face embedding function.
        
        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self.model = None
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        try:
            # Import sentence-transformers (install with: pip install sentence-transformers)
            from sentence_transformers import SentenceTransformer
            
            self.model = SentenceTransformer(model_name)
            self.logger.info(f"Loaded Hugging Face model: {model_name}")
            
        except ImportError:
            self.logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise ImportError("sentence-transformers package is required for local embeddings")
        except Exception as e:
            self.logger.error(f"Failed to load Hugging Face model {model_name}: {e}")
            raise
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        
        if not self.model:
            raise RuntimeError("Hugging Face model not initialized")
        
        try:
            # Generate embeddings
            embeddings = self.model.encode(texts, convert_to_tensor=False)
            
            # Convert to list of lists
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.tolist()
            
            self.logger.debug(f"Generated embeddings for {len(texts)} texts")
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            raise


class FallbackEmbeddingFunction:
    """
    Fallback embedding function that tries multiple providers.
    
    Attempts OpenAI first, then falls back to Hugging Face.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, hf_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize fallback embedding function.
        
        Args:
            openai_api_key: OpenAI API key (optional)
            hf_model: Hugging Face model name for fallback
        """
        self.openai_api_key = openai_api_key
        self.hf_model_name = hf_model
        self.primary_function = None
        self.fallback_function = None
        self.current_provider = None
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Try to initialize OpenAI first
        if openai_api_key:
            try:
                from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
                self.primary_function = OpenAIEmbeddingFunction(
                    api_key=openai_api_key,
                    model_name="text-embedding-ada-002"
                )
                self.current_provider = "openai"
                self.logger.info("Initialized OpenAI embedding function as primary")
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI embeddings: {e}")
        
        # Initialize Hugging Face fallback
        try:
            self.fallback_function = HuggingFaceEmbeddingFunction(hf_model)
            if not self.primary_function:
                self.current_provider = "huggingface"
            self.logger.info("Initialized Hugging Face embedding function as fallback")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Hugging Face embeddings: {e}")
        
        # Check if we have at least one working function
        if not self.primary_function and not self.fallback_function:
            raise RuntimeError("No embedding functions available")
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using available provider."""
        
        # Try primary function first (OpenAI)
        if self.primary_function and self.current_provider == "openai":
            try:
                result = self.primary_function(texts)
                return result
            except Exception as e:
                self.logger.warning(f"OpenAI embeddings failed: {e}")
                if self.fallback_function:
                    self.logger.info("Switching to Hugging Face embeddings")
                    self.current_provider = "huggingface"
                else:
                    raise
        
        # Use fallback function (Hugging Face)
        if self.fallback_function:
            try:
                return self.fallback_function(texts)
            except Exception as e:
                self.logger.error(f"Fallback embeddings failed: {e}")
                raise
        
        raise RuntimeError("No embedding functions available")
    
    def get_current_provider(self) -> str:
        """Get the name of the currently active embedding provider."""
        return self.current_provider or "none"


# Installation instructions for sentence-transformers
HUGGINGFACE_INSTALL_CMD = """
To use Hugging Face embeddings as fallback:

pip install sentence-transformers

This will enable local embedding generation without OpenAI API calls.
"""

def create_embedding_function(openai_api_key: Optional[str] = None, use_fallback: bool = True):
    """
    Create an embedding function with optional fallback.
    
    Args:
        openai_api_key: OpenAI API key (optional)
        use_fallback: Whether to use Hugging Face as fallback
    
    Returns:
        Embedding function instance
    """
    if use_fallback:
        try:
            return FallbackEmbeddingFunction(openai_api_key=openai_api_key)
        except Exception as e:
            logger.warning(f"Fallback embedding initialization failed: {e}")
    
    # Try OpenAI only
    if openai_api_key:
        try:
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            return OpenAIEmbeddingFunction(
                api_key=openai_api_key,
                model_name="text-embedding-ada-002"
            )
        except Exception as e:
            logger.error(f"OpenAI embedding initialization failed: {e}")
    
    raise RuntimeError("No embedding functions available. Either provide valid OpenAI API key or install sentence-transformers.")