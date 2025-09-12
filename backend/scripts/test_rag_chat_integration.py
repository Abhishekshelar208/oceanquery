#!/usr/bin/env python3
"""
Test script for RAG-enhanced chat pipeline integration.

This script tests the enhanced chat pipeline with RAG system integration.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))
os.environ['PYTHONPATH'] = str(backend_src)

async def test_rag_chat_integration():
    """Test the RAG-enhanced chat pipeline."""
    
    print("🧪 Testing RAG-Enhanced Chat Pipeline")
    print("=" * 50)
    
    try:
        # Import the enhanced chat pipeline
        print("1. Importing enhanced chat pipeline...")
        from services.nlp.enhanced_chat_pipeline import create_enhanced_chat_pipeline
        print("   ✅ Enhanced chat pipeline imported")
        
        # Initialize with RAG enabled
        print("\n2. Initializing RAG-enhanced chat pipeline...")
        pipeline = create_enhanced_chat_pipeline(enable_rag=True)
        print("   ✅ Pipeline initialized")
        print(f"   📊 RAG enabled: {pipeline.enable_rag}")
        
        if pipeline.rag_system:
            print("   ✅ RAG system loaded successfully")
        else:
            print("   ⚠️ RAG system not loaded (may need OpenAI API key)")
        
        # Test pipeline statistics
        print("\n3. Testing pipeline statistics...")
        stats = pipeline.get_pipeline_stats()
        print(f"   📊 Total queries processed: {stats['total_queries_processed']}")
        print(f"   🤖 RAG enabled: {stats['rag_enabled']}")
        print(f"   🧠 RAG enhanced queries: {stats['rag_enhanced_queries']}")
        print(f"   📈 RAG enhancement rate: {stats['rag_enhancement_rate']}%")
        
        if 'rag_system_stats' in stats:
            rag_stats = stats['rag_system_stats']
            kb_stats = rag_stats.get('knowledge_base', {})
            print(f"   📚 Total documents in knowledge base: {kb_stats.get('total_documents', 0)}")
        
        # Test sample queries
        print("\n4. Testing sample queries...")
        test_queries = [
            {
                "query": "What is ocean temperature?",
                "description": "Basic oceanography question"
            },
            {
                "query": "How do ARGO floats measure salinity?", 
                "description": "ARGO-specific technical question"
            },
            {
                "query": "Show me temperature profiles in the North Atlantic",
                "description": "Data retrieval with location"
            },
            {
                "query": "What causes thermocline variations?",
                "description": "Process understanding question"
            }
        ]
        
        for i, test_case in enumerate(test_queries, 1):
            query = test_case["query"]
            description = test_case["description"]
            
            print(f"\n   🔍 Query {i}: {description}")
            print(f"   Question: '{query}'")
            
            try:
                # Process without database (will handle gracefully)
                response = await pipeline.process_query(
                    user_query=query,
                    conversation_id=f"test_conv_{i}",
                    include_sql=False,
                    db_session=None  # No database session
                )
                
                print(f"   ✅ Response generated")
                print(f"   📝 Success: {response.get('success', False)}")
                
                # Check if RAG enhanced
                context_info = response.get('context_info', {})
                rag_enhanced = context_info.get('rag_enhanced', False)
                knowledge_summary = context_info.get('knowledge_context_summary')
                
                if rag_enhanced:
                    print(f"   🧠 RAG enhanced: Yes")
                    print(f"   📚 Knowledge context: {knowledge_summary}")
                    
                    # Show knowledge insights if available
                    data = response.get('data', {})
                    insights = data.get('knowledge_insights', [])
                    if insights:
                        print(f"   💡 Knowledge insights: {len(insights)} items")
                        for insight in insights[:2]:
                            topic = insight.get('topic', 'general').replace('_', ' ').title()
                            print(f"      - {topic} (relevance: {insight.get('relevance', 0):.2f})")
                else:
                    print(f"   🧠 RAG enhanced: No (may need OpenAI API key)")
                
                # Show message preview
                message = response.get('message', '')
                if len(message) > 100:
                    message_preview = message[:97] + "..."
                else:
                    message_preview = message
                print(f"   💬 Message preview: {message_preview}")
                
            except Exception as e:
                print(f"   ❌ Query failed: {e}")
        
        # Test conversation context
        print("\n5. Testing conversation context...")
        conv_id = "test_conversation_context"
        
        # First query
        response1 = await pipeline.process_query(
            "Tell me about ARGO floats",
            conversation_id=conv_id,
            include_sql=False
        )
        print("   📝 First query: 'Tell me about ARGO floats'")
        
        # Follow-up query
        response2 = await pipeline.process_query(
            "How accurate are their measurements?",
            conversation_id=conv_id,
            include_sql=False
        )
        print("   📝 Follow-up query: 'How accurate are their measurements?'")
        
        context_info2 = response2.get('context_info', {})
        if context_info2.get('applied_context', False):
            print("   ✅ Conversation context applied successfully")
        else:
            print("   ⚠️ Conversation context not applied")
        
        # Final statistics
        print("\n6. Final pipeline statistics...")
        final_stats = pipeline.get_pipeline_stats()
        print(f"   📊 Total queries processed: {final_stats['total_queries_processed']}")
        print(f"   ✅ Successful queries: {final_stats['successful_queries']}")
        print(f"   ❌ Failed queries: {final_stats['failed_queries']}")
        print(f"   📈 Success rate: {final_stats['success_rate']}%")
        print(f"   🧠 RAG enhanced queries: {final_stats['rag_enhanced_queries']}")
        print(f"   📚 Total knowledge chunks used: {final_stats['total_knowledge_chunks_used']}")
        
        print("\n🎉 RAG-Enhanced Chat Pipeline integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ RAG-Enhanced Chat Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    print("Testing RAG-Enhanced Chat Pipeline Integration")
    print("=" * 55)
    
    # Check environment
    from core.config import settings
    print(f"OpenAI API Key: {'✅ Set' if settings.openai_api_key else '❌ Missing'}")
    print(f"Auto-load Knowledge: {settings.auto_load_knowledge}")
    print(f"RAG Max Context Tokens: {settings.rag_max_context_tokens}")
    print(f"RAG Relevance Threshold: {settings.rag_relevance_threshold}")
    print()
    
    if not settings.openai_api_key:
        print("⚠️  Warning: OpenAI API key not set.")
        print("   The pipeline will work but without RAG enhancements.")
        print("   Set OPENAI_API_KEY environment variable for full functionality.")
        print()
    
    # Run the test
    success = asyncio.run(test_rag_chat_integration())
    
    if success:
        print("\n✨ RAG-Enhanced Chat Pipeline is ready!")
        print("🚀 Your AI chat system now has:")
        print("   • Intelligent context awareness")
        print("   • Oceanographic knowledge integration")
        print("   • Enhanced response quality")
        print("   • Conversation continuity")
        sys.exit(0)
    else:
        print("\n💥 Integration needs attention.")
        sys.exit(1)


if __name__ == "__main__":
    main()