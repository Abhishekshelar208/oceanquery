"""
Production-ready Sentence Transformers embedding service for OceanQuery RAG system.

Provides high-quality, local embeddings without external API dependencies.
"""

import logging
import os
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


class SentenceTransformersEmbedding:
    """
    Production-ready Sentence Transformers embedding service.
    
    Features:
    - High-quality embeddings without API costs
    - Local processing (offline capable)
    - Thread-safe operations
    - Model caching and reuse
    - Multiple model support
    """
    
    # Recommended models for different use cases
    MODELS = {
        'default': 'all-MiniLM-L6-v2',  # Fast, good quality, 384 dims
        'high_quality': 'all-mpnet-base-v2',  # Best quality, 768 dims
        'multilingual': 'paraphrase-multilingual-MiniLM-L12-v2',  # Multilingual support
        'fast': 'all-MiniLM-L12-v2',  # Fastest processing
        'domain_specific': 'allenai-specter',  # Scientific domain
    }
    
    def __init__(self, model_name: str = None, cache_dir: Optional[str] = None):
        """
        Initialize Sentence Transformers embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model
            cache_dir: Directory to cache downloaded models
        """
        self.model_name = model_name or self.MODELS['default']
        self.cache_dir = cache_dir
        self.model = None
        self._lock = threading.Lock()
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Set cache directory if provided
        if cache_dir:
            os.environ['SENTENCE_TRANSFORMERS_HOME'] = cache_dir
            Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize model
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the sentence transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            
            self.logger.info(f"Loading Sentence Transformers model: {self.model_name}")
            
            # Load model with device optimization
            device = self._get_optimal_device()
            self.model = SentenceTransformer(self.model_name, device=device)
            
            # Get model info
            embedding_dim = self.model.get_sentence_embedding_dimension()
            max_seq_length = self.model.max_seq_length
            
            self.logger.info(f"Model loaded successfully:")
            self.logger.info(f"  - Model: {self.model_name}")
            self.logger.info(f"  - Device: {device}")
            self.logger.info(f"  - Embedding dimension: {embedding_dim}")
            self.logger.info(f"  - Max sequence length: {max_seq_length}")
            
        except ImportError as e:
            self.logger.error("sentence-transformers not installed")
            raise ImportError(
                "sentence-transformers is required. Install with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            self.logger.error(f"Failed to initialize model {self.model_name}: {e}")
            raise RuntimeError(f"Model initialization failed: {e}") from e
    
    def _get_optimal_device(self) -> str:
        """Determine the optimal device for model execution."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon GPU
            else:
                return "cpu"
        except ImportError:
            return "cpu"
    
    def encode(self, texts: List[str], batch_size: int = 32, show_progress: bool = False) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to encode
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Model not initialized")
        
        if not texts:
            return []
        
        try:
            with self._lock:  # Thread-safe encoding
                self.logger.debug(f"Encoding {len(texts)} texts with batch_size={batch_size}")
                
                # Encode texts
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True,
                    normalize_embeddings=True  # Normalize for better similarity calculations
                )
                
                # Convert numpy array to list of lists
                if isinstance(embeddings, np.ndarray):
                    embeddings = embeddings.tolist()
                
                self.logger.debug(f"Successfully encoded {len(texts)} texts")
                return embeddings
                
        except Exception as e:
            self.logger.error(f"Error encoding texts: {e}")
            raise RuntimeError(f"Encoding failed: {e}") from e
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        """Make the class callable for ChromaDB compatibility."""
        return self.encode(texts)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        if not self.model:
            return {"status": "not_initialized"}
        
        try:
            return {
                "model_name": self.model_name,
                "embedding_dimension": self.model.get_sentence_embedding_dimension(),
                "max_sequence_length": self.model.max_seq_length,
                "device": str(self.model.device),
                "status": "ready"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def similarity(self, embeddings1: List[List[float]], embeddings2: List[List[float]]) -> np.ndarray:
        """
        Calculate cosine similarity between two sets of embeddings.
        
        Args:
            embeddings1: First set of embeddings
            embeddings2: Second set of embeddings
            
        Returns:
            Similarity matrix
        """
        try:
            import torch
            
            # Convert to tensors
            emb1 = torch.tensor(embeddings1)
            emb2 = torch.tensor(embeddings2)
            
            # Calculate cosine similarity
            similarity_matrix = torch.nn.functional.cosine_similarity(
                emb1.unsqueeze(1), emb2.unsqueeze(0), dim=2
            )
            
            return similarity_matrix.numpy()
            
        except ImportError:
            # Fallback to numpy if torch not available
            emb1 = np.array(embeddings1)
            emb2 = np.array(embeddings2)
            
            # Normalize embeddings
            emb1_norm = emb1 / np.linalg.norm(emb1, axis=1, keepdims=True)
            emb2_norm = emb2 / np.linalg.norm(emb2, axis=1, keepdims=True)
            
            # Calculate cosine similarity
            return np.dot(emb1_norm, emb2_norm.T)
    
    @classmethod
    def get_available_models(cls) -> Dict[str, str]:
        """Get list of available pre-configured models."""
        return cls.MODELS.copy()
    
    @classmethod
    def recommend_model(cls, use_case: str = "general") -> str:
        """
        Recommend a model based on use case.
        
        Args:
            use_case: Use case description
            
        Returns:
            Recommended model name
        """
        recommendations = {
            "general": cls.MODELS['default'],
            "high_quality": cls.MODELS['high_quality'],
            "fast": cls.MODELS['fast'],
            "scientific": cls.MODELS['domain_specific'],
            "multilingual": cls.MODELS['multilingual'],
            "production": cls.MODELS['default'],  # Good balance of speed and quality
        }
        
        return recommendations.get(use_case.lower(), cls.MODELS['default'])


class ChromaDBSentenceTransformersEmbedding(SentenceTransformersEmbedding):
    """
    ChromaDB-compatible Sentence Transformers embedding function.
    
    Drop-in replacement for OpenAI embeddings in ChromaDB.
    """
    
    def __init__(self, model_name: str = None, **kwargs):
        """Initialize with ChromaDB compatibility."""
        super().__init__(model_name=model_name, **kwargs)
        
    def __call__(self, input: List[str]) -> List[List[float]]:
        """ChromaDB-compatible interface."""
        return self.encode(input)
    
    def name(self) -> str:
        """Return embedding function name for ChromaDB compatibility."""
        return f"sentence-transformers-{self.model_name}"
    
    def get_config(self) -> Dict[str, Any]:
        """Return configuration for ChromaDB compatibility."""
        return {
            "name": self.name(),
            "model_name": self.model_name,
            "provider": "sentence-transformers"
        }


# Factory functions
def create_embedding_function(
    model_name: str = None,
    use_case: str = "production",
    cache_dir: str = None
) -> SentenceTransformersEmbedding:
    """
    Create a production-ready embedding function.
    
    Args:
        model_name: Specific model name (optional)
        use_case: Use case for model recommendation
        cache_dir: Model cache directory
        
    Returns:
        Configured embedding function
    """
    if not model_name:
        model_name = SentenceTransformersEmbedding.recommend_model(use_case)
    
    return SentenceTransformersEmbedding(
        model_name=model_name,
        cache_dir=cache_dir
    )


def create_chromadb_embedding_function(
    model_name: str = None,
    use_case: str = "production"
) -> ChromaDBSentenceTransformersEmbedding:
    """
    Create ChromaDB-compatible embedding function.
    
    Args:
        model_name: Specific model name (optional)
        use_case: Use case for model recommendation
        
    Returns:
        ChromaDB-compatible embedding function
    """
    if not model_name:
        model_name = SentenceTransformersEmbedding.recommend_model(use_case)
    
    return ChromaDBSentenceTransformersEmbedding(model_name=model_name)


# Production settings
PRODUCTION_MODEL = SentenceTransformersEmbedding.MODELS['default']  # all-MiniLM-L6-v2
PRODUCTION_CACHE_DIR = "./models/sentence_transformers"

logger.info("Sentence Transformers embedding service initialized")