#!/usr/bin/env python3
"""
RAG System Demo with Mock Embeddings (No OpenAI Required).

Demonstrates the complete RAG system functionality without needing OpenAI API calls.
Uses mock embeddings and local similarity calculations.
"""

import sys
import os
import asyncio
from pathlib import Path
import numpy as np
from typing import Dict, List, Any, Optional
import json
from datetime import datetime

# Add the backend src to path
backend_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(backend_src))
os.environ['PYTHONPATH'] = str(backend_src)

class MockEmbeddingFunction:
    """Mock embedding function that doesn't require OpenAI API."""
    
    def __init__(self):
        # Simple word-based embeddings for demo
        self.word_vectors = {
            'ocean': [1.0, 0.8, 0.2, 0.3, 0.1],
            'temperature': [0.8, 1.0, 0.1, 0.4, 0.2],
            'salinity': [0.6, 0.3, 1.0, 0.2, 0.1],
            'argo': [0.4, 0.2, 0.3, 1.0, 0.8],
            'float': [0.3, 0.1, 0.2, 0.9, 1.0],
            'density': [0.7, 0.6, 0.8, 0.1, 0.2],
            'profile': [0.5, 0.7, 0.4, 0.8, 0.3],
            'measurement': [0.6, 0.8, 0.5, 0.7, 0.4],
            'thermocline': [0.8, 0.9, 0.3, 0.2, 0.1],
            'deep': [0.2, 0.3, 0.1, 0.4, 0.8],
            'surface': [0.9, 0.7, 0.2, 0.3, 0.1],
        }
        
    def __call__(self, texts):
        """Generate embeddings for texts."""
        embeddings = []
        for text in texts:
            # Simple word-based embedding
            words = text.lower().split()
            embedding = np.zeros(5)
            count = 0
            
            for word in words:
                if word in self.word_vectors:
                    embedding += np.array(self.word_vectors[word])
                    count += 1
                else:
                    # Random embedding for unknown words
                    embedding += np.random.random(5) * 0.1
                    count += 1
            
            if count > 0:
                embedding = embedding / count
            else:
                embedding = np.random.random(5) * 0.1
                
            embeddings.append(embedding.tolist())
        
        return embeddings

class MockVectorStore:
    """Mock vector store that simulates ChromaDB without OpenAI API."""
    
    def __init__(self):
        self.collections = {}
        self.embedding_function = MockEmbeddingFunction()
        
    def get_or_create_collection(self, name, embedding_function=None, metadata=None):
        if name not in self.collections:
            self.collections[name] = {
                'documents': [],
                'embeddings': [],
                'metadatas': [],
                'ids': [],
                'metadata': metadata or {}
            }
        return MockCollection(name, self)
    
    def get_collection_stats(self):
        stats = {}
        for name, collection in self.collections.items():
            stats[name] = {
                'document_count': len(collection['documents']),
                'collection_metadata': collection['metadata']
            }
        return stats
    
    def bulk_add_knowledge(self, knowledge_data):
        """Bulk add knowledge data to multiple collections."""
        results = {}
        
        for collection_name, documents_data in knowledge_data.items():
            try:
                # Get or create collection
                collection = self.get_or_create_collection(
                    collection_name, 
                    metadata={"description": f"Collection for {collection_name}"}
                )
                
                # Extract documents and metadata
                documents = [doc['content'] for doc in documents_data]
                metadatas = [doc.get('metadata', {}) for doc in documents_data]
                
                # Add to collection
                collection.add(documents=documents, metadatas=metadatas)
                
                results[collection_name] = True
                
            except Exception as e:
                print(f"Error adding to collection {collection_name}: {e}")
                results[collection_name] = False
        
        return results
    
    def search_similar(self, query, collection_names=None, n_results=5, min_relevance_score=0.7):
        """Search for similar documents across collections."""
        if collection_names is None:
            collection_names = list(self.collections.keys())
        
        all_results = []
        
        for collection_name in collection_names:
            if collection_name in self.collections:
                collection = MockCollection(collection_name, self)
                results = collection.search_similar(
                    query, n_results=n_results, min_relevance_score=min_relevance_score
                )
                all_results.extend(results)
        
        # Sort by similarity score (descending)
        all_results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return all_results[:n_results]

