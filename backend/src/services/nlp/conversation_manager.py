"""
Context-aware conversation manager for multi-turn oceanographic data queries.
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

from .models import QueryIntent, ConversationContext, Parameter, GeographicRegion, TimeRange

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation context and multi-turn dialogues."""
    
    def __init__(self, context_ttl_minutes: int = 30):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # In-memory storage for conversation contexts
        # In production, this would be backed by Redis or a database
        self.contexts: Dict[str, ConversationContext] = {}
        
        # Context time-to-live
        self.context_ttl = timedelta(minutes=context_ttl_minutes)
        
        # Conversation statistics
        self.stats = defaultdict(int)
        
    def get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Get existing context or create new one."""
        
        # Clean expired contexts first
        self._cleanup_expired_contexts()
        
        if conversation_id in self.contexts:
            context = self.contexts[conversation_id]
            
            # Check if context is expired
            if datetime.utcnow() - context.updated_at > self.context_ttl:
                self.logger.info(f"Context {conversation_id} expired, creating new one")
                del self.contexts[conversation_id]
                return self._create_new_context(conversation_id)
            
            return context
        
        return self._create_new_context(conversation_id)
    
    def update_context(self, conversation_id: str, new_intent: QueryIntent) -> ConversationContext:
        """Update conversation context with new query intent."""
        
        context = self.get_or_create_context(conversation_id)
        context.update_context(new_intent)
        
        # Update statistics
        self.stats['total_turns'] += 1
        self.stats['active_conversations'] = len(self.contexts)
        
        self.logger.debug(f"Updated context for {conversation_id}, turns: {len(context.previous_intents)}")
        
        return context
    
    def apply_context_to_intent(self, conversation_id: str, intent: QueryIntent) -> QueryIntent:
        """Apply conversation context to enhance current intent."""
        
        context = self.get_or_create_context(conversation_id)
        
        if not context.previous_intents:
            return intent  # No previous context to apply
        
        # Apply context from previous turns
        enhanced_intent = self._enhance_with_context(intent, context)
        
        # Update context with the enhanced intent
        self.update_context(conversation_id, enhanced_intent)
        
        return enhanced_intent
    
    def _create_new_context(self, conversation_id: str) -> ConversationContext:
        """Create a new conversation context."""
        
        context = ConversationContext(conversation_id=conversation_id)
        self.contexts[conversation_id] = context
        
        self.stats['conversations_created'] += 1
        
        self.logger.info(f"Created new conversation context: {conversation_id}")
        return context
    
    def _enhance_with_context(self, intent: QueryIntent, context: ConversationContext) -> QueryIntent:
        """Enhance current intent with conversation context."""
        
        # Track what we're inheriting from context
        inherited = []
        
        # Inherit parameters if current query doesn't specify any
        if not intent.parameters and context.last_parameters:
            intent.parameters = context.last_parameters.copy()
            inherited.append(f"parameters: {[p.value for p in intent.parameters]}")
        
        # Inherit geographic region if not specified
        if not intent.geographic_region and not intent.geographic_bounds and context.last_region:
            intent.geographic_region = context.last_region
            inherited.append(f"region: {context.last_region.value}")
        
        # Inherit time range if not specified
        if not intent.time_range and context.last_time_range:
            intent.time_range = context.last_time_range
            inherited.append(f"time_range: {context.last_time_range.start_date} to {context.last_time_range.end_date}")
        
        # Inherit float IDs for follow-up queries
        if not intent.float_ids and context.last_float_ids:
            # Only inherit if the query seems related to specific floats
            if self._is_float_related_query(intent):
                intent.float_ids = context.last_float_ids.copy()
                inherited.append(f"float_ids: {intent.float_ids}")
        
        # Handle follow-up query patterns
        self._handle_followup_patterns(intent, context)
        
        # Add context information to entities
        if inherited:
            intent.entities["inherited_context"] = inherited
            intent.entities["context_applied"] = True
            
            self.logger.debug(f"Applied context: {inherited}")
        
        return intent
    
    def _is_float_related_query(self, intent: QueryIntent) -> bool:
        """Check if query is related to specific floats."""
        
        # Keywords that suggest the user wants to continue with same floats
        float_keywords = [
            "same", "those", "these", "that", "this", "continue", "also", "additionally"
        ]
        
        query_lower = intent.original_query.lower()
        return any(keyword in query_lower for keyword in float_keywords)
    
    def _handle_followup_patterns(self, intent: QueryIntent, context: ConversationContext):
        """Handle common follow-up query patterns."""
        
        query_lower = intent.original_query.lower()
        
        # Pattern: "What about salinity?" after temperature query
        if query_lower.startswith("what about") or "what about" in query_lower:
            # If no parameters extracted but we have previous parameters,
            # this might be asking about a different parameter
            if not intent.parameters and context.last_parameters:
                # Try to extract new parameter from the "what about X" phrase
                parameter_keywords = {
                    Parameter.SALINITY: ["salinity", "salt"],
                    Parameter.OXYGEN: ["oxygen", "o2", "dissolved oxygen"],
                    Parameter.PRESSURE: ["pressure", "depth"],
                    Parameter.TEMPERATURE: ["temperature", "temp"]
                }
                
                for param, keywords in parameter_keywords.items():
                    if any(keyword in query_lower for keyword in keywords):
                        intent.parameters = [param]
                        intent.entities["followup_parameter_detected"] = param.value
                        break
        
        # Pattern: "Show me a map" after data query
        elif any(phrase in query_lower for phrase in ["show me a", "display", "visualize"]):
            if any(viz in query_lower for viz in ["map", "plot", "chart", "graph"]):
                intent.query_type = intent.query_type or "visualization"
                intent.entities["followup_visualization"] = True
        
        # Pattern: "More details" or "Tell me more"
        elif any(phrase in query_lower for phrase in ["more details", "tell me more", "elaborate", "expand"]):
            if context.previous_intents:
                last_intent = context.previous_intents[-1]
                # Enhance the query to get more detailed information
                if hasattr(last_intent, 'query_type'):
                    intent.entities["followup_details_requested"] = True
        
        # Pattern: "Compare with [region/parameter]"
        elif "compare" in query_lower or "versus" in query_lower or " vs " in query_lower:
            intent.query_type = "comparison"
            intent.entities["followup_comparison"] = True
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """Get conversation history for RAG context analysis."""
        
        context = self.get_or_create_context(conversation_id)
        history = []
        
        for intent in context.previous_intents:
            # Convert intent to conversation message format
            history.append({
                "role": "user",
                "content": intent.original_query,
                "timestamp": context.updated_at.isoformat() if hasattr(context, 'updated_at') else None
            })
            
            # Add a mock assistant response for context
            history.append({
                "role": "assistant", 
                "content": f"Processed {intent.query_type.value} query for {intent.parameters}",
                "timestamp": context.updated_at.isoformat() if hasattr(context, 'updated_at') else None
            })
        
        return history
    
    def _cleanup_expired_contexts(self):
        """Remove expired conversation contexts."""
        
        current_time = datetime.utcnow()
        expired_contexts = []
        
        for conv_id, context in self.contexts.items():
            if current_time - context.updated_at > self.context_ttl:
                expired_contexts.append(conv_id)
        
        for conv_id in expired_contexts:
            del self.contexts[conv_id]
            self.stats['contexts_expired'] += 1
        
        if expired_contexts:
            self.logger.info(f"Cleaned up {len(expired_contexts)} expired contexts")
    
    def get_conversation_summary(self, conversation_id: str) -> Dict[str, Any]:
        """Get summary of conversation context."""
        
        if conversation_id not in self.contexts:
            return {"error": "Conversation not found"}
        
        context = self.contexts[conversation_id]
        
        return {
            "conversation_id": conversation_id,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat(),
            "total_turns": len(context.previous_intents),
            "last_parameters": [p.value for p in context.last_parameters] if context.last_parameters else [],
            "last_region": context.last_region.value if context.last_region else None,
            "last_time_range": {
                "start": context.last_time_range.start_date.isoformat() if context.last_time_range and context.last_time_range.start_date else None,
                "end": context.last_time_range.end_date.isoformat() if context.last_time_range and context.last_time_range.end_date else None
            } if context.last_time_range else None,
            "last_float_ids": context.last_float_ids,
            "recent_query_types": [intent.query_type.value for intent in context.previous_intents[-5:]]  # Last 5 query types
        }
    
    def get_context_suggestions(self, conversation_id: str) -> List[str]:
        """Get suggestions for next queries based on conversation context."""
        
        if conversation_id not in self.contexts:
            return []
        
        context = self.contexts[conversation_id]
        suggestions = []
        
        if not context.previous_intents:
            return suggestions
        
        last_intent = context.previous_intents[-1]
        
        # Suggest based on last query type
        if last_intent.query_type.value == "statistics":
            if context.last_parameters:
                param_name = context.last_parameters[0].value
                suggestions.extend([
                    f"Show me a plot of {param_name} data",
                    f"What about salinity in the same region?",
                    f"Compare {param_name} between different regions"
                ])
        
        elif last_intent.query_type.value == "floats":
            if context.last_float_ids:
                suggestions.extend([
                    "Show me profiles from these floats",
                    "What temperature data do these floats have?",
                    "Display these floats on a map"
                ])
        
        elif last_intent.query_type.value == "profiles":
            suggestions.extend([
                "Show me measurements from these profiles",
                "Plot temperature vs depth for these profiles",
                "What's the data quality like?"
            ])
        
        # Suggest based on available context
        if context.last_region:
            region_name = context.last_region.value.replace('_', ' ').title()
            suggestions.append(f"What's the data coverage in {region_name}?")
        
        if context.last_time_range:
            suggestions.append("What about data from a different time period?")
        
        # Remove duplicates and limit suggestions
        suggestions = list(set(suggestions))[:5]
        
        return suggestions
    
    def clear_context(self, conversation_id: str) -> bool:
        """Clear specific conversation context."""
        
        if conversation_id in self.contexts:
            del self.contexts[conversation_id]
            self.logger.info(f"Cleared context for conversation {conversation_id}")
            return True
        
        return False
    
    def clear_all_contexts(self):
        """Clear all conversation contexts."""
        
        count = len(self.contexts)
        self.contexts.clear()
        self.stats['contexts_cleared'] += count
        
        self.logger.info(f"Cleared all {count} conversation contexts")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation manager statistics."""
        
        active_contexts = len(self.contexts)
        
        # Calculate average turns per conversation
        total_turns = sum(len(ctx.previous_intents) for ctx in self.contexts.values())
        avg_turns = total_turns / active_contexts if active_contexts > 0 else 0
        
        return {
            "active_conversations": active_contexts,
            "total_turns_handled": self.stats['total_turns'],
            "conversations_created": self.stats['conversations_created'],
            "contexts_expired": self.stats['contexts_expired'],
            "contexts_cleared": self.stats.get('contexts_cleared', 0),
            "average_turns_per_conversation": round(avg_turns, 2),
            "context_ttl_minutes": self.context_ttl.total_seconds() / 60
        }


def create_conversation_manager(context_ttl_minutes: int = 30) -> ConversationManager:
    """Factory function to create a conversation manager instance."""
    return ConversationManager(context_ttl_minutes=context_ttl_minutes)