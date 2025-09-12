"""
RAG (Retrieval-Augmented Generation) services for OceanQuery.

This module provides advanced AI-powered chat capabilities using:
- Vector database for oceanographic knowledge
- Semantic search and retrieval  
- Context-augmented response generation
- Scientific accuracy and citations
"""

import logging
from typing import Optional

from .vector_store import VectorStoreService, create_vector_store_service
from .knowledge_manager import KnowledgeManager, create_knowledge_manager
from .rag_orchestrator import RAGOrchestrator, create_rag_orchestrator

logger = logging.getLogger(__name__)

# Export main classes
__all__ = [
    'VectorStoreService',
    'KnowledgeManager', 
    'RAGOrchestrator',
    'create_vector_store_service',
    'create_knowledge_manager',
    'create_rag_orchestrator',
    'initialize_rag_system'
]


def initialize_rag_system(persist_directory: Optional[str] = None, embedding_model: Optional[str] = None) -> tuple[VectorStoreService, KnowledgeManager, RAGOrchestrator]:
    """
    Initialize complete RAG system with Sentence Transformers.
    
    Args:
        persist_directory: Directory to persist vector database
        embedding_model: Sentence Transformers model name (optional)
        
    Returns:
        Tuple of (vector_store, knowledge_manager, rag_orchestrator)
    """
    logger.info("Initializing RAG system with Sentence Transformers...")
    
    # Create vector store with Sentence Transformers
    vector_store = create_vector_store_service(
        persist_directory=persist_directory,
        embedding_model=embedding_model
    )
    logger.info("Vector store service created with Sentence Transformers")
    
    # Create knowledge manager
    knowledge_manager = create_knowledge_manager(vector_store)
    logger.info("Knowledge manager created")
    
    # Create RAG orchestrator
    rag_orchestrator = create_rag_orchestrator(vector_store, knowledge_manager)
    logger.info("RAG orchestrator created")
    
    logger.info("RAG system initialization complete")
    return vector_store, knowledge_manager, rag_orchestrator


logger.info("RAG services module initialized")
