#!/usr/bin/env python3
"""
Test RAG-enhanced chatbot with conceptual questions that don't require database.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))
os.environ['PYTHONPATH'] = str(backend_src)

async def test_conceptual_questions():
    """Test RAG chatbot with conceptual oceanography questions."""
    
    print("🤖 Testing RAG-Enhanced Chatbot - Conceptual Questions")
    print("=" * 60)
    
    # Import and initialize
    from services.nlp.enhanced_chat_pipeline import create_enhanced_chat_pipeline
    
    print("Initializing RAG-enhanced chatbot...")
    pipeline = create_enhanced_chat_pipeline(enable_rag=True)
    print("✅ Chatbot ready with RAG system\n")
    
    # Test conceptual questions
    questions = [
        {
            "question": "What is a thermocline?",
            "expected_rag": "Should provide definition, depth characteristics, and oceanographic importance",
            "expected_knowledge": "thermocline, temperature gradient, water column"
        },
        {
            "question": "Explain ARGO float sensors",
            "expected_rag": "Should detail sensor types, measurement capabilities, and technical specifications", 
            "expected_knowledge": "conductivity, temperature, pressure, quality control"
        },
        {
            "question": "How is salinity measured?",
            "expected_rag": "Should explain measurement methods, units (PSU), and calibration processes",
            "expected_knowledge": "conductivity, practical salinity units, measurement accuracy"
        }
    ]
    
    for i, test in enumerate(questions, 1):
        print(f"🔍 Question {i}: \"{test['question']}\"")
        print(f"📝 Expected RAG Enhancement: {test['expected_rag']}")
        
        try:
            # Process with RAG enhancement 
            response = await pipeline.process_query(
                user_query=test['question'],
                conversation_id=f"concept_test_{i}",
                include_sql=False,
                db_session=None
            )
            
            # Check RAG enhancement
            context_info = response.get('context_info', {})
            rag_enhanced = context_info.get('rag_enhanced', False)
            knowledge_summary = context_info.get('knowledge_context_summary', '')
            
            print(f"🧠 RAG Enhanced: {rag_enhanced}")
            if knowledge_summary:
                print(f"📚 Knowledge Context: {knowledge_summary}")
            
            # Check for knowledge insights in response data
            data = response.get('data', {})
            insights = data.get('knowledge_insights', [])
            
            if insights:
                print(f"💡 Knowledge Insights ({len(insights)} found):")
                for j, insight in enumerate(insights[:2], 1):
                    topic = insight.get('topic', 'general')
                    relevance = insight.get('relevance', 0)
                    print(f"   {j}. {topic.title()} (relevance: {relevance:.3f})")
            
            # Show enhanced message
            message = response.get('message', '')
            if "🧠 **Ocean Science Insights:**" in message:
                print("✅ RAG insights added to response!")
                # Show just the insights section
                if "---" in message:
                    insights_section = message.split("---")[-1][:300] + "..."
                    print(f"📖 Insights Preview: {insights_section}")
            else:
                print("⚠️  No RAG insights in response")
                preview = message[:150] + "..." if len(message) > 150 else message
                print(f"💬 Response: {preview}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("-" * 50)
    
    # Final statistics
    print(f"\n📊 Final Statistics:")
    stats = pipeline.get_pipeline_stats()
    print(f"   Total Queries: {stats.get('total_queries_processed', 0)}")
    print(f"   RAG Enhanced: {stats.get('rag_enhanced_queries', 0)}")
    print(f"   Knowledge Chunks: {stats.get('total_knowledge_chunks_used', 0)}")
    print(f"   Enhancement Rate: {stats.get('rag_enhancement_rate', 0)}%")
    
    if stats.get('rag_enhanced_queries', 0) > 0:
        print("\n🎉 RAG system is successfully enhancing chatbot responses!")
    else:
        print("\n⚠️  RAG system may need debugging - no enhancements detected")

if __name__ == "__main__":
    asyncio.run(test_conceptual_questions())