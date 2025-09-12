#!/usr/bin/env python3
"""
Test RAG system structure without OpenAI dependency.
"""

import sys
import os
from pathlib import Path

# Add the backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

# Set PYTHONPATH to include src directory
os.environ['PYTHONPATH'] = str(backend_src)

def test_rag_imports():
    """Test that all RAG components can be imported."""
    
    print("🧪 Testing RAG System Structure")
    print("=" * 40)
    
    try:
        print("1. Testing imports...")
        
        # Test individual imports
        from services.rag.vector_store import VectorStoreService
        print("   ✅ VectorStoreService imported")
        
        from services.rag.knowledge_manager import KnowledgeManager  
        print("   ✅ KnowledgeManager imported")
        
        from services.rag.rag_orchestrator import RAGOrchestrator
        print("   ✅ RAGOrchestrator imported")
        
        # Test main module import
        from services.rag import initialize_rag_system
        print("   ✅ initialize_rag_system imported")
        
        print("\n2. Testing knowledge data structure...")
        from services.rag.knowledge_manager import create_knowledge_manager
        
        # Create a mock vector store for testing
        class MockVectorStore:
            def __init__(self):
                self.collections = {
                    "oceanography": None,
                    "argo": None, 
                    "measurements": None,
                    "analysis": None,
                    "examples": None
                }
            
            def bulk_add_knowledge(self, data):
                return {k: True for k in data.keys()}
        
        mock_store = MockVectorStore()
        km = create_knowledge_manager(mock_store)
        
        # Test knowledge data
        knowledge_data = km._get_oceanographic_knowledge_data()
        print(f"   📊 Knowledge collections: {list(knowledge_data.keys())}")
        
        total_items = sum(len(items) for items in knowledge_data.values())
        print(f"   📚 Total knowledge items: {total_items}")
        
        for collection, items in knowledge_data.items():
            print(f"   📁 {collection}: {len(items)} items")
        
        print("\n3. Testing configuration...")
        from core.config import settings
        print(f"   ⚙️  Vector DB Path: {settings.chroma_persist_directory}")
        print(f"   ⚙️  RAG Max Tokens: {settings.rag_max_context_tokens}")
        print(f"   ⚙️  Relevance Threshold: {settings.rag_relevance_threshold}")
        print(f"   ⚙️  Max Chunks: {settings.rag_max_chunks}")
        
        print("\n🎉 RAG system structure is valid!")
        print("✨ Ready to test with OpenAI API key!")
        return True
        
    except Exception as e:
        print(f"\n❌ RAG structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_imports()
    sys.exit(0 if success else 1)