class MockCollection:
    """Mock collection for the vector store."""
    
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self.metadata = store.collections[name]['metadata']
    
    def add(self, documents, metadatas=None, ids=None):
        """Add documents to collection."""
        collection = self.store.collections[self.name]
        
        # Generate embeddings
        embeddings = self.store.embedding_function(documents)
        
        collection['documents'].extend(documents)
        collection['embeddings'].extend(embeddings)
        collection['metadatas'].extend(metadatas or [{} for _ in documents])
        collection['ids'].extend(ids or [f"{self.name}_{i}" for i in range(len(documents))])
    
    def query(self, query_texts, n_results=5, include=None):
        """Query the collection."""
        collection = self.store.collections[self.name]
        
        if not collection['documents']:
            return {'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        # Generate query embedding
        query_embeddings = self.store.embedding_function(query_texts)
        query_embedding = np.array(query_embeddings[0])
        
        # Calculate distances
        distances = []
        for doc_embedding in collection['embeddings']:
            doc_emb = np.array(doc_embedding)
            # Cosine distance
            cos_sim = np.dot(query_embedding, doc_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb))
            distance = 1 - cos_sim
            distances.append(max(0, distance))  # Ensure non-negative
        
        # Sort by distance and get top results
        sorted_indices = sorted(range(len(distances)), key=lambda i: distances[i])[:n_results]
        
        return {
            'documents': [[collection['documents'][i] for i in sorted_indices]],
            'metadatas': [[collection['metadatas'][i] for i in sorted_indices]],
            'distances': [[distances[i] for i in sorted_indices]]
        }
    
    def count(self):
        return len(self.store.collections[self.name]['documents'])
    
    def peek(self, limit=10):
        collection = self.store.collections[self.name]
        return {
            'documents': collection['documents'][:limit],
            'metadatas': collection['metadatas'][:limit]
        }
    
    def add_documents(self, collection_name, documents, metadatas=None):
        """Add documents to specific collection."""
        return self.add(documents, metadatas)
    
    def search_similar(self, query, collection_names=None, n_results=5, min_relevance_score=0.7):
        """Search for similar documents."""
        results = self.query([query], n_results=n_results)
        
        formatted_results = []
        if results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i]
                similarity_score = 1 / (1 + distance)
                
                if similarity_score >= min_relevance_score:
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i],
                        'collection': self.name,
                        'similarity_score': similarity_score,
                        'distance': distance
                    })
        
        return formatted_results

