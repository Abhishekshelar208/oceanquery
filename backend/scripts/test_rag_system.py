#!/usr/bin/env python3
"""
Test script for RAG system functionality.

This script tests the vector database, knowledge manager, and RAG orchestrator
to ensure they work correctly together.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))

# Now import our modules
from services.rag import initialize_rag_system
from core.config import settings

async def test_rag_system():
    """Test the complete RAG system functionality."""
    
    print("🧪 Testing OceanQuery RAG System")
    print("=" * 50)
    
    try:
        # Initialize RAG system
        print("1. Initializing RAG system...")
        vector_store, knowledge_manager, rag_orchestrator = initialize_rag_system()
        print("   ✅ RAG system initialized successfully")
        
        # Test vector store
        print("\n2. Testing vector store statistics...")
        stats = vector_store.get_collection_stats()
        print(f"   📊 Collections: {list(stats.keys())}")
        for collection, info in stats.items():
            print(f"   📁 {collection}: {info.get('document_count', 0)} documents")
        
        # Load knowledge base
        print("\n3. Loading oceanographic knowledge...")
        load_results = knowledge_manager.load_oceanographic_knowledge()
        successful_loads = sum(1 for success in load_results.values() if success)
        print(f"   📚 Loaded knowledge into {successful_loads}/{len(load_results)} collections")
        
        # Test knowledge search
        print("\n4. Testing knowledge search...")
        test_queries = [
            "What is ocean temperature?",
            "How do ARGO floats work?", 
            "Explain salinity measurements",
            "Temperature profiles in the ocean"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n   🔍 Query {i}: '{query}'")
            results = knowledge_manager.search_knowledge(query, max_results=3)
            print(f"   📋 Found {len(results)} relevant documents")
            
            if results:
                top_result = results[0]
                print(f"   🏆 Top result (relevance: {top_result.get('relevance_score', 0):.3f})")
                content_preview = top_result.get('content', '')[:100] + "..."
                print(f"      {content_preview}")
        
        # Test RAG orchestrator context enhancement
        print("\n5. Testing RAG orchestrator context enhancement...")
        test_user_query = "Show me recent temperature trends in the Pacific Ocean"
        
        enhanced_context = rag_orchestrator.enhance_query_with_context(
            user_query=test_user_query,
            conversation_history=None,
            query_intent={
                "intent_type": "trend_analysis",
                "parameters": {"location": "Pacific", "measurement": "temperature"}
            }
        )
        
        print(f"   🎯 Enhanced context for: '{test_user_query}'")
        print(f"   📈 Status: {enhanced_context.get('enhancement_status')}")
        print(f"   📊 Knowledge chunks: {len(enhanced_context.get('knowledge_context', []))}")
        print(f"   📝 Context summary: {enhanced_context.get('context_summary')}")
        
        # Test conversation context
        print("\n6. Testing conversation context analysis...")
        conversation_history = [
            {"role": "user", "content": "Tell me about ocean temperature"},
            {"role": "assistant", "content": "Ocean temperature varies globally..."},
            {"role": "user", "content": "What about in the Arctic?"}
        ]
        
        enhanced_context_with_history = rag_orchestrator.enhance_query_with_context(
            user_query="Show recent changes there",
            conversation_history=conversation_history,
            query_intent={"intent_type": "location_specific"}
        )
        
        conv_context = enhanced_context_with_history.get('conversation_context', {})
        print(f"   💬 Conversation analysis: {conv_context.get('has_context', False)}")
        print(f"   🔤 Recent topics: {conv_context.get('recent_topics', [])}")
        
        # Get final statistics
        print("\n7. Final RAG system statistics...")
        rag_stats = rag_orchestrator.get_rag_statistics()
        kb_stats = rag_stats.get('knowledge_base', {})
        print(f"   📚 Total documents in knowledge base: {kb_stats.get('total_documents', 0)}")
        print(f"   🏗️ Configuration: {rag_stats.get('configuration', {})}")
        
        print("\n🎉 All RAG system tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ RAG system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print(f"Testing with configuration:")
    print(f"  OpenAI API Key: {'✅ Set' if settings.openai_api_key else '❌ Missing'}")
    print(f"  Vector DB Path: {settings.chroma_persist_directory}")
    print(f"  Embedding Model: {settings.embedding_model}")
    print()
    
    if not settings.openai_api_key:
        print("⚠️  Warning: OpenAI API key not set. Set OPENAI_API_KEY environment variable.")
        print("   The vector database will still be tested, but embeddings will fail.")
        print()
    
    # Run the async test
    success = asyncio.run(test_rag_system())
    
    if success:
        print("\n✨ RAG system is ready for integration!")
        sys.exit(0)
    else:
        print("\n💥 RAG system needs attention before integration.")
        sys.exit(1)


if __name__ == "__main__":
    main()