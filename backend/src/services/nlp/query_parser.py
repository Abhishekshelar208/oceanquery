"""
Advanced natural language query parser for ocean data queries.
"""

import re
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple, Set
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

from .models import (
    QueryIntent, QueryType, Parameter, AggregationType, 
    GeographicRegion, GeographicBounds, TimeRange, DepthRange,
    TemporalGranularity, ConversationContext,
    PARAMETER_ALIASES, AGGREGATION_ALIASES, REGION_ALIASES, REGION_BOUNDS
)

logger = logging.getLogger(__name__)


class QueryParser:
    """Advanced natural language query parser for oceanographic data."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Compile regex patterns for better performance
        self._compile_patterns()
        
        # Build reverse lookup dictionaries for faster alias matching
        self._build_aliases()
        
    def _compile_patterns(self):
        """Compile frequently used regex patterns."""
        
        # Numeric patterns
        self.number_pattern = re.compile(r'[-+]?\d*\.?\d+')
        self.coordinate_pattern = re.compile(r'([-+]?\d+(?:\.\d+)?)[°]?([ns]|north|south|east|west)?', re.IGNORECASE)
        
        # Date patterns
        self.date_patterns = [
            re.compile(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b'),  # YYYY-MM-DD
            re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b'),  # MM/DD/YYYY
            re.compile(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+(\d{4})\b', re.IGNORECASE),
            re.compile(r'\b(\d{4})\b')  # Just year
        ]
        
        # Relative time patterns
        self.relative_time_pattern = re.compile(
            r'\b(last|past|previous|recent|since|from|during|in)\s+(\d+)?\s*(year|month|week|day|decade)s?\b',
            re.IGNORECASE
        )
        
        # ID patterns
        self.float_id_pattern = re.compile(r'\b\d{7}\b')  # 7-digit float IDs
        self.profile_id_pattern = re.compile(r'\b\d+_\d+\b')  # profile_id format
        
        # Depth/pressure patterns
        self.depth_pattern = re.compile(
            r'\b(\d+(?:\.\d+)?)\s*(m|meter|metre|depth|deep|dbar|decibar|pressure)\b', 
            re.IGNORECASE
        )
        
        # Comparison patterns
        self.comparison_pattern = re.compile(
            r'\b(compare|versus|vs|against|between|and)\b',
            re.IGNORECASE
        )
        
        # Visualization patterns
        self.visualization_pattern = re.compile(
            r'\b(plot|chart|graph|map|visualize|show|display|draw)\b',
            re.IGNORECASE
        )
        
    def _build_aliases(self):
        """Build reverse lookup dictionaries for aliases."""
        
        # Parameter aliases
        self.parameter_lookup = {}
        for param, aliases in PARAMETER_ALIASES.items():
            for alias in aliases:
                self.parameter_lookup[alias.lower()] = param
                
        # Aggregation aliases
        self.aggregation_lookup = {}
        for agg, aliases in AGGREGATION_ALIASES.items():
            for alias in aliases:
                self.aggregation_lookup[alias.lower()] = agg
                
        # Region aliases
        self.region_lookup = {}
        for region, aliases in REGION_ALIASES.items():
            for alias in aliases:
                self.region_lookup[alias.lower()] = region
                
    def parse_query(self, query: str, context: Optional[ConversationContext] = None) -> QueryIntent:
        """
        Parse a natural language query into structured intent.
        
        Args:
            query: Natural language query string
            context: Optional conversation context for follow-up queries
            
        Returns:
            QueryIntent with parsed information
        """
        self.logger.info(f"Parsing query: '{query}'")
        
        # Normalize query
        normalized_query = self._normalize_query(query)
        
        # Create base intent
        intent = QueryIntent(
            query_type=QueryType.HELP,  # Default, will be overridden
            original_query=query,
            entities={}
        )
        
        # Extract entities
        self._extract_parameters(normalized_query, intent)
        self._extract_aggregations(normalized_query, intent)
        self._extract_geographic_info(normalized_query, intent)
        self._extract_temporal_info(normalized_query, intent)
        self._extract_depth_info(normalized_query, intent)
        self._extract_identifiers(normalized_query, intent)
        self._extract_output_preferences(normalized_query, intent)
        self._extract_comparisons(normalized_query, intent)
        
        # Determine query type
        self._determine_query_type(normalized_query, intent)
        
        # Apply context from previous conversations
        if context:
            self._apply_context(intent, context)
            
        # Calculate confidence score
        intent.confidence = self._calculate_confidence(intent, normalized_query)
        
        self.logger.info(f"Parsed intent: {intent.query_type.value}, confidence: {intent.confidence:.2f}")
        
        return intent
        
    def _normalize_query(self, query: str) -> str:
        """Normalize query text for parsing."""
        # Convert to lowercase
        normalized = query.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Handle common contractions and variations
        replacements = {
            "what's": "what is",
            "show me": "show",
            "give me": "show",
            "i want": "show",
            "can you": "",
            "please": "",
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
            
        return normalized.strip()
        
    def _extract_parameters(self, query: str, intent: QueryIntent):
        """Extract ocean parameters from query."""
        found_parameters = set()
        
        # Check each word/phrase against parameter aliases
        words = query.split()
        for i, word in enumerate(words):
            # Single word matching
            if word in self.parameter_lookup:
                found_parameters.add(self.parameter_lookup[word])
                intent.entities[f"parameter_{word}"] = self.parameter_lookup[word].value
                
            # Multi-word phrase matching
            for j in range(i + 1, min(i + 4, len(words))):  # Check up to 3-word phrases
                phrase = " ".join(words[i:j+1])
                if phrase in self.parameter_lookup:
                    found_parameters.add(self.parameter_lookup[phrase])
                    intent.entities[f"parameter_{phrase}"] = self.parameter_lookup[phrase].value
                    
        intent.parameters = list(found_parameters)
        
    def _extract_aggregations(self, query: str, intent: QueryIntent):
        """Extract aggregation types from query."""
        found_aggregations = set()
        
        words = query.split()
        for i, word in enumerate(words):
            if word in self.aggregation_lookup:
                found_aggregations.add(self.aggregation_lookup[word])
                intent.entities[f"aggregation_{word}"] = self.aggregation_lookup[word].value
                
            # Multi-word phrases
            for j in range(i + 1, min(i + 3, len(words))):
                phrase = " ".join(words[i:j+1])
                if phrase in self.aggregation_lookup:
                    found_aggregations.add(self.aggregation_lookup[phrase])
                    intent.entities[f"aggregation_{phrase}"] = self.aggregation_lookup[phrase].value
                    
        intent.aggregations = list(found_aggregations)
        
    def _extract_geographic_info(self, query: str, intent: QueryIntent):
        """Extract geographic information from query."""
        
        # Check for named regions
        for region, aliases in REGION_ALIASES.items():
            for alias in aliases:
                if alias in query:
                    intent.geographic_region = region
                    intent.geographic_bounds = REGION_BOUNDS.get(region)
                    intent.entities[f"region_{alias}"] = region.value
                    break
            if intent.geographic_region:
                break
                
        # Extract coordinate patterns
        coordinates = self.coordinate_pattern.findall(query)
        if coordinates and len(coordinates) >= 2:
            try:
                coords = []
                for coord_str, direction in coordinates[:4]:  # Max 4 coordinates for bounds
                    coord = float(coord_str)
                    if direction and direction.lower() in ['s', 'south', 'w', 'west']:
                        coord = -abs(coord)
                    coords.append(coord)
                    
                if len(coords) >= 2:
                    # Try to determine if these are lat/lon pairs or bounds
                    if len(coords) == 2:
                        # Single point - create small bounds around it
                        lat, lon = coords
                        intent.geographic_bounds = GeographicBounds(
                            lat - 1, lat + 1, lon - 1, lon + 1
                        )
                    elif len(coords) == 4:
                        # Four coordinates - assume min_lat, max_lat, min_lon, max_lon
                        intent.geographic_bounds = GeographicBounds(*coords)
                        
                intent.entities["coordinates"] = coords
                
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Error parsing coordinates: {e}")
                
    def _extract_temporal_info(self, query: str, intent: QueryIntent):
        """Extract temporal information from query."""
        
        # Look for relative time expressions
        relative_matches = self.relative_time_pattern.findall(query)
        if relative_matches:
            for prefix, number_str, unit in relative_matches:
                try:
                    number = int(number_str) if number_str else 1
                    end_date = date.today()
                    
                    if unit.startswith('year'):
                        start_date = end_date - relativedelta(years=number)
                    elif unit.startswith('month'):
                        start_date = end_date - relativedelta(months=number)
                    elif unit.startswith('week'):
                        start_date = end_date - timedelta(weeks=number)
                    elif unit.startswith('day'):
                        start_date = end_date - timedelta(days=number)
                    else:
                        continue
                        
                    intent.time_range = TimeRange(
                        start_date=start_date,
                        end_date=end_date,
                        relative_period=f"{prefix} {number_str or ''} {unit}".strip()
                    )
                    intent.entities[f"time_relative"] = intent.time_range.relative_period
                    break
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Error parsing relative time: {e}")
                    
        # Look for specific dates
        if not intent.time_range:
            dates_found = []
            
            for pattern in self.date_patterns:
                matches = pattern.findall(query)
                for match in matches:
                    try:
                        if len(match) == 3:  # Day/month/year or year/month/day
                            if len(match[0]) == 4:  # Year first
                                year, month, day = match
                            else:  # Month/day first
                                month, day, year = match
                            parsed_date = date(int(year), int(month), int(day))
                        elif len(match) == 2:  # Month and year
                            month_str, year = match
                            month_names = {
                                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                                'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                                'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                            }
                            month = month_names.get(month_str[:3].lower(), 1)
                            parsed_date = date(int(year), month, 1)
                        else:  # Just year
                            year = match[0] if isinstance(match, tuple) else match
                            parsed_date = date(int(year), 1, 1)
                            
                        dates_found.append(parsed_date)
                        
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Error parsing date {match}: {e}")
                        
            if dates_found:
                if len(dates_found) == 1:
                    # Single date - use as end date with start one year before
                    end_date = dates_found[0]
                    start_date = end_date - relativedelta(years=1)
                else:
                    # Multiple dates - use range
                    dates_found.sort()
                    start_date, end_date = dates_found[0], dates_found[-1]
                    
                intent.time_range = TimeRange(start_date=start_date, end_date=end_date)
                intent.entities["dates_found"] = [d.isoformat() for d in dates_found]
                
    def _extract_depth_info(self, query: str, intent: QueryIntent):
        """Extract depth/pressure information from query."""
        
        depth_matches = self.depth_pattern.findall(query)
        depths = []
        
        for value_str, unit in depth_matches:
            try:
                value = float(value_str)
                
                # Convert to consistent units (meters for depth, dbar for pressure)
                if unit.lower() in ['dbar', 'decibar', 'pressure']:
                    # Pressure value
                    if not depths or len(depths) == 1:
                        depths.append(('pressure', value))
                else:
                    # Depth value in meters
                    if not depths or len(depths) == 1:
                        depths.append(('depth', value))
                        
            except ValueError:
                continue
                
        if depths:
            if len(depths) == 1:
                depth_type, value = depths[0]
                if depth_type == 'depth':
                    intent.depth_range = DepthRange(min_depth=0, max_depth=value)
                else:
                    intent.depth_range = DepthRange(min_pressure=0, max_pressure=value)
            elif len(depths) == 2:
                # Two depth values - use as range
                type1, val1 = depths[0]
                type2, val2 = depths[1]
                if type1 == type2:
                    min_val, max_val = min(val1, val2), max(val1, val2)
                    if type1 == 'depth':
                        intent.depth_range = DepthRange(min_depth=min_val, max_depth=max_val)
                    else:
                        intent.depth_range = DepthRange(min_pressure=min_val, max_pressure=max_val)
                        
            intent.entities["depths"] = depths
            
    def _extract_identifiers(self, query: str, intent: QueryIntent):
        """Extract float and profile IDs from query."""
        
        # Extract float IDs (7 digits)
        float_ids = self.float_id_pattern.findall(query)
        intent.float_ids = list(set(float_ids))  # Remove duplicates
        
        # Extract profile IDs (format: number_number)
        profile_ids = self.profile_id_pattern.findall(query)
        intent.profile_ids = list(set(profile_ids))
        
        if intent.float_ids:
            intent.entities["float_ids"] = intent.float_ids
        if intent.profile_ids:
            intent.entities["profile_ids"] = intent.profile_ids
            
    def _extract_output_preferences(self, query: str, intent: QueryIntent):
        """Extract output format and visualization preferences."""
        
        # Check for visualization requests
        if self.visualization_pattern.search(query):
            # Determine visualization type
            if any(word in query for word in ['map', 'location', 'position']):
                intent.visualization_type = 'map'
            elif any(word in query for word in ['plot', 'profile', 'depth']):
                intent.visualization_type = 'plot'
            elif any(word in query for word in ['chart', 'trend', 'time']):
                intent.visualization_type = 'chart'
            else:
                intent.visualization_type = 'plot'  # Default
                
            intent.entities["wants_visualization"] = True
            intent.entities["visualization_type"] = intent.visualization_type
            
        # Check for export requests
        export_formats = ['csv', 'json', 'netcdf', 'excel', 'download']
        for fmt in export_formats:
            if fmt in query:
                intent.export_format = fmt
                intent.entities["export_format"] = fmt
                break
                
        # Extract limit if specified
        limit_pattern = re.compile(r'\b(?:top|first|limit|max)\s*(\d+)\b', re.IGNORECASE)
        limit_match = limit_pattern.search(query)
        if limit_match:
            try:
                intent.limit = int(limit_match.group(1))
                intent.entities["limit"] = intent.limit
            except ValueError:
                pass
                
    def _extract_comparisons(self, query: str, intent: QueryIntent):
        """Extract comparison requests from query."""
        
        if self.comparison_pattern.search(query):
            intent.entities["wants_comparison"] = True
            
            # Try to identify what's being compared
            # This is a simplified implementation - could be much more sophisticated
            
            # Check for parameter comparisons
            if len(intent.parameters) > 1:
                intent.compare_parameters = intent.parameters[1:]
                
            # Check for region comparisons
            regions_mentioned = []
            for region, aliases in REGION_ALIASES.items():
                for alias in aliases:
                    if alias in query:
                        regions_mentioned.append(region)
                        
            if len(regions_mentioned) > 1:
                intent.compare_regions = regions_mentioned[1:]
                
    def _determine_query_type(self, query: str, intent: QueryIntent):
        """Determine the primary query type based on extracted information."""
        
        # Keyword-based type detection
        type_keywords = {
            QueryType.STATISTICS: [
                'statistics', 'stats', 'summary', 'average', 'mean', 'count', 
                'total', 'how many', 'what is', 'data'
            ],
            QueryType.FLOATS: [
                'float', 'floats', 'sensor', 'sensors', 'buoy', 'buoys', 
                'platform', 'instrument'
            ],
            QueryType.PROFILES: [
                'profile', 'profiles', 'measurement', 'cast', 'cycle'
            ],
            QueryType.MEASUREMENTS: [
                'measurement', 'measurements', 'data point', 'value', 'reading'
            ],
            QueryType.VISUALIZATION: [
                'plot', 'chart', 'graph', 'map', 'visualize', 'show', 'display'
            ],
            QueryType.EXPORT: [
                'export', 'download', 'save', 'file', 'csv', 'json'
            ],
            QueryType.COMPARISON: [
                'compare', 'comparison', 'versus', 'vs', 'difference', 'between'
            ],
            QueryType.HELP: [
                'help', 'what can', 'how to', 'explain', 'tutorial'
            ]
        }
        
        # Score each query type
        type_scores = {}
        for query_type, keywords in type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query)
            if score > 0:
                type_scores[query_type] = score
                
        # Additional scoring based on extracted entities
        if intent.visualization_type:
            type_scores[QueryType.VISUALIZATION] = type_scores.get(QueryType.VISUALIZATION, 0) + 2
            
        if intent.export_format:
            type_scores[QueryType.EXPORT] = type_scores.get(QueryType.EXPORT, 0) + 2
            
        if intent.compare_parameters or intent.compare_regions:
            type_scores[QueryType.COMPARISON] = type_scores.get(QueryType.COMPARISON, 0) + 2
            
        if intent.float_ids:
            type_scores[QueryType.FLOATS] = type_scores.get(QueryType.FLOATS, 0) + 1
            
        if intent.profile_ids:
            type_scores[QueryType.PROFILES] = type_scores.get(QueryType.PROFILES, 0) + 1
            
        if intent.aggregations:
            type_scores[QueryType.STATISTICS] = type_scores.get(QueryType.STATISTICS, 0) + 1
            
        # Select highest scoring type
        if type_scores:
            intent.query_type = max(type_scores, key=type_scores.get)
        else:
            # Default to statistics for data queries, help for everything else
            if intent.parameters or intent.aggregations:
                intent.query_type = QueryType.STATISTICS
            else:
                intent.query_type = QueryType.HELP
                
        intent.entities["type_scores"] = {k.value: v for k, v in type_scores.items()}
        
    def _apply_context(self, intent: QueryIntent, context: ConversationContext):
        """Apply conversation context to fill in missing information."""
        
        # If no parameters specified, use last parameters from context
        if not intent.parameters and context.last_parameters:
            intent.parameters = context.last_parameters
            intent.entities["context_parameters"] = [p.value for p in context.last_parameters]
            
        # If no region specified, use last region
        if not intent.geographic_region and context.last_region:
            intent.geographic_region = context.last_region
            intent.geographic_bounds = REGION_BOUNDS.get(context.last_region)
            intent.entities["context_region"] = context.last_region.value
            
        # If no time range specified, use last time range
        if not intent.time_range and context.last_time_range:
            intent.time_range = context.last_time_range
            intent.entities["context_time_range"] = True
            
        # If no float IDs specified, use last float IDs
        if not intent.float_ids and context.last_float_ids:
            intent.float_ids = context.last_float_ids
            intent.entities["context_float_ids"] = context.last_float_ids
            
    def _calculate_confidence(self, intent: QueryIntent, query: str) -> float:
        """Calculate confidence score for the parsed intent."""
        
        confidence = 0.0
        factors = 0
        
        # Base confidence from query type determination
        if "type_scores" in intent.entities and intent.entities["type_scores"]:
            max_score = max(intent.entities["type_scores"].values())
            if max_score > 0:
                confidence += min(max_score * 0.2, 0.4)  # Max 0.4 from type detection
                factors += 1
                
        # Confidence from extracted entities
        entity_bonus = 0.0
        if intent.parameters:
            entity_bonus += 0.2
        if intent.geographic_region or intent.geographic_bounds:
            entity_bonus += 0.1
        if intent.time_range:
            entity_bonus += 0.1
        if intent.aggregations:
            entity_bonus += 0.1
        if intent.float_ids or intent.profile_ids:
            entity_bonus += 0.1
            
        confidence += entity_bonus
        factors += 1
        
        # Penalty for very short queries
        if len(query.split()) < 3:
            confidence *= 0.8
            
        # Penalty for very long queries without clear structure
        if len(query.split()) > 20:
            confidence *= 0.9
            
        # Bonus for specific IDs (high confidence)
        if intent.profile_ids or intent.float_ids:
            confidence += 0.1
            
        return min(confidence, 1.0)  # Cap at 1.0


def create_query_parser() -> QueryParser:
    """Factory function to create a query parser instance."""
    return QueryParser()