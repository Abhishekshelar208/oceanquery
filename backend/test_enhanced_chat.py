#!/usr/bin/env python3
"""
Test script for Enhanced AI Chat Pipeline
"""

import asyncio
import sys
import os
sys.path.append('src')

from services.nlp.enhanced_chat_pipeline import create_enhanced_chat_pipeline


async def test_queries():
    """Test various natural language queries."""
    
    # Create pipeline
    pipeline = create_enhanced_chat_pipeline()
    
    # Test queries
    test_queries = [
        "How many ARGO floats are active?",
        "Show me temperature data from the Arabian Sea",
        "What's the average salinity in 2023?",
        "Compare temperature between Indian Ocean and Bay of Bengal",
        "Show me a map of float locations",
        "Plot temperature profile for 2902755_001",
        "What about salinity?",  # Follow-up question
        "Give me statistics",
        "Help me understand ARGO data"
    ]
    
    conversation_id = "test_conv_123"
    
    print("🧪 Testing Enhanced AI Chat Pipeline\n")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🤖 Query {i}: {query}")
        print("-" * 40)
        
        try:
            response = await pipeline.process_query(
                user_query=query,
                conversation_id=conversation_id,
                include_sql=True,
                max_results=10
            )
            
            print(f"✅ Success (confidence: {response.get('context_info', {}).get('confidence', 0):.2f})")
            print(f"📊 Query Type: {response.get('context_info', {}).get('query_type', 'unknown')}")
            print(f"⏱️ Processing: {response.get('processing_time_ms', 0):.1f}ms")
            
            if response.get('sql_query'):
                print(f"🗄️ SQL: {response['sql_query'][:100]}...")
            
            print(f"💬 Response: {response['message'][:200]}...")
            
            if response.get('suggestions'):
                print(f"💡 Suggestions: {', '.join(response['suggestions'][:2])}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Print pipeline statistics
    print("\n" + "=" * 60)
    print("📈 Pipeline Statistics:")
    stats = pipeline.get_pipeline_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(test_queries())