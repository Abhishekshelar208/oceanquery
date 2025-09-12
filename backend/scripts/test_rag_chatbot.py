#!/usr/bin/env python3
"""
Test RAG-enhanced chatbot with sample questions.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))
os.environ['PYTHONPATH'] = str(backend_src)

async def test_rag_chatbot():
    """Test the RAG-enhanced chatbot with sample questions."""
    
    print("🤖 Testing RAG-Enhanced Chatbot")
    print("=" * 50)
    
    # Import the enhanced chat pipeline
    from services.nlp.enhanced_chat_pipeline import create_enhanced_chat_pipeline
    
    # Initialize with RAG enabled
    pipeline = create_enhanced_chat_pipeline(enable_rag=True)
    
    # Test questions with expected outputs
    test_questions = [
        {
            "question": "What is ocean temperature?",
            "expected": "Should provide oceanographic knowledge about temperature variations, depth relationships, and climate effects with RAG insights"
        },
        {
            "question": "How do ARGO floats work?",
            "expected": "Should explain ARGO float operations, sensors, data collection cycle with technical knowledge from RAG"
        },
        {
            "question": "Show me salinity data in the Pacific",
            "expected": "Should attempt SQL query generation + provide salinity measurement knowledge from RAG system"
        }
    ]
    
    for i, test in enumerate(test_questions, 1):
        print(f"\n🔍 Question {i}: {test['question']}")
        print(f"📝 Expected: {test['expected']}")
        
        try:
            # Process query through RAG-enhanced pipeline
            response = await pipeline.process_query(
                user_query=test['question'],
                conversation_id=f"test_{i}",
                include_sql=False,  # No DB for this test
                db_session=None
            )
            
            print(f"✅ Success: {response.get('success', False)}")
            print(f"🧠 RAG Enhanced: {response.get('context_info', {}).get('rag_enhanced', False)}")
            
            # Show knowledge insights if available
            knowledge_summary = response.get('context_info', {}).get('knowledge_context_summary')
            if knowledge_summary:
                print(f"📚 Knowledge: {knowledge_summary}")
            
            # Show message preview
            message = response.get('message', '')
            preview = message[:200] + "..." if len(message) > 200 else message
            print(f"💬 Response Preview: {preview}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Show pipeline stats
    print(f"\n📊 Pipeline Statistics:")
    stats = pipeline.get_pipeline_stats()
    print(f"   RAG Enhanced Queries: {stats.get('rag_enhanced_queries', 0)}")
    print(f"   Knowledge Chunks Used: {stats.get('total_knowledge_chunks_used', 0)}")
    print(f"   Success Rate: {stats.get('success_rate', 0)}%")

if __name__ == "__main__":
    asyncio.run(test_rag_chatbot())