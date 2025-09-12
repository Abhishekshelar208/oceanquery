"""
Vector Database Service for OceanQuery RAG system.

Handles ChromaDB integration, embeddings management, and semantic search.
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import chromadb
from chromadb.config import Settings
# Remove OpenAI dependency - using local embeddings
# from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
# import openai
# from openai import OpenAI

from core.config import settings
from .sentence_transformers_embeddings import create_chromadb_embedding_function

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Vector database service for oceanographic knowledge storage and retrieval."""
    
    def __init__(self, persist_directory: Optional[str] = None, embedding_model: Optional[str] = None):
        """
        Initialize vector store service with Sentence Transformers.
        
        Args:
            persist_directory: Directory to persist vector database
            embedding_model: Sentence Transformers model name (optional)
        """
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Set up persistence directory
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Set up Sentence Transformers embedding function
        try:
            self.embedding_function = create_chromadb_embedding_function(
                model_name=embedding_model,
                use_case="production"
            )
            self.logger.info(f"Initialized Sentence Transformers embeddings: {self.embedding_function.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize embeddings: {e}")
            raise RuntimeError(f"Embedding initialization failed: {e}")
        
        # Initialize collections
        self.collections = {}
        self._initialize_collections()
        
        self.logger.info(f"Vector store initialized with persist directory: {self.persist_directory}")
    
    def _initialize_collections(self):
        """Initialize ChromaDB collections for different knowledge types."""
        
        collection_configs = {
            "oceanography": {
                "name": "oceanography_knowledge",
                "metadata": {"description": "General oceanographic concepts and terminology"}
            },
            "argo": {
                "name": "argo_documentation", 
                "metadata": {"description": "ARGO float system documentation and technical details"}
            },
            "measurements": {
                "name": "measurement_explanations",
                "metadata": {"description": "Ocean measurement types, units, and interpretations"}
            },
            "analysis": {
                "name": "analysis_methods",
                "metadata": {"description": "Data analysis methods and scientific interpretations"}
            },
            "examples": {
                "name": "query_examples",
                "metadata": {"description": "Example queries and their explanations"}
            }
        }
        
        for collection_key, config in collection_configs.items():
            try:
                collection = self.client.get_or_create_collection(
                    name=config["name"],
                    embedding_function=self.embedding_function,
                    metadata=config["metadata"]
                )
                self.collections[collection_key] = collection
                self.logger.debug(f"Initialized collection: {config['name']}")
                
            except Exception as e:
                self.logger.error(f"Error initializing collection {config['name']}: {e}")
                raise
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ) -> bool:
        """
        Add documents to a collection.
        
        Args:
            collection_name: Name of the collection
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional custom IDs for documents
            
        Returns:
            Success status
        """
        try:
            if collection_name not in self.collections:
                raise ValueError(f"Collection '{collection_name}' not found")
            
            collection = self.collections[collection_name]
            
            # Generate IDs if not provided
            if ids is None:
                ids = [self._generate_document_id(doc, collection_name, i) 
                       for i, doc in enumerate(documents)]
            
            # Prepare metadatas
            if metadatas is None:
                metadatas = [{"source": "manual", "collection": collection_name} 
                           for _ in documents]
            
            # Add documents to collection
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            self.logger.info(f"Added {len(documents)} documents to collection '{collection_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding documents to collection '{collection_name}': {e}")
            return False
    
    def search_similar(
        self,
        query: str,
        collection_names: Optional[List[str]] = None,
        n_results: int = 5,
        min_relevance_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents across collections.
        
        Args:
            query: Search query
            collection_names: Collections to search (all if None)
            n_results: Maximum number of results per collection
            min_relevance_score: Minimum relevance score threshold
            
        Returns:
            List of search results with scores and metadata
        """
        if collection_names is None:
            collection_names = list(self.collections.keys())
        
        all_results = []
        
        for collection_name in collection_names:
            if collection_name not in self.collections:
                self.logger.warning(f"Collection '{collection_name}' not found, skipping")
                continue
            
            try:
                collection = self.collections[collection_name]
                
                # Perform similarity search
                results = collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    include=['documents', 'metadatas', 'distances']
                )
                
                # Process results
                for i, document in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i]
                    # Convert distance to similarity score (0-1, higher is better)
                    similarity_score = 1 / (1 + distance)
                    
                    if similarity_score >= min_relevance_score:
                        result = {
                            'content': document,
                            'metadata': results['metadatas'][0][i],
                            'collection': collection_name,
                            'similarity_score': similarity_score,
                            'distance': distance
                        }
                        all_results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error searching collection '{collection_name}': {e}")
        
        # Sort by similarity score (descending)
        all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        self.logger.debug(f"Found {len(all_results)} relevant documents for query: '{query[:50]}...'")
        return all_results
    
    def get_collection_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all collections."""
        
        stats = {}
        
        for collection_name, collection in self.collections.items():
            try:
                count = collection.count()
                stats[collection_name] = {
                    'document_count': count,
                    'collection_metadata': collection.metadata
                }
            except Exception as e:
                self.logger.error(f"Error getting stats for collection '{collection_name}': {e}")
                stats[collection_name] = {
                    'document_count': 0,
                    'error': str(e)
                }
        
        return stats
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection and all its documents."""
        
        try:
            if collection_name in self.collections:
                self.client.delete_collection(name=self.collections[collection_name].name)
                del self.collections[collection_name]
                self.logger.info(f"Deleted collection: {collection_name}")
                return True
            else:
                self.logger.warning(f"Collection '{collection_name}' not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Error deleting collection '{collection_name}': {e}")
            return False
    
    def reset_database(self) -> bool:
        """Reset the entire vector database (USE WITH CAUTION)."""
        
        try:
            # Delete all collections
            for collection_name in list(self.collections.keys()):
                self.delete_collection(collection_name)
            
            # Reset client
            self.client.reset()
            
            # Reinitialize collections
            self._initialize_collections()
            
            self.logger.warning("Vector database has been reset!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error resetting database: {e}")
            return False
    
    def _generate_document_id(self, document: str, collection: str, index: int) -> str:
        """Generate a unique ID for a document."""
        
        # Create hash from document content + collection + index
        content = f"{document}{collection}{index}"
        doc_hash = hashlib.md5(content.encode()).hexdigest()[:16]
        return f"{collection}_{doc_hash}"
    
    def bulk_add_knowledge(self, knowledge_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, bool]:
        """
        Bulk add knowledge data to multiple collections.
        
        Args:
            knowledge_data: Dict with collection names as keys and list of documents as values
                          Each document should have 'content' and optionally 'metadata'
        
        Returns:
            Status for each collection
        """
        results = {}
        
        for collection_name, documents_data in knowledge_data.items():
            try:
                documents = [doc['content'] for doc in documents_data]
                metadatas = [doc.get('metadata', {}) for doc in documents_data]
                
                # Add source information to metadata
                for metadata in metadatas:
                    metadata['added_via'] = 'bulk_add'
                    metadata['collection'] = collection_name
                
                success = self.add_documents(
                    collection_name=collection_name,
                    documents=documents,
                    metadatas=metadatas
                )
                results[collection_name] = success
                
            except Exception as e:
                self.logger.error(f"Error bulk adding to collection '{collection_name}': {e}")
                results[collection_name] = False
        
        return results


def create_vector_store_service(persist_directory: Optional[str] = None, embedding_model: Optional[str] = None) -> VectorStoreService:
    """Factory function to create vector store service with Sentence Transformers."""
    return VectorStoreService(persist_directory=persist_directory, embedding_model=embedding_model)
