"""
Dynamic SQL query generation from parsed natural language intents.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, date
from sqlalchemy import text, and_, or_, func, desc, asc
from sqlalchemy.orm import Query

from .models import (
    QueryIntent, QueryType, Parameter, AggregationType,
    GeographicRegion, GeographicBounds, TimeRange, DepthRange,
    TemporalGranularity
)

logger = logging.getLogger(__name__)


class SQLGenerator:
    """Dynamic SQL query generator for oceanographic data queries."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # SQL injection prevention patterns
        self._safe_patterns = {
            'table_names': ['argo_floats', 'argo_profiles', 'argo_measurements'],
            'column_names': [
                'float_id', 'profile_id', 'measurement_date', 'latitude', 'longitude',
                'pressure', 'depth', 'temperature', 'salinity', 'oxygen',
                'temperature_qc', 'salinity_qc', 'oxygen_qc', 'status',
                'cycle_number', 'data_points', 'max_pressure', 'min_pressure'
            ]
        }
        
    def generate_sql(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate SQL query from parsed intent.
        
        Args:
            intent: Parsed query intent
            limit: Optional result limit override
            
        Returns:
            Dictionary containing SQL query, parameters, and metadata
        """
        self.logger.info(f"Generating SQL for {intent.query_type.value} query")
        
        try:
            if intent.query_type == QueryType.STATISTICS:
                return self._generate_statistics_query(intent, limit)
            elif intent.query_type == QueryType.FLOATS:
                return self._generate_floats_query(intent, limit)
            elif intent.query_type == QueryType.PROFILES:
                return self._generate_profiles_query(intent, limit)
            elif intent.query_type == QueryType.MEASUREMENTS:
                return self._generate_measurements_query(intent, limit)
            elif intent.query_type == QueryType.COMPARISON:
                return self._generate_comparison_query(intent, limit)
            elif intent.query_type == QueryType.VISUALIZATION:
                return self._generate_visualization_query(intent, limit)
            else:
                return self._generate_default_query(intent, limit)
                
        except Exception as e:
            self.logger.error(f"Error generating SQL: {e}", exc_info=True)
            return {
                "sql": "SELECT COUNT(*) as error_fallback FROM argo_floats LIMIT 1;",
                "parameters": {},
                "error": str(e),
                "query_type": intent.query_type.value
            }
    
    def _generate_statistics_query(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """Generate SQL for statistical queries."""
        
        if not intent.parameters:
            # General statistics query
            sql = """
            SELECT 
                COUNT(DISTINCT f.float_id) as total_floats,
                COUNT(DISTINCT f.float_id) FILTER (WHERE f.status = 'active') as active_floats,
                COUNT(DISTINCT p.profile_id) as total_profiles,
                COUNT(DISTINCT m.id) as total_measurements,
                MIN(p.measurement_date) as earliest_date,
                MAX(p.measurement_date) as latest_date,
                ROUND(AVG(p.latitude)::numeric, 2) as avg_latitude,
                ROUND(AVG(p.longitude)::numeric, 2) as avg_longitude
            FROM argo_floats f
            LEFT JOIN argo_profiles p ON f.float_id = p.float_id
            LEFT JOIN argo_measurements m ON p.profile_id = m.profile_id
            """
            
            where_conditions, params = self._build_where_conditions(intent)
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
                
        else:
            # Parameter-specific statistics
            parameter = intent.parameters[0].value
            aggregations = intent.aggregations if intent.aggregations else [AggregationType.COUNT, AggregationType.AVERAGE]
            
            select_fields = []
            for agg in aggregations:
                if agg == AggregationType.COUNT:
                    select_fields.append(f"COUNT(m.{parameter}) as {parameter}_count")
                elif agg in [AggregationType.AVERAGE, AggregationType.MEAN]:
                    select_fields.append(f"ROUND(AVG(m.{parameter})::numeric, 2) as avg_{parameter}")
                elif agg == AggregationType.MINIMUM:
                    select_fields.append(f"ROUND(MIN(m.{parameter})::numeric, 2) as min_{parameter}")
                elif agg == AggregationType.MAXIMUM:
                    select_fields.append(f"ROUND(MAX(m.{parameter})::numeric, 2) as max_{parameter}")
                elif agg == AggregationType.STANDARD_DEVIATION:
                    select_fields.append(f"ROUND(STDDEV(m.{parameter})::numeric, 2) as std_{parameter}")
                elif agg == AggregationType.MEDIAN:
                    select_fields.append(f"ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY m.{parameter})::numeric, 2) as median_{parameter}")
            
            # Add depth range if available
            if parameter != 'depth':
                select_fields.extend([
                    "ROUND(MIN(m.depth)::numeric, 1) as min_depth",
                    "ROUND(MAX(m.depth)::numeric, 1) as max_depth"
                ])
            
            sql = f"""
            SELECT 
                {', '.join(select_fields)},
                COUNT(DISTINCT p.profile_id) as profiles_with_data
            FROM argo_measurements m
            JOIN argo_profiles p ON m.profile_id = p.profile_id
            JOIN argo_floats f ON p.float_id = f.float_id
            WHERE m.{parameter} IS NOT NULL
            """
            
            where_conditions, params = self._build_where_conditions(intent)
            if where_conditions:
                sql += " AND " + " AND ".join(where_conditions)
        
        return {
            "sql": sql.strip(),
            "parameters": params,
            "query_type": intent.query_type.value,
            "primary_parameter": intent.parameters[0].value if intent.parameters else None,
            "aggregations": [a.value for a in intent.aggregations] if intent.aggregations else []
        }
    
    def _generate_floats_query(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """Generate SQL for float queries."""
        
        limit = limit or intent.limit or 50
        
        sql = """
        SELECT 
            f.float_id,
            f.platform_number,
            f.institution,
            f.status,
            f.total_profiles,
            f.last_latitude,
            f.last_longitude,
            f.first_profile_date,
            f.last_profile_date,
            COUNT(DISTINCT p.profile_id) as actual_profiles
        FROM argo_floats f
        LEFT JOIN argo_profiles p ON f.float_id = p.float_id
        """
        
        where_conditions, params = self._build_where_conditions(intent)
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)
            
        sql += """
        GROUP BY f.float_id, f.platform_number, f.institution, f.status, 
                 f.total_profiles, f.last_latitude, f.last_longitude,
                 f.first_profile_date, f.last_profile_date
        ORDER BY f.last_profile_date DESC NULLS LAST
        """
        
        if limit:
            sql += f" LIMIT {limit}"
            
        return {
            "sql": sql.strip(),
            "parameters": params,
            "query_type": intent.query_type.value,
            "limit": limit
        }
    
    def _generate_profiles_query(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """Generate SQL for profile queries."""
        
        limit = limit or intent.limit or 100
        
        if intent.profile_ids:
            # Specific profile query
            profile_ids = ', '.join(f"'{pid}'" for pid in intent.profile_ids)
            sql = f"""
            SELECT 
                p.profile_id,
                p.float_id,
                p.cycle_number,
                p.measurement_date,
                p.latitude,
                p.longitude,
                p.data_points,
                p.max_pressure,
                p.min_pressure,
                p.quality_flag,
                f.institution,
                f.status as float_status
            FROM argo_profiles p
            JOIN argo_floats f ON p.float_id = f.float_id
            WHERE p.profile_id IN ({profile_ids})
            ORDER BY p.measurement_date DESC
            """
        else:
            # General profile query
            sql = """
            SELECT 
                p.profile_id,
                p.float_id,
                p.cycle_number,
                p.measurement_date,
                p.latitude,
                p.longitude,
                p.data_points,
                p.max_pressure,
                p.min_pressure,
                p.quality_flag,
                f.institution
            FROM argo_profiles p
            JOIN argo_floats f ON p.float_id = f.float_id
            """
            
            where_conditions, params = self._build_where_conditions(intent)
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
                
            sql += " ORDER BY p.measurement_date DESC"
            
            if limit:
                sql += f" LIMIT {limit}"
        
        return {
            "sql": sql.strip(),
            "parameters": params if 'params' in locals() else {},
            "query_type": intent.query_type.value,
            "limit": limit,
            "specific_profiles": bool(intent.profile_ids)
        }
    
    def _generate_measurements_query(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """Generate SQL for measurement queries."""
        
        limit = limit or intent.limit or 1000
        
        # Determine which parameters to select
        if intent.parameters:
            param_columns = []
            for param in intent.parameters:
                param_columns.extend([
                    f"m.{param.value}",
                    f"m.{param.value}_qc"
                ])
        else:
            # Default parameters
            param_columns = [
                "m.temperature", "m.temperature_qc",
                "m.salinity", "m.salinity_qc",
                "m.pressure", "m.pressure_qc",
                "m.oxygen", "m.oxygen_qc"
            ]
        
        sql = f"""
        SELECT 
            m.profile_id,
            p.float_id,
            p.measurement_date,
            p.latitude,
            p.longitude,
            m.pressure,
            m.depth,
            {', '.join(param_columns)}
        FROM argo_measurements m
        JOIN argo_profiles p ON m.profile_id = p.profile_id
        JOIN argo_floats f ON p.float_id = f.float_id
        """
        
        where_conditions, params = self._build_where_conditions(intent)
        
        # Add parameter-specific conditions
        if intent.parameters:
            param_conditions = []
            for param in intent.parameters:
                param_conditions.append(f"m.{param.value} IS NOT NULL")
            if param_conditions:
                where_conditions.extend(param_conditions)
        
        if where_conditions:
            sql += " WHERE " + " AND ".join(where_conditions)
            
        sql += " ORDER BY p.measurement_date DESC, m.pressure ASC"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        return {
            "sql": sql.strip(),
            "parameters": params,
            "query_type": intent.query_type.value,
            "parameters_requested": [p.value for p in intent.parameters] if intent.parameters else [],
            "limit": limit
        }
    
    def _generate_comparison_query(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """Generate SQL for comparison queries."""
        
        if intent.compare_parameters and len(intent.compare_parameters) > 0:
            # Parameter comparison
            param1 = intent.parameters[0].value if intent.parameters else 'temperature'
            param2 = intent.compare_parameters[0].value
            
            sql = f"""
            SELECT 
                p.profile_id,
                p.float_id,
                p.measurement_date,
                p.latitude,
                p.longitude,
                ROUND(AVG(m.{param1})::numeric, 2) as avg_{param1},
                ROUND(AVG(m.{param2})::numeric, 2) as avg_{param2},
                ROUND((AVG(m.{param1}) - AVG(m.{param2}))::numeric, 2) as difference,
                COUNT(*) as measurement_count
            FROM argo_measurements m
            JOIN argo_profiles p ON m.profile_id = p.profile_id
            JOIN argo_floats f ON p.float_id = f.float_id
            WHERE m.{param1} IS NOT NULL AND m.{param2} IS NOT NULL
            """
            
            where_conditions, params = self._build_where_conditions(intent)
            if where_conditions:
                sql += " AND " + " AND ".join(where_conditions)
                
            sql += f"""
            GROUP BY p.profile_id, p.float_id, p.measurement_date, p.latitude, p.longitude
            ORDER BY p.measurement_date DESC
            LIMIT {limit or 100}
            """
            
        elif intent.compare_regions and len(intent.compare_regions) > 0:
            # Regional comparison
            parameter = intent.parameters[0].value if intent.parameters else 'temperature'
            
            sql = f"""
            SELECT 
                'region_1' as region,
                COUNT(DISTINCT p.profile_id) as profiles,
                COUNT(m.id) as measurements,
                ROUND(AVG(m.{parameter})::numeric, 2) as avg_{parameter},
                ROUND(MIN(m.{parameter})::numeric, 2) as min_{parameter},
                ROUND(MAX(m.{parameter})::numeric, 2) as max_{parameter}
            FROM argo_measurements m
            JOIN argo_profiles p ON m.profile_id = p.profile_id
            WHERE m.{parameter} IS NOT NULL
            AND p.latitude BETWEEN %(region1_min_lat)s AND %(region1_max_lat)s
            AND p.longitude BETWEEN %(region1_min_lon)s AND %(region1_max_lon)s
            
            UNION ALL
            
            SELECT 
                'region_2' as region,
                COUNT(DISTINCT p.profile_id) as profiles,
                COUNT(m.id) as measurements,
                ROUND(AVG(m.{parameter})::numeric, 2) as avg_{parameter},
                ROUND(MIN(m.{parameter})::numeric, 2) as min_{parameter},
                ROUND(MAX(m.{parameter})::numeric, 2) as max_{parameter}
            FROM argo_measurements m
            JOIN argo_profiles p ON m.profile_id = p.profile_id
            WHERE m.{parameter} IS NOT NULL
            AND p.latitude BETWEEN %(region2_min_lat)s AND %(region2_max_lat)s
            AND p.longitude BETWEEN %(region2_min_lon)s AND %(region2_max_lon)s
            """
            
            params = {}
            # Add region bounds - this is simplified, would need proper region definitions
            params.update({
                'region1_min_lat': -10, 'region1_max_lat': 30,
                'region1_min_lon': 60, 'region1_max_lon': 100,
                'region2_min_lat': -40, 'region2_max_lat': 10,
                'region2_min_lon': 80, 'region2_max_lon': 120
            })
        else:
            # Fallback to simple statistics
            return self._generate_statistics_query(intent, limit)
        
        return {
            "sql": sql.strip(),
            "parameters": params if 'params' in locals() else {},
            "query_type": intent.query_type.value,
            "comparison_type": "parameters" if intent.compare_parameters else "regions"
        }
    
    def _generate_visualization_query(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """Generate SQL for visualization queries."""
        
        limit = limit or intent.limit or 500
        
        if intent.visualization_type == 'map':
            # Map visualization - return float/profile locations
            sql = """
            SELECT DISTINCT
                p.float_id,
                p.profile_id,
                p.measurement_date,
                p.latitude,
                p.longitude,
                f.status as float_status,
                f.institution
            FROM argo_profiles p
            JOIN argo_floats f ON p.float_id = f.float_id
            """
            
            where_conditions, params = self._build_where_conditions(intent)
            if where_conditions:
                sql += " WHERE " + " AND ".join(where_conditions)
                
            sql += " ORDER BY p.measurement_date DESC"
            
        elif intent.visualization_type == 'plot' and intent.profile_ids:
            # Profile plot - return measurement depth series
            profile_id = intent.profile_ids[0]
            parameter = intent.parameters[0].value if intent.parameters else 'temperature'
            
            sql = f"""
            SELECT 
                m.pressure,
                m.depth,
                m.{parameter},
                m.{parameter}_qc,
                p.measurement_date,
                p.latitude,
                p.longitude,
                p.float_id
            FROM argo_measurements m
            JOIN argo_profiles p ON m.profile_id = p.profile_id
            WHERE p.profile_id = %(profile_id)s
            AND m.{parameter} IS NOT NULL
            ORDER BY m.pressure ASC
            """
            
            params = {'profile_id': profile_id}
            
        else:
            # Time series or general visualization
            parameter = intent.parameters[0].value if intent.parameters else 'temperature'
            
            sql = f"""
            SELECT 
                p.measurement_date,
                p.latitude,
                p.longitude,
                p.float_id,
                ROUND(AVG(m.{parameter})::numeric, 2) as avg_{parameter},
                COUNT(m.id) as measurement_count
            FROM argo_measurements m
            JOIN argo_profiles p ON m.profile_id = p.profile_id
            JOIN argo_floats f ON p.float_id = f.float_id
            WHERE m.{parameter} IS NOT NULL
            """
            
            where_conditions, params = self._build_where_conditions(intent)
            if where_conditions:
                sql += " AND " + " AND ".join(where_conditions)
                
            sql += f"""
            GROUP BY p.measurement_date, p.latitude, p.longitude, p.float_id
            ORDER BY p.measurement_date ASC
            LIMIT {limit}
            """
        
        return {
            "sql": sql.strip(),
            "parameters": params if 'params' in locals() else {},
            "query_type": intent.query_type.value,
            "visualization_type": intent.visualization_type,
            "parameter": intent.parameters[0].value if intent.parameters else None
        }
    
    def _generate_default_query(self, intent: QueryIntent, limit: Optional[int] = None) -> Dict[str, Any]:
        """Generate default fallback query."""
        
        sql = """
        SELECT 
            COUNT(DISTINCT f.float_id) as total_floats,
            COUNT(DISTINCT p.profile_id) as total_profiles,
            MAX(p.measurement_date) as latest_date
        FROM argo_floats f
        LEFT JOIN argo_profiles p ON f.float_id = p.float_id
        """
        
        return {
            "sql": sql.strip(),
            "parameters": {},
            "query_type": intent.query_type.value,
            "fallback": True
        }
    
    def _build_where_conditions(self, intent: QueryIntent) -> Tuple[List[str], Dict[str, Any]]:
        """Build WHERE clause conditions and parameters from intent."""
        
        conditions = []
        params = {}
        
        # Geographic conditions
        if intent.geographic_bounds:
            bounds = intent.geographic_bounds
            if bounds.is_valid():
                conditions.append("p.latitude BETWEEN %(min_lat)s AND %(max_lat)s")
                conditions.append("p.longitude BETWEEN %(min_lon)s AND %(max_lon)s")
                params.update({
                    'min_lat': bounds.min_latitude,
                    'max_lat': bounds.max_latitude,
                    'min_lon': bounds.min_longitude,
                    'max_lon': bounds.max_longitude
                })
        
        # Temporal conditions
        if intent.time_range:
            time_range = intent.time_range
            if time_range.start_date:
                conditions.append("p.measurement_date >= %(start_date)s")
                params['start_date'] = time_range.start_date
            if time_range.end_date:
                conditions.append("p.measurement_date <= %(end_date)s")
                params['end_date'] = time_range.end_date
        
        # Depth conditions
        if intent.depth_range:
            depth_range = intent.depth_range
            if depth_range.min_depth is not None:
                conditions.append("m.depth >= %(min_depth)s")
                params['min_depth'] = depth_range.min_depth
            if depth_range.max_depth is not None:
                conditions.append("m.depth <= %(max_depth)s")
                params['max_depth'] = depth_range.max_depth
            if depth_range.min_pressure is not None:
                conditions.append("m.pressure >= %(min_pressure)s")
                params['min_pressure'] = depth_range.min_pressure
            if depth_range.max_pressure is not None:
                conditions.append("m.pressure <= %(max_pressure)s")
                params['max_pressure'] = depth_range.max_pressure
        
        # Float ID conditions
        if intent.float_ids:
            float_ids = ', '.join(f"'{fid}'" for fid in intent.float_ids)
            conditions.append(f"f.float_id IN ({float_ids})")
        
        # Profile ID conditions
        if intent.profile_ids:
            profile_ids = ', '.join(f"'{pid}'" for pid in intent.profile_ids)
            conditions.append(f"p.profile_id IN ({profile_ids})")
        
        # Data quality conditions
        if intent.quality_flags:
            # Only include good quality data
            if '1' in intent.quality_flags or 'good' in [qf.lower() for qf in intent.quality_flags]:
                if intent.parameters:
                    for param in intent.parameters:
                        conditions.append(f"(m.{param.value}_qc = '1' OR m.{param.value}_qc IS NULL)")
        
        # Data mode conditions
        if intent.data_mode:
            conditions.append("p.data_mode = %(data_mode)s")
            params['data_mode'] = intent.data_mode
        
        return conditions, params
    
    def validate_sql_safety(self, sql: str) -> bool:
        """Validate SQL query for safety (basic SQL injection prevention)."""
        
        # Convert to lowercase for checking
        sql_lower = sql.lower()
        
        # Check for dangerous keywords
        dangerous_keywords = [
            'drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update',
            'grant', 'revoke', 'execute', 'exec', 'xp_', 'sp_', 'bulk', 'union',
            'information_schema', 'pg_', 'mysql', 'sys'
        ]
        
        for keyword in dangerous_keywords:
            if keyword in sql_lower:
                self.logger.warning(f"Potentially unsafe SQL keyword detected: {keyword}")
                return False
        
        # Check for only allowed table names
        for table in self._safe_patterns['table_names']:
            sql_lower = sql_lower.replace(table, '')
        
        # Basic structure validation
        if not sql_lower.strip().startswith('select'):
            self.logger.warning("SQL must start with SELECT")
            return False
        
        return True


def create_sql_generator() -> SQLGenerator:
    """Factory function to create an SQL generator instance."""
    return SQLGenerator()