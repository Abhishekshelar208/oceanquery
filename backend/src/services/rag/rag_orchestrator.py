"""
RAG Orchestrator for OceanQuery system.

Coordinates knowledge retrieval, context assembly, and enhanced response generation.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from .vector_store import VectorStoreService
from .knowledge_manager import KnowledgeManager
from core.config import settings

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """Orchestrates the RAG pipeline for enhanced AI responses."""
    
    def __init__(self, vector_store: VectorStoreService, knowledge_manager: KnowledgeManager):
        """
        Initialize RAG orchestrator.
        
        Args:
            vector_store: Vector store service instance
            knowledge_manager: Knowledge manager instance
        """
        self.vector_store = vector_store
        self.knowledge_manager = knowledge_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configuration parameters
        self.max_context_tokens = settings.rag_max_context_tokens or 4000
        self.relevance_threshold = settings.rag_relevance_threshold or 0.75
        self.max_knowledge_chunks = settings.rag_max_chunks or 8
        
        self.logger.info("RAG orchestrator initialized")
    
    def enhance_query_with_context(
        self, 
        user_query: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        query_intent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhance user query with relevant oceanographic context.
        
        Args:
            user_query: Original user query
            conversation_history: Previous conversation messages
            query_intent: Parsed query intent information
            
        Returns:
            Enhanced context package for LLM
        """
        try:
            # 1. Retrieve relevant knowledge
            knowledge_context = self._retrieve_relevant_knowledge(
                user_query, query_intent
            )
            
            # 2. Analyze conversation context
            conversation_context = self._analyze_conversation_context(
                conversation_history, user_query
            )
            
            # 3. Determine domain-specific context needs
            domain_context = self._get_domain_specific_context(query_intent)
            
            # 4. Assemble comprehensive context
            enhanced_context = self._assemble_context_package(
                user_query=user_query,
                knowledge_context=knowledge_context,
                conversation_context=conversation_context,
                domain_context=domain_context,
                query_intent=query_intent
            )
            
            self.logger.info(f"Enhanced query context with {len(knowledge_context)} knowledge chunks")
            return enhanced_context
            
        except Exception as e:
            self.logger.error(f"Error enhancing query with context: {e}")
            return {
                "original_query": user_query,
                "knowledge_context": [],
                "context_summary": "Error retrieving context",
                "enhancement_status": "failed",
                "error": str(e)
            }
    
    def _retrieve_relevant_knowledge(
        self, 
        query: str, 
        query_intent: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge from vector store."""
        
        try:
            # Determine which collections to search based on query intent
            target_collections = self._select_target_collections(query, query_intent)
            
            # Perform semantic search
            knowledge_results = self.knowledge_manager.search_knowledge(
                query=query,
                collections=target_collections,
                max_results=self.max_knowledge_chunks,
                min_relevance=self.relevance_threshold
            )
            
            # Filter and rank results
            filtered_results = self._filter_and_rank_knowledge(
                knowledge_results, query, query_intent
            )
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Error retrieving relevant knowledge: {e}")
            return []
    
    def _select_target_collections(
        self, 
        query: str, 
        query_intent: Optional[Dict[str, Any]] = None
    ) -> Optional[List[str]]:
        """Select which knowledge collections to search based on query characteristics."""
        
        if not query_intent:
            return None  # Search all collections
        
        # Map intent types to relevant collections
        intent_collection_map = {
            "data_analysis": ["analysis", "measurements"],
            "measurement_explanation": ["measurements", "oceanography"],
            "argo_specific": ["argo", "measurements"],
            "conceptual_question": ["oceanography", "analysis", "examples"],
            "trend_analysis": ["analysis", "examples"],
            "comparison": ["analysis", "oceanography"],
            "location_specific": ["oceanography", "examples"],
        }
        
        # Get intent type
        intent_type = query_intent.get("intent_type", "general")
        
        # Select collections based on intent
        selected_collections = intent_collection_map.get(intent_type, None)
        
        # Add examples collection for complex queries
        query_keywords = query.lower()
        if any(word in query_keywords for word in ["how", "why", "what", "explain"]):
            if selected_collections:
                selected_collections = list(set(selected_collections + ["examples"]))
            else:
                selected_collections = ["examples", "oceanography"]
        
        self.logger.debug(f"Selected collections for intent '{intent_type}': {selected_collections}")
        return selected_collections
    
    def _filter_and_rank_knowledge(
        self, 
        knowledge_results: List[Dict[str, Any]], 
        query: str, 
        query_intent: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Filter and rank knowledge results by relevance and utility."""
        
        if not knowledge_results:
            return []
        
        # Sort by relevance score (already sorted by vector store)
        ranked_results = sorted(
            knowledge_results, 
            key=lambda x: x.get('relevance_score', 0), 
            reverse=True
        )
        
        # Apply additional filtering based on query intent
        if query_intent:
            ranked_results = self._apply_intent_based_filtering(
                ranked_results, query_intent
            )
        
        # Ensure diversity in knowledge types
        diverse_results = self._ensure_knowledge_diversity(ranked_results)
        
        # Truncate to fit within token limits
        final_results = self._truncate_to_token_limit(diverse_results)
        
        return final_results
    
    def _apply_intent_based_filtering(
        self, 
        results: List[Dict[str, Any]], 
        query_intent: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply filtering based on query intent."""
        
        # Boost scores for results matching query parameters
        parameters = query_intent.get("parameters", {})
        
        for result in results:
            metadata = result.get("metadata", {})
            content = result.get("content", "").lower()
            
            # Boost for parameter matches
            score_boost = 0
            for param, value in parameters.items():
                if isinstance(value, str) and value.lower() in content:
                    score_boost += 0.1
                elif param in content:
                    score_boost += 0.05
            
            # Boost for importance level
            importance = metadata.get("importance", "medium")
            if importance == "high":
                score_boost += 0.1
            elif importance == "low":
                score_boost -= 0.05
            
            # Apply boost
            result["relevance_score"] = min(1.0, result.get("relevance_score", 0) + score_boost)
        
        # Re-sort with boosted scores
        return sorted(results, key=lambda x: x["relevance_score"], reverse=True)
    
    def _ensure_knowledge_diversity(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ensure diversity in knowledge types and sources."""
        
        diverse_results = []
        collection_counts = {}
        
        for result in results:
            collection = result.get("collection", "unknown")
            current_count = collection_counts.get(collection, 0)
            
            # Limit results per collection to ensure diversity
            max_per_collection = 3
            if current_count < max_per_collection:
                diverse_results.append(result)
                collection_counts[collection] = current_count + 1
            
            # Stop if we have enough diverse results
            if len(diverse_results) >= self.max_knowledge_chunks:
                break
        
        return diverse_results
    
    def _truncate_to_token_limit(
        self, 
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Truncate results to fit within token limits."""
        
        # Rough estimation: 4 characters per token
        chars_per_token = 4
        max_chars = self.max_context_tokens * chars_per_token
        
        truncated_results = []
        current_chars = 0
        
        for result in results:
            content = result.get("content", "")
            content_chars = len(content)
            
            if current_chars + content_chars <= max_chars:
                truncated_results.append(result)
                current_chars += content_chars
            else:
                # Try to include partial content if possible
                remaining_chars = max_chars - current_chars
                if remaining_chars > 200:  # Only if significant content can fit
                    truncated_content = content[:remaining_chars-3] + "..."
                    truncated_result = result.copy()
                    truncated_result["content"] = truncated_content
                    truncated_result["truncated"] = True
                    truncated_results.append(truncated_result)
                break
        
        return truncated_results
    
    def _analyze_conversation_context(
        self, 
        conversation_history: Optional[List[Dict[str, str]]], 
        current_query: str
    ) -> Dict[str, Any]:
        """Analyze conversation history for context clues."""
        
        if not conversation_history:
            return {"has_context": False}
        
        context_analysis = {
            "has_context": True,
            "conversation_length": len(conversation_history),
            "recent_topics": [],
            "context_queries": [],
            "temporal_references": False
        }
        
        # Analyze recent messages for context
        recent_messages = conversation_history[-3:]  # Last 3 exchanges
        
        for message in recent_messages:
            content = message.get("content", "").lower()
            
            # Extract topics mentioned
            oceanographic_terms = [
                "temperature", "salinity", "density", "mixed layer", 
                "thermocline", "argo", "float", "profile", "depth",
                "ocean", "pacific", "atlantic", "southern", "arctic"
            ]
            
            found_terms = [term for term in oceanographic_terms if term in content]
            context_analysis["recent_topics"].extend(found_terms)
            
            # Check for temporal references
            if any(word in content for word in ["recent", "lately", "now", "current", "today", "yesterday"]):
                context_analysis["temporal_references"] = True
            
            # Store context queries
            if message.get("role") == "user":
                context_analysis["context_queries"].append(content)
        
        # Remove duplicates and limit topics
        context_analysis["recent_topics"] = list(set(context_analysis["recent_topics"]))[:5]
        
        return context_analysis
    
    def _get_domain_specific_context(self, query_intent: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Get domain-specific context based on query intent."""
        
        domain_context = {
            "oceanography_domain": True,
            "data_type": "observational",
            "spatial_scope": "global",
            "temporal_scope": "multi-year"
        }
        
        if not query_intent:
            return domain_context
        
        # Update based on parsed intent
        parameters = query_intent.get("parameters", {})
        
        # Set spatial scope
        if parameters.get("location"):
            domain_context["spatial_scope"] = "regional"
            domain_context["region"] = parameters["location"]
        
        # Set temporal scope
        time_range = parameters.get("time_range", {})
        if time_range:
            if "recent" in str(time_range):
                domain_context["temporal_scope"] = "recent"
            elif "year" in str(time_range):
                domain_context["temporal_scope"] = "annual"
        
        # Set measurement context
        measurement = parameters.get("measurement", "")
        if measurement:
            domain_context["primary_measurement"] = measurement
            domain_context["measurement_category"] = self._categorize_measurement(measurement)
        
        return domain_context
    
    def _categorize_measurement(self, measurement: str) -> str:
        """Categorize measurement type."""
        
        measurement_categories = {
            "temperature": "physical",
            "salinity": "physical", 
            "density": "physical",
            "pressure": "physical",
            "oxygen": "chemical",
            "chlorophyll": "biological",
            "ph": "chemical",
            "nitrate": "chemical"
        }
        
        measurement_lower = measurement.lower()
        for key, category in measurement_categories.items():
            if key in measurement_lower:
                return category
        
        return "physical"  # Default
    
    def _assemble_context_package(
        self,
        user_query: str,
        knowledge_context: List[Dict[str, Any]],
        conversation_context: Dict[str, Any],
        domain_context: Dict[str, Any],
        query_intent: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Assemble comprehensive context package for LLM."""
        
        # Create structured context
        context_package = {
            "original_query": user_query,
            "knowledge_context": knowledge_context,
            "conversation_context": conversation_context,
            "domain_context": domain_context,
            "query_intent": query_intent or {},
            "context_summary": self._generate_context_summary(knowledge_context),
            "enhancement_status": "success",
            "context_metadata": {
                "knowledge_chunks": len(knowledge_context),
                "relevance_scores": [k.get("relevance_score", 0) for k in knowledge_context],
                "knowledge_collections": list(set(k.get("collection", "") for k in knowledge_context)),
                "timestamp": datetime.now().isoformat()
            }
        }
        
        return context_package
    
    def _generate_context_summary(self, knowledge_context: List[Dict[str, Any]]) -> str:
        """Generate a summary of retrieved context."""
        
        if not knowledge_context:
            return "No relevant knowledge found"
        
        # Collect topics and collections
        topics = set()
        collections = set()
        
        for item in knowledge_context:
            metadata = item.get("metadata", {})
            topics.add(metadata.get("topic", "general"))
            collections.add(item.get("collection", "unknown"))
        
        # Generate summary
        summary_parts = [
            f"Retrieved {len(knowledge_context)} relevant knowledge items",
            f"Topics: {', '.join(list(topics)[:3])}",
            f"Sources: {', '.join(collections)}"
        ]
        
        return " | ".join(summary_parts)
    
    def get_rag_statistics(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        
        knowledge_stats = self.knowledge_manager.get_knowledge_stats()
        vector_stats = self.vector_store.get_collection_stats()
        
        return {
            "knowledge_base": knowledge_stats,
            "vector_store": vector_stats,
            "configuration": {
                "max_context_tokens": self.max_context_tokens,
                "relevance_threshold": self.relevance_threshold,
                "max_knowledge_chunks": self.max_knowledge_chunks
            },
            "last_updated": datetime.now().isoformat()
        }


def create_rag_orchestrator(
    vector_store: VectorStoreService, 
    knowledge_manager: KnowledgeManager
) -> RAGOrchestrator:
    """Factory function to create RAG orchestrator."""
    return RAGOrchestrator(vector_store, knowledge_manager)