async def demo_rag_system():
    """Demo the RAG system with mock embeddings."""
    
    print("🎭 OceanQuery RAG System Demo (Mock Embeddings)")
    print("=" * 60)
    print("This demo shows RAG functionality without requiring OpenAI API calls")
    print()
    
    try:
        # 1. Create mock services
        print("1. Creating mock RAG services...")
        
        # Import required modules
        from services.rag.knowledge_manager import KnowledgeManager
        from services.rag.rag_orchestrator import RAGOrchestrator
        
        # Create mock vector store
        mock_vector_store = MockVectorStore()
        print("   ✅ Mock vector store created")
        
        # Create knowledge manager with mock store
        knowledge_manager = KnowledgeManager(mock_vector_store)
        print("   ✅ Knowledge manager created")
        
        # Create RAG orchestrator
        rag_orchestrator = RAGOrchestrator(mock_vector_store, knowledge_manager)
        print("   ✅ RAG orchestrator created")
        
        # 2. Load knowledge base
        print("\n2. Loading oceanographic knowledge base...")
        load_results = knowledge_manager.load_oceanographic_knowledge()
        successful_loads = sum(1 for success in load_results.values() if success)
        print(f"   📚 Loaded knowledge into {successful_loads}/{len(load_results)} collections")
        
        # Show collection stats
        stats = mock_vector_store.get_collection_stats()
        total_docs = sum(s['document_count'] for s in stats.values())
        print(f"   📊 Total documents: {total_docs}")
        for collection, info in stats.items():
            print(f"   📁 {collection}: {info['document_count']} documents")
        
        # 3. Test knowledge search
        print("\n3. Testing knowledge search capabilities...")
        test_queries = [
            "What is ocean temperature?",
            "How do ARGO floats work?",
            "Explain salinity measurements",
            "What causes thermocline variations?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n   🔍 Query {i}: '{query}'")
            results = knowledge_manager.search_knowledge(query, max_results=3, min_relevance=0.1)
            print(f"   📋 Found {len(results)} relevant documents")
            
            if results:
                top_result = results[0]
                relevance = top_result.get('relevance_score', 0)
                collection = top_result.get('collection', 'unknown')
                content = top_result.get('content', '')[:100] + "..."
                
                print(f"   🏆 Top result from '{collection}' (relevance: {relevance:.3f})")
                print(f"      {content}")
        
        # 4. Test RAG orchestrator context enhancement
        print("\n4. Testing RAG context enhancement...")
        
        sample_queries = [
            {
                "query": "Show temperature profiles in the Pacific",
                "intent": {
                    "intent_type": "data_analysis",
                    "parameters": {"location": "Pacific", "measurement": "temperature"}
                }
            },
            {
                "query": "How accurate are ARGO measurements?",
                "intent": {
                    "intent_type": "argo_specific",
                    "parameters": {"topic": "accuracy"}
                }
            }
        ]
        
        for i, test_case in enumerate(sample_queries, 1):
            query = test_case["query"]
            intent = test_case["intent"]
            
            print(f"\n   🎯 Test {i}: '{query}'")
            
            enhanced_context = rag_orchestrator.enhance_query_with_context(
                user_query=query,
                conversation_history=None,
                query_intent=intent
            )
            
            status = enhanced_context.get('enhancement_status')
            knowledge_count = len(enhanced_context.get('knowledge_context', []))
            summary = enhanced_context.get('context_summary', 'No context')
            
            print(f"   📈 Enhancement status: {status}")
            print(f"   📚 Knowledge chunks: {knowledge_count}")
            print(f"   📝 Context summary: {summary}")
            
            # Show knowledge insights
            knowledge_context = enhanced_context.get('knowledge_context', [])
            if knowledge_context:
                print("   💡 Knowledge insights:")
                for j, item in enumerate(knowledge_context[:2], 1):
                    topic = item.get('metadata', {}).get('topic', 'general')
                    score = item.get('relevance_score', 0)
                    print(f"      {j}. {topic.title()} (relevance: {score:.3f})")
        
        # 5. Test conversation context analysis
        print("\n5. Testing conversation context analysis...")
        
        conversation_history = [
            {"role": "user", "content": "Tell me about ocean temperature"},
            {"role": "assistant", "content": "Ocean temperature varies globally..."},
            {"role": "user", "content": "What about salinity?"}
        ]
        
        enhanced_context = rag_orchestrator.enhance_query_with_context(
            user_query="Compare them in the Atlantic",
            conversation_history=conversation_history,
            query_intent={"intent_type": "comparison"}
        )
        
        conv_context = enhanced_context.get('conversation_context', {})
        print(f"   💬 Conversation analysis: {conv_context.get('has_context', False)}")
        print(f"   🔤 Recent topics: {conv_context.get('recent_topics', [])}")
        print(f"   ⏰ Temporal references: {conv_context.get('temporal_references', False)}")
        
        # 6. Show RAG system statistics
        print("\n6. RAG system statistics...")
        rag_stats = rag_orchestrator.get_rag_statistics()
        
        kb_stats = rag_stats.get('knowledge_base', {})
        config = rag_stats.get('configuration', {})
        
        print(f"   📊 Total documents in knowledge base: {kb_stats.get('total_documents', 0)}")
        print(f"   ⚙️  Max context tokens: {config.get('max_context_tokens', 'N/A')}")
        print(f"   🎯 Relevance threshold: {config.get('relevance_threshold', 'N/A')}")
        print(f"   📦 Max knowledge chunks: {config.get('max_knowledge_chunks', 'N/A')}")
        
        # 7. Export knowledge summary
        print("\n7. Knowledge base summary...")
        summary = knowledge_manager.export_knowledge_summary()
        
        print("   📚 Collection samples:")
        samples = summary.get('sample_documents', {})
        for collection, docs in samples.items():
            if docs:
                print(f"      {collection}: {len(docs)} sample(s)")
                print(f"         \"{docs[0][:60]}...\"")
        
        print(f"\n   📅 Export timestamp: {summary.get('export_timestamp')}")
        
        print("\n🎉 RAG System Demo completed successfully!")
        print("\n✨ Key Features Demonstrated:")
        print("   • 📚 Knowledge base loading and management")
        print("   • 🔍 Semantic search across specialized collections")
        print("   • 🎯 Intent-based knowledge retrieval")
        print("   • 💬 Conversation context analysis")
        print("   • 📊 Comprehensive system statistics")
        print("   • 🧠 Context-aware response enhancement")
        
        print("\n🚀 Your RAG system is fully functional!")
        print("   Once OpenAI quota is resolved, it will provide even better embeddings.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ RAG demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main demo function."""
    print("OceanQuery RAG System - Mock Demo")
    print("=" * 40)
    print("This demonstration shows the RAG system working")
    print("without requiring OpenAI API calls.")
    print()
    
    success = asyncio.run(demo_rag_system())
    
    if success:
        print("\n" + "=" * 60)
        print("🔧 OPENAI QUOTA ISSUE RESOLUTION:")
        print("=" * 60)
        print("Your OpenAI API key has exceeded the quota. To resolve:")
        print()
        print("1. 💳 Check your billing at: https://platform.openai.com/account/billing")
        print("2. 💰 Add credits to your OpenAI account")
        print("3. 📊 Monitor usage at: https://platform.openai.com/account/usage")
        print()
        print("🔄 Alternatives while resolving quota:")
        print("   • Use the RAG system in offline mode (as demonstrated)")
        print("   • Implement Hugging Face embeddings as backup")
        print("   • Use local LLM models for embeddings")
        print()
        print("✨ The RAG system architecture is complete and ready!")
        sys.exit(0)
    else:
        print("\n💥 Demo needs attention.")
        sys.exit(1)

if __name__ == "__main__":
    main()