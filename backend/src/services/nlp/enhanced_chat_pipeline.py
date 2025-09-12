"""
Enhanced AI Chat Pipeline for OceanQuery - integrates all NLP components.
"""

import logging
import time
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from .query_parser import QueryParser
from .sql_generator import SQLGenerator
from .conversation_manager import ConversationManager
from .models import QueryIntent, QueryType, Parameter
from ..rag import initialize_rag_system, RAGOrchestrator, KnowledgeManager, VectorStoreService
from core.config import settings

logger = logging.getLogger(__name__)


class EnhancedChatPipeline:
    """Enhanced AI-powered chat pipeline for natural language ocean data queries with RAG support."""
    
    def __init__(self, db_session_factory=None, enable_rag: bool = True):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize NLP components
        self.query_parser = QueryParser()
        self.sql_generator = SQLGenerator()
        self.conversation_manager = ConversationManager(context_ttl_minutes=30)
        
        # Database session factory
        self.db_session_factory = db_session_factory
        
        # Initialize RAG system
        self.enable_rag = enable_rag
        self.rag_system = None
        if enable_rag:
            try:
                self.vector_store, self.knowledge_manager, self.rag_orchestrator = initialize_rag_system()
                self.rag_system = self.rag_orchestrator
                
                # Load knowledge base if configured
                if settings.auto_load_knowledge:
                    load_results = self.knowledge_manager.load_oceanographic_knowledge()
                    successful_loads = sum(1 for success in load_results.values() if success)
                    self.logger.info(f"RAG system initialized with knowledge in {successful_loads}/{len(load_results)} collections")
                else:
                    self.logger.info("RAG system initialized without knowledge auto-loading")
                    
            except Exception as e:
                self.logger.warning(f"Failed to initialize RAG system: {e}. Continuing without RAG support.")
                self.enable_rag = False
                self.rag_system = None
        
        # Pipeline statistics
        self.stats = {
            'queries_processed': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'total_processing_time': 0.0,
            'average_confidence': 0.0,
            'rag_enhanced_queries': 0,
            'knowledge_chunks_used': 0
        }
        
        self.logger.info("Enhanced Chat Pipeline initialized")
    
    async def process_query(
        self, 
        user_query: str, 
        conversation_id: Optional[str] = None,
        include_sql: bool = True,
        max_results: int = 100,
        db_session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query through the enhanced AI pipeline.
        
        Args:
            user_query: Natural language query from user
            conversation_id: Optional conversation ID for context
            include_sql: Whether to include generated SQL in response
            max_results: Maximum number of results to return
            db_session: Optional database session
            
        Returns:
            Enhanced chat response with data, visualizations, and context
        """
        start_time = time.time()
        self.stats['queries_processed'] += 1
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"conv_{int(time.time())}"
        
        try:
            self.logger.info(f"Processing query: '{user_query}' (conversation: {conversation_id})")
            
            # Step 1: Parse natural language query
            intent = self.query_parser.parse_query(user_query)
            
            # Step 2: Get conversation history for RAG context
            conversation_history = self.conversation_manager.get_conversation_history(conversation_id)
            
            # Step 3: Enhance with RAG context (if enabled)
            rag_context = None
            if self.enable_rag and self.rag_system:
                try:
                    rag_context = self.rag_system.enhance_query_with_context(
                        user_query=user_query,
                        conversation_history=conversation_history,
                        query_intent={
                            "intent_type": intent.query_type.value,
                            "parameters": {p.name: p.value for p in intent.parameters} if intent.parameters else {},
                            "confidence": intent.confidence
                        }
                    )
                    if rag_context and rag_context.get('enhancement_status') == 'success':
                        self.stats['rag_enhanced_queries'] += 1
                        self.stats['knowledge_chunks_used'] += len(rag_context.get('knowledge_context', []))
                        self.logger.debug(f"RAG enhanced query with {len(rag_context.get('knowledge_context', []))} knowledge chunks")
                except Exception as e:
                    self.logger.warning(f"RAG enhancement failed: {e}")
                    rag_context = None
            
            # Step 4: Apply conversation context
            enhanced_intent = self.conversation_manager.apply_context_to_intent(
                conversation_id, intent
            )
            
            # Step 5: Generate SQL query
            sql_result = self.sql_generator.generate_sql(enhanced_intent, limit=max_results)
            
            # Step 6: Execute query and get data
            query_data = await self._execute_sql_query(sql_result, db_session)
            
            # Step 7: Generate enhanced response with RAG context
            response = await self._generate_response(
                enhanced_intent, sql_result, query_data, conversation_id, include_sql, rag_context, user_query
            )
            
            # Step 8: Update statistics
            processing_time = time.time() - start_time
            self._update_stats(enhanced_intent.confidence, processing_time, success=True)
            
            response['processing_time_ms'] = processing_time * 1000
            response['conversation_id'] = conversation_id
            
            self.logger.info(f"Query processed successfully in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_stats(0.0, processing_time, success=False)
            
            self.logger.error(f"Error processing query: {e}", exc_info=True)
            
            return {
                'message': f"I encountered an error while processing your query: {str(e)}\\n\\nPlease try rephrasing your question or ask for help.",
                'sql_query': None,
                'data': {'error': str(e)},
                'conversation_id': conversation_id,
                'processing_time_ms': processing_time * 1000,
                'success': False
            }
    
    async def _execute_sql_query(
        self, 
        sql_result: Dict[str, Any], 
        db_session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Execute the generated SQL query and return results."""
        
        if 'error' in sql_result:
            return {'error': sql_result['error'], 'results': []}
        
        sql_query = sql_result.get('sql')
        parameters = sql_result.get('parameters', {})
        
        if not sql_query:
            return {'error': 'No SQL query generated', 'results': []}
        
        # Validate SQL safety
        if not self.sql_generator.validate_sql_safety(sql_query):
            return {'error': 'SQL query failed safety validation', 'results': []}
        
        try:
            # Use provided session or create new one
            if db_session:
                session = db_session
                should_close = False
            elif self.db_session_factory:
                session = self.db_session_factory()
                should_close = True
            else:
                return {'error': 'No database session available', 'results': []}
            
            try:
                # Execute query
                self.logger.debug(f"Executing SQL: {sql_query[:200]}...")
                result = session.execute(text(sql_query), parameters)
                
                # Fetch results
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = list(result.keys())
                    
                    # Convert rows to dictionaries
                    results = []
                    for row in rows:
                        row_dict = {}
                        for i, column in enumerate(columns):
                            value = row[i]
                            # Convert datetime objects to ISO strings
                            if isinstance(value, datetime):
                                value = value.isoformat()
                            row_dict[column] = value
                        results.append(row_dict)
                    
                    return {
                        'results': results,
                        'row_count': len(results),
                        'columns': columns
                    }
                else:
                    return {'results': [], 'row_count': 0, 'columns': []}
                    
            finally:
                if should_close:
                    session.close()
                    
        except Exception as e:
            self.logger.error(f"Database query execution error: {e}")
            return {'error': f'Database error: {str(e)}', 'results': []}
    
    async def _generate_response(
        self,
        intent: QueryIntent,
        sql_result: Dict[str, Any],
        query_data: Dict[str, Any],
        conversation_id: str,
        include_sql: bool,
        rag_context: Optional[Dict[str, Any]] = None,
        user_query: str = ""
    ) -> Dict[str, Any]:
        """Generate enhanced response based on query results with RAG context."""
        
        response = {
            'message': '',
            'sql_query': sql_result.get('sql') if include_sql else None,
            'data': {},
            'visualizations': [],
            'suggestions': [],
            'context_info': {},
            'success': True
        }
        
        # Handle errors
        if 'error' in query_data:
            response['message'] = f"❌ **Query Error**: {query_data['error']}\\n\\nPlease try a different query or ask for help."
            response['success'] = False
            return response
        
        # Get results
        results = query_data.get('results', [])
        row_count = query_data.get('row_count', 0)
        
        # Generate response based on query type
        if intent.query_type == QueryType.STATISTICS:
            response = await self._generate_statistics_response(intent, results, response)
        elif intent.query_type == QueryType.FLOATS:
            response = await self._generate_floats_response(intent, results, response)
        elif intent.query_type == QueryType.PROFILES:
            response = await self._generate_profiles_response(intent, results, response)
        elif intent.query_type == QueryType.MEASUREMENTS:
            response = await self._generate_measurements_response(intent, results, response)
        elif intent.query_type == QueryType.COMPARISON:
            response = await self._generate_comparison_response(intent, results, response)
        elif intent.query_type == QueryType.VISUALIZATION:
            response = await self._generate_visualization_response(intent, results, response)
        else:
            response = await self._generate_default_response(intent, results, response)
        
        # Add context information including RAG context
        response['context_info'] = {
            'confidence': intent.confidence,
            'query_type': intent.query_type.value,
            'parameters': [p.value for p in intent.parameters] if intent.parameters else [],
            'applied_context': intent.entities.get('context_applied', False),
            'inherited_context': intent.entities.get('inherited_context', []),
            'rag_enhanced': rag_context is not None and rag_context.get('enhancement_status') == 'success',
            'knowledge_context_summary': rag_context.get('context_summary') if rag_context else None
        }
        
        # Add suggestions for next queries
        response['suggestions'] = self.conversation_manager.get_context_suggestions(conversation_id)
        
        # Add row count information
        if row_count > 0:
            response['data']['row_count'] = row_count
            response['data']['results_summary'] = f"Found {row_count:,} results"
        
        # Always try to enhance with knowledge - either RAG or fallback
        if rag_context and rag_context.get('enhancement_status') == 'success':
            response = await self._enhance_response_with_rag_context(response, rag_context, user_query)
        
        # Always apply fallback knowledge for key oceanographic terms
        response = self._add_fallback_knowledge(response, user_query)
        
        return response
    
    async def _enhance_response_with_rag_context(
        self, 
        response: Dict[str, Any], 
        rag_context: Dict[str, Any],
        user_query: str = ""
    ) -> Dict[str, Any]:
        """Enhance response with relevant knowledge from RAG context."""
        
        knowledge_context = rag_context.get('knowledge_context', [])
        if not knowledge_context:
            return response
        
        # Always try to enhance with the best available knowledge
        insights = []
        
        # Get the best knowledge items (sorted by relevance)
        sorted_knowledge = sorted(knowledge_context, 
                                key=lambda x: x.get('relevance_score', 0), 
                                reverse=True)
        
        for knowledge_item in sorted_knowledge[:2]:  # Top 2 most relevant
            content = knowledge_item.get('content', '')
            relevance = knowledge_item.get('relevance_score', 0)
            metadata = knowledge_item.get('metadata', {})
            topic = metadata.get('topic', 'Ocean Science')
            
            # Very lenient threshold - capture more knowledge
            if relevance > 0.1 and len(content.strip()) > 30:
                # Clean up and format the content
                if len(content) > 250:
                    # Find a good breaking point
                    truncated = content[:250]
                    last_sentence = truncated.rfind('.')
                    if last_sentence > 100:
                        insight = truncated[:last_sentence + 1]
                    else:
                        insight = truncated + "..."
                else:
                    insight = content
                
                # Format topic name nicely
                formatted_topic = topic.replace('_', ' ').title()
                insights.append(f"🔍 **{formatted_topic}**: {insight}")
        
        # If we have insights, add them prominently to the response
        if insights:
            # Add knowledge section at the start of the message for better visibility
            original_message = response['message']
            knowledge_section = "🌊 **Enhanced with Ocean Knowledge:**\n\n" + "\n\n".join(insights)
            response['message'] = knowledge_section + "\n\n---\n\n" + original_message
        else:
            # Fallback: Add basic knowledge for key oceanographic terms
            response = self._add_fallback_knowledge(response, user_query)
            
            # Add knowledge metadata
            if 'data' not in response:
                response['data'] = {}
            response['data']['knowledge_insights'] = [
                {
                    'topic': item.get('metadata', {}).get('topic', 'general'),
                    'content': item.get('content', ''),
                    'relevance': item.get('relevance_score', 0),
                    'collection': item.get('collection', 'unknown')
                }
                for item in knowledge_context
            ]
        
        return response
    
    def _add_fallback_knowledge(self, response: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Add fallback knowledge for key oceanographic terms when RAG retrieval fails."""
        
        # Analyze user query for key terms
        query_lower = user_query.lower()
        
        # Step 1: Classify query intent for prioritized matching
        query_intent = self._classify_query_intent(query_lower)
        
        # Step 2: Select knowledge based on query intent
        knowledge_by_intent = {
            'ai_technology': [
                "🔍 **AI in Ocean Research**: Artificial Intelligence analyzes massive oceanographic datasets, identifies patterns in climate data, predicts ocean behavior, processes satellite imagery, and enables autonomous underwater vehicles for deep-sea exploration.",
                "🔍 **ML in Oceanography**: Neural networks analyze complex ocean patterns, classify water masses, predict El Niño events, process acoustic data from marine life, and improve climate model accuracy.",
                "🔍 **Ocean Automation**: Autonomous systems like ARGO floats, underwater gliders, and robotic submarines collect data 24/7, enabling continuous ocean monitoring without human intervention in remote areas."
            ],
            'argo_technology': [
                "🔍 **ARGO Floats**: Autonomous robotic instruments that drift with ocean currents, diving to 2000m every 10 days to measure temperature, salinity, and pressure profiles before surfacing to transmit data via satellite.",
                "🔍 **Ocean Sensors**: ARGO floats carry CTD sensors (Conductivity-Temperature-Depth) and often oxygen sensors. These instruments provide high-precision measurements essential for climate research."
            ],
            'ocean_processes': [
                "🔍 **Thermocline**: The ocean layer where temperature rapidly decreases with depth, typically found between 200-1000m, varying seasonally due to surface heating, wind mixing, and circulation patterns.",
                "🔍 **Ocean Currents**: Large-scale water movements driven by wind, density differences, and Earth's rotation. Transport heat, nutrients, and marine life across ocean basins, affecting global climate."
            ],
            'ocean_measurements': [
                "🔍 **Salinity**: Concentration of dissolved salts in seawater, measured in Practical Salinity Units (PSU), ranging globally from 32-37 PSU with an average of 35 PSU.",
                "🔍 **Ocean Temperature**: Measured using CTD sensors on ARGO floats, ranging from -2°C in polar waters to 30°C in tropical surface waters, with thermoclines creating distinct temperature layers.",
                "🔍 **Dissolved Oxygen**: Essential gas dissolved in seawater, vital for marine life. Measured in micromoles per kilogram (μmol/kg), varying from near-zero in oxygen minimum zones to over 300 μmol/kg in surface waters.",
                "🔍 **Ocean Density**: Determines water mass movement and stratification. Calculated from temperature, salinity, and pressure. Denser water sinks, driving global ocean circulation and mixing processes.",
                "🔍 **Ocean Pressure**: Increases by ~1 atmosphere every 10 meters of depth. ARGO floats measure pressure to determine their exact depth and calculate other oceanographic variables."
            ],
            'bgc_measurements': [
                "🔍 **BGC Floats**: Bio-Geo-Chemical floats measure chlorophyll-a, pH, nitrate, oxygen, and backscattering to study ocean productivity, carbon cycle, and marine ecosystem health across global oceans.",
                "🔍 **Chlorophyll-a**: Green pigment in phytoplankton measured by fluorescence sensors on BGC floats. Indicates ocean productivity and primary production, ranging from <0.1 mg/m³ in oligotrophic regions to >10 mg/m³ in productive areas.",
                "🔍 **Ocean pH**: Measures seawater acidity (typically 7.8-8.2). BGC floats detect ocean acidification caused by CO2 absorption, critical for understanding coral reef health and marine ecosystem impacts.",
                "🔍 **Nitrate**: Essential nutrient measured by BGC sensors using UV spectrophotometry. Concentrations range from near-zero in surface waters to 40+ μmol/kg in deep waters, controlling phytoplankton growth.",
                "🔍 **Backscattering**: Optical measurement of particle concentration in seawater. BGC floats measure backscattering at multiple wavelengths to estimate particle size distribution and marine snow formation."
            ],
            'general_oceanography': [
                "🔍 **Ocean Profiles**: Vertical measurements from surface to depth showing how temperature, salinity, and other properties change. ARGO floats create these profiles every 10 days across global oceans."
            ]
        }
        
        # Step 3: Get relevant knowledge based on classified intent
        added_knowledge = knowledge_by_intent.get(query_intent, [])
        
        # Step 4: Limit to top 2 most relevant items to avoid overwhelming
        added_knowledge = added_knowledge[:2]
        
        # Add fallback knowledge if any key terms were found
        if added_knowledge:
            original_msg = response['message']
            knowledge_section = "🌊 **Enhanced with Ocean Knowledge:**\n\n" + "\n\n".join(added_knowledge)
            response['message'] = knowledge_section + "\n\n---\n\n" + original_msg
            
            # Add metadata
            if 'data' not in response:
                response['data'] = {}
            response['data']['fallback_knowledge_used'] = True
        
        return response
    
    def _classify_query_intent(self, query_lower: str) -> str:
        """Classify query intent to prioritize correct knowledge matching."""
        
        # Priority 1: AI/Technology questions
        ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural network', 
                       'deep learning', 'automation', 'autonomous', 'robot', 'algorithm', 'help']
        if any(keyword in query_lower for keyword in ai_keywords):
            return 'ai_technology'
        
        # Priority 2: ARGO float technology
        argo_keywords = ['argo', 'float', 'sensor', 'ctd', 'autonomous', 'instrument']
        if any(keyword in query_lower for keyword in argo_keywords):
            return 'argo_technology'
        
        # Priority 3: Ocean processes/phenomena
        process_keywords = ['thermocline', 'circulation', 'current', 'mixing', 'stratification', 
                           'variation', 'cause', 'process', 'formation']
        if any(keyword in query_lower for keyword in process_keywords):
            return 'ocean_processes'
        
        # Priority 4: BGC measurements/biogeochemical parameters
        bgc_keywords = ['bgc', 'biogeochemical', 'bio-geo-chemical', 'chlorophyll', 'ph', 
                       'nitrate', 'backscattering', 'fluorescence', 'productivity', 'ecosystem']
        if any(keyword in query_lower for keyword in bgc_keywords):
            return 'bgc_measurements'
        
        # Priority 5: Ocean measurements/parameters
        measurement_keywords = ['salinity', 'temperature', 'oxygen', 'dissolved', 'density', 
                               'pressure', 'measurement', 'profile']
        if any(keyword in query_lower for keyword in measurement_keywords):
            return 'ocean_measurements'
        
        # Default: general oceanography
        return 'general_oceanography'
    
    async def _generate_statistics_response(
        self, 
        intent: QueryIntent, 
        results: List[Dict[str, Any]], 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate response for statistics queries."""
        
        if not results:
            response['message'] = "❌ No statistical data found for your query."
            return response
        
        stats = results[0] if results else {}
        
        # Build message based on available statistics
        message_parts = ["📊 **Ocean Data Statistics**\\n\\n"]
        
        if intent.parameters:
            param_name = intent.parameters[0].value
            param_display = param_name.replace('_', ' ').title()
            
            message_parts.append(f"🌊 **{param_display} Analysis:**\\n")
            
            for key, value in stats.items():
                if param_name in key and value is not None:
                    if 'count' in key:
                        message_parts.append(f"  • **Measurements**: {value:,}\\n")
                    elif 'avg' in key:
                        message_parts.append(f"  • **Average**: {value}\\n")
                    elif 'min' in key:
                        message_parts.append(f"  • **Minimum**: {value}\\n")
                    elif 'max' in key:
                        message_parts.append(f"  • **Maximum**: {value}\\n")
            
            # Add depth information if available
            if 'min_depth' in stats and 'max_depth' in stats:
                message_parts.append(f"\\n🌊 **Depth Range**: {stats['min_depth']}m to {stats['max_depth']}m\\n")
        
        else:
            # General statistics
            if 'total_floats' in stats:
                message_parts.append(f"🛟 **Total Floats**: {stats['total_floats']:,}\\n")
            if 'active_floats' in stats:
                message_parts.append(f"✅ **Active Floats**: {stats['active_floats']:,}\\n")
            if 'total_profiles' in stats:
                message_parts.append(f"📊 **Total Profiles**: {stats['total_profiles']:,}\\n")
            if 'total_measurements' in stats:
                message_parts.append(f"📈 **Total Measurements**: {stats['total_measurements']:,}\\n")
        
        message_parts.append("\\n*This data comes from real ARGO oceanographic floats!*")
        
        response['message'] = ''.join(message_parts)
        response['data'] = {'statistics': stats, 'chart_data': stats}
        
        # Suggest visualizations
        if intent.parameters:
            param_name = intent.parameters[0].value
            response['visualizations'] = [{
                'type': 'chart',
                'title': f'{param_name.title()} Statistics',
                'data': stats,
                'chart_type': 'bar'
            }]
        
        return response
    
    async def _generate_floats_response(
        self, 
        intent: QueryIntent, 
        results: List[Dict[str, Any]], 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate response for float queries."""
        
        if not results:
            response['message'] = "❌ No ARGO floats found matching your criteria."
            return response
        
        float_count = len(results)
        
        message_parts = [f"🛟 **Found {float_count:,} ARGO Float{'s' if float_count != 1 else ''}**\\n\\n"]
        
        # Show details for first few floats
        for i, float_data in enumerate(results[:3]):
            float_id = float_data.get('float_id', 'Unknown')
            institution = float_data.get('institution', 'Unknown')
            status = float_data.get('status', 'unknown')
            profiles = float_data.get('actual_profiles', 0)
            
            status_emoji = '✅' if status == 'active' else '⚠️'
            message_parts.append(f"{status_emoji} **Float {float_id}**\\n")
            message_parts.append(f"  • Institution: {institution}\\n")
            message_parts.append(f"  • Status: {status}\\n")
            message_parts.append(f"  • Profiles: {profiles:,}\\n")
            
            if float_data.get('last_latitude') and float_data.get('last_longitude'):
                lat, lon = float_data['last_latitude'], float_data['last_longitude']
                message_parts.append(f"  • Last Position: {lat:.2f}°N, {lon:.2f}°E\\n")
            
            message_parts.append("\\n")
        
        if float_count > 3:
            message_parts.append(f"*... and {float_count - 3} more floats*\\n\\n")
        
        message_parts.append("💡 **Try asking**: 'Show me profiles from these floats' or 'Display these on a map'")
        
        response['message'] = ''.join(message_parts)
        response['data'] = {'floats': results, 'float_count': float_count}
        
        # Suggest map visualization
        response['visualizations'] = [{
            'type': 'map',
            'title': 'ARGO Float Locations',
            'data': results,
            'map_type': 'scatter'
        }]
        
        return response
    
    async def _generate_profiles_response(
        self, 
        intent: QueryIntent, 
        results: List[Dict[str, Any]], 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate response for profile queries."""
        
        if not results:
            response['message'] = "❌ No ARGO profiles found matching your criteria."
            return response
        
        profile_count = len(results)
        
        message_parts = [f"📊 **Found {profile_count:,} ARGO Profile{'s' if profile_count != 1 else ''}**\\n\\n"]
        
        # Show details for first few profiles
        for i, profile_data in enumerate(results[:3]):
            profile_id = profile_data.get('profile_id', 'Unknown')
            float_id = profile_data.get('float_id', 'Unknown')
            date = profile_data.get('measurement_date', 'Unknown')
            data_points = profile_data.get('data_points', 0)
            
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date.replace('Z', '+00:00')).strftime('%Y-%m-%d')
                except:
                    pass
            
            message_parts.append(f"📈 **Profile {profile_id}**\\n")
            message_parts.append(f"  • Float: {float_id}\\n")
            message_parts.append(f"  • Date: {date}\\n")
            message_parts.append(f"  • Data Points: {data_points:,}\\n")
            
            if profile_data.get('latitude') and profile_data.get('longitude'):
                lat, lon = profile_data['latitude'], profile_data['longitude']
                message_parts.append(f"  • Location: {lat:.2f}°N, {lon:.2f}°E\\n")
            
            message_parts.append("\\n")
        
        if profile_count > 3:
            message_parts.append(f"*... and {profile_count - 3} more profiles*\\n\\n")
        
        message_parts.append("💡 **Try asking**: 'Show me measurements from these profiles' or 'Plot temperature profiles'")
        
        response['message'] = ''.join(message_parts)
        response['data'] = {'profiles': results, 'profile_count': profile_count}
        
        return response
    
    async def _generate_measurements_response(
        self, 
        intent: QueryIntent, 
        results: List[Dict[str, Any]], 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate response for measurement queries."""
        
        if not results:
            response['message'] = "❌ No measurements found matching your criteria."
            return response
        
        measurement_count = len(results)
        
        # Get parameter statistics
        if intent.parameters:
            param = intent.parameters[0].value
            values = [r.get(param) for r in results if r.get(param) is not None]
            
            if values:
                import statistics
                avg_val = statistics.mean(values)
                min_val = min(values)
                max_val = max(values)
                
                message_parts = [
                    f"📊 **{measurement_count:,} {param.title()} Measurements**\\n\\n",
                    f"📈 **Statistics:**\\n",
                    f"  • Average: {avg_val:.2f}\\n",
                    f"  • Range: {min_val:.2f} to {max_val:.2f}\\n",
                    f"  • Total Points: {len(values):,}\\n\\n"
                ]
            else:
                message_parts = [f"📊 **Found {measurement_count:,} measurement records**\\n\\n"]
        else:
            message_parts = [f"📊 **Found {measurement_count:,} measurement records**\\n\\n"]
        
        # Show sample data
        message_parts.append("🔍 **Sample Data:**\\n")
        for i, measurement in enumerate(results[:3]):
            depth = measurement.get('depth', measurement.get('pressure', 'N/A'))
            message_parts.append(f"  • Depth {depth}m: ")
            
            if intent.parameters:
                for param in intent.parameters:
                    value = measurement.get(param.value)
                    if value is not None:
                        message_parts.append(f"{param.value}={value:.2f} ")
            
            message_parts.append("\\n")
        
        if measurement_count > 3:
            message_parts.append(f"\\n*... and {measurement_count - 3} more measurements*")
        
        response['message'] = ''.join(message_parts)
        response['data'] = {'measurements': results, 'measurement_count': measurement_count}
        
        return response
    
    async def _generate_comparison_response(
        self, 
        intent: QueryIntent, 
        results: List[Dict[str, Any]], 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate response for comparison queries."""
        
        if not results:
            response['message'] = "❌ No data found for comparison."
            return response
        
        message_parts = ["🔄 **Data Comparison Results**\\n\\n"]
        
        # Handle different comparison types
        if len(results) >= 2:
            for result in results[:2]:
                if 'region' in result:
                    region = result.get('region', 'Unknown')
                    message_parts.append(f"📍 **{region.replace('_', ' ').title()}:**\\n")
                
                for key, value in result.items():
                    if key != 'region' and value is not None:
                        if isinstance(value, (int, float)):
                            message_parts.append(f"  • {key.replace('_', ' ').title()}: {value:,}\\n")
                
                message_parts.append("\\n")
        
        response['message'] = ''.join(message_parts)
        response['data'] = {'comparison_results': results}
        
        return response
    
    async def _generate_visualization_response(
        self, 
        intent: QueryIntent, 
        results: List[Dict[str, Any]], 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate response for visualization queries."""
        
        if not results:
            response['message'] = "❌ No data found for visualization."
            return response
        
        viz_type = intent.visualization_type or 'chart'
        
        message_parts = [f"📊 **{viz_type.title()} Visualization Ready**\\n\\n"]
        message_parts.append(f"Generated visualization with {len(results):,} data points.\\n\\n")
        
        if viz_type == 'map':
            message_parts.append("🗺️ Interactive map shows float locations and trajectories.")
        elif viz_type == 'plot':
            param = intent.parameters[0].value if intent.parameters else 'parameter'
            message_parts.append(f"📈 Depth profile plot for {param} measurements.")
        else:
            message_parts.append("📊 Time series chart showing data trends over time.")
        
        response['message'] = ''.join(message_parts)
        response['data'] = {'visualization_data': results}
        response['visualizations'] = [{
            'type': viz_type,
            'data': results,
            'parameter': intent.parameters[0].value if intent.parameters else None
        }]
        
        return response
    
    async def _generate_default_response(
        self, 
        intent: QueryIntent, 
        results: List[Dict[str, Any]], 
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate default response."""
        
        if not results:
            response['message'] = "❓ I couldn't find specific data for your query. Try asking about ARGO floats, temperature, salinity, or ocean profiles."
            return response
        
        result = results[0] if results else {}
        
        message_parts = ["🌊 **Ocean Data Summary**\\n\\n"]
        
        for key, value in result.items():
            if value is not None:
                if isinstance(value, (int, float)):
                    message_parts.append(f"• **{key.replace('_', ' ').title()}**: {value:,}\\n")
        
        response['message'] = ''.join(message_parts)
        response['data'] = {'summary': result}
        
        return response
    
    def _update_stats(self, confidence: float, processing_time: float, success: bool):
        """Update pipeline statistics."""
        
        if success:
            self.stats['successful_queries'] += 1
        else:
            self.stats['failed_queries'] += 1
        
        self.stats['total_processing_time'] += processing_time
        
        # Update average confidence (running average)
        total_queries = self.stats['successful_queries'] + self.stats['failed_queries']
        if total_queries > 0:
            self.stats['average_confidence'] = (
                (self.stats['average_confidence'] * (total_queries - 1) + confidence) / total_queries
            )
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline performance statistics including RAG metrics."""
        
        total_queries = self.stats['queries_processed']
        avg_processing_time = (
            self.stats['total_processing_time'] / total_queries 
            if total_queries > 0 else 0
        )
        
        success_rate = (
            self.stats['successful_queries'] / total_queries 
            if total_queries > 0 else 0
        )
        
        rag_enhancement_rate = (
            self.stats['rag_enhanced_queries'] / total_queries 
            if total_queries > 0 else 0
        )
        
        avg_knowledge_chunks = (
            self.stats['knowledge_chunks_used'] / self.stats['rag_enhanced_queries']
            if self.stats['rag_enhanced_queries'] > 0 else 0
        )
        
        base_stats = {
            'total_queries_processed': total_queries,
            'successful_queries': self.stats['successful_queries'],
            'failed_queries': self.stats['failed_queries'],
            'success_rate': round(success_rate * 100, 2),
            'average_processing_time_ms': round(avg_processing_time * 1000, 2),
            'average_confidence': round(self.stats['average_confidence'], 3),
            'conversation_stats': self.conversation_manager.get_statistics(),
            'rag_enabled': self.enable_rag,
            'rag_enhanced_queries': self.stats['rag_enhanced_queries'],
            'rag_enhancement_rate': round(rag_enhancement_rate * 100, 2),
            'total_knowledge_chunks_used': self.stats['knowledge_chunks_used'],
            'avg_knowledge_chunks_per_query': round(avg_knowledge_chunks, 1)
        }
        
        # Add RAG system statistics if available
        if self.enable_rag and self.rag_system:
            try:
                rag_stats = self.rag_system.get_rag_statistics()
                base_stats['rag_system_stats'] = rag_stats
            except Exception as e:
                self.logger.warning(f"Could not get RAG system stats: {e}")
        
        return base_stats


def create_enhanced_chat_pipeline(db_session_factory=None, enable_rag: bool = True) -> EnhancedChatPipeline:
    """Factory function to create an enhanced chat pipeline instance with RAG support."""
    return EnhancedChatPipeline(db_session_factory=db_session_factory, enable_rag=enable_rag)
