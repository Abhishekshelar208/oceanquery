"""
Data models for natural language query parsing.
"""

from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Types of queries the system can handle."""
    STATISTICS = "statistics"
    PROFILES = "profiles"
    FLOATS = "floats"
    MEASUREMENTS = "measurements"
    COMPARISON = "comparison"
    VISUALIZATION = "visualization"
    EXPORT = "export"
    HELP = "help"


class Parameter(str, Enum):
    """Ocean parameters available for analysis."""
    TEMPERATURE = "temperature"
    SALINITY = "salinity"
    PRESSURE = "pressure"
    OXYGEN = "oxygen"
    PH = "ph"
    NITRATE = "nitrate"
    CHLOROPHYLL_A = "chlorophyll_a"
    DEPTH = "depth"


class AggregationType(str, Enum):
    """Statistical aggregation types."""
    AVERAGE = "average"
    MEAN = "mean"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    COUNT = "count"
    SUM = "sum"
    STANDARD_DEVIATION = "std"
    MEDIAN = "median"
    RANGE = "range"


class TemporalGranularity(str, Enum):
    """Temporal grouping granularity."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    SEASON = "season"


class GeographicRegion(str, Enum):
    """Predefined geographic regions."""
    INDIAN_OCEAN = "indian_ocean"
    ARABIAN_SEA = "arabian_sea"
    BAY_OF_BENGAL = "bay_of_bengal"
    SOUTHERN_OCEAN = "southern_ocean"
    EQUATORIAL = "equatorial"
    GLOBAL = "global"


@dataclass
class GeographicBounds:
    """Geographic bounding box."""
    min_latitude: Optional[float] = None
    max_latitude: Optional[float] = None
    min_longitude: Optional[float] = None
    max_longitude: Optional[float] = None
    
    def is_valid(self) -> bool:
        """Check if bounds are valid."""
        if not all([self.min_latitude, self.max_latitude, self.min_longitude, self.max_longitude]):
            return False
        return (
            -90 <= self.min_latitude <= self.max_latitude <= 90 and
            -180 <= self.min_longitude <= self.max_longitude <= 180
        )


@dataclass
class TimeRange:
    """Time range specification."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    relative_period: Optional[str] = None  # "last year", "past month", etc.
    
    def is_valid(self) -> bool:
        """Check if time range is valid."""
        if self.start_date and self.end_date:
            return self.start_date <= self.end_date
        return True


@dataclass
class DepthRange:
    """Depth/pressure range specification."""
    min_depth: Optional[float] = None
    max_depth: Optional[float] = None
    min_pressure: Optional[float] = None
    max_pressure: Optional[float] = None
    
    def is_valid(self) -> bool:
        """Check if depth range is valid."""
        if self.min_depth is not None and self.max_depth is not None:
            return 0 <= self.min_depth <= self.max_depth
        if self.min_pressure is not None and self.max_pressure is not None:
            return 0 <= self.min_pressure <= self.max_pressure
        return True


@dataclass
class QueryIntent:
    """Parsed query intent with all extracted information."""
    query_type: QueryType
    parameters: List[Parameter] = field(default_factory=list)
    aggregations: List[AggregationType] = field(default_factory=list)
    
    # Geographic constraints
    geographic_bounds: Optional[GeographicBounds] = None
    geographic_region: Optional[GeographicRegion] = None
    
    # Temporal constraints
    time_range: Optional[TimeRange] = None
    temporal_granularity: Optional[TemporalGranularity] = None
    
    # Depth constraints
    depth_range: Optional[DepthRange] = None
    
    # Specific identifiers
    float_ids: List[str] = field(default_factory=list)
    profile_ids: List[str] = field(default_factory=list)
    
    # Data quality filters
    quality_flags: List[str] = field(default_factory=list)
    data_mode: Optional[str] = None  # R=real-time, D=delayed-mode
    
    # Output preferences
    limit: Optional[int] = None
    visualization_type: Optional[str] = None  # plot, map, chart, table
    export_format: Optional[str] = None  # csv, json, netcdf
    
    # Comparison settings
    compare_parameters: List[Parameter] = field(default_factory=list)
    compare_regions: List[GeographicRegion] = field(default_factory=list)
    compare_time_periods: List[TimeRange] = field(default_factory=list)
    
    # Confidence score
    confidence: float = 0.0
    
    # Original query for reference
    original_query: str = ""
    
    # Parsed entities for debugging
    entities: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_type": self.query_type.value,
            "parameters": [p.value for p in self.parameters],
            "aggregations": [a.value for a in self.aggregations],
            "geographic_bounds": self.geographic_bounds.__dict__ if self.geographic_bounds else None,
            "geographic_region": self.geographic_region.value if self.geographic_region else None,
            "time_range": self.time_range.__dict__ if self.time_range else None,
            "temporal_granularity": self.temporal_granularity.value if self.temporal_granularity else None,
            "depth_range": self.depth_range.__dict__ if self.depth_range else None,
            "float_ids": self.float_ids,
            "profile_ids": self.profile_ids,
            "quality_flags": self.quality_flags,
            "data_mode": self.data_mode,
            "limit": self.limit,
            "visualization_type": self.visualization_type,
            "export_format": self.export_format,
            "compare_parameters": [p.value for p in self.compare_parameters],
            "compare_regions": [r.value for r in self.compare_regions],
            "confidence": self.confidence,
            "original_query": self.original_query,
            "entities": self.entities
        }


@dataclass
class ConversationContext:
    """Context from previous conversation turns."""
    conversation_id: str
    previous_intents: List[QueryIntent] = field(default_factory=list)
    last_parameters: List[Parameter] = field(default_factory=list)
    last_region: Optional[GeographicRegion] = None
    last_time_range: Optional[TimeRange] = None
    last_float_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def update_context(self, new_intent: QueryIntent):
        """Update context with new query intent."""
        self.previous_intents.append(new_intent)
        if new_intent.parameters:
            self.last_parameters = new_intent.parameters
        if new_intent.geographic_region:
            self.last_region = new_intent.geographic_region
        if new_intent.time_range:
            self.last_time_range = new_intent.time_range
        if new_intent.float_ids:
            self.last_float_ids = new_intent.float_ids
        self.updated_at = datetime.utcnow()
        
        # Keep only last 10 intents to prevent memory bloat
        if len(self.previous_intents) > 10:
            self.previous_intents = self.previous_intents[-10:]


class ParsedQuery(BaseModel):
    """API response model for parsed queries."""
    intent: Dict[str, Any] = Field(..., description="Parsed query intent")
    confidence: float = Field(..., description="Parsing confidence score")
    entities: Dict[str, Any] = Field(default={}, description="Extracted entities")
    suggestions: List[str] = Field(default=[], description="Query improvement suggestions")
    errors: List[str] = Field(default=[], description="Parsing errors or warnings")


# Geographic region mappings
REGION_BOUNDS = {
    GeographicRegion.INDIAN_OCEAN: GeographicBounds(-40, 30, 20, 120),
    GeographicRegion.ARABIAN_SEA: GeographicBounds(10, 25, 60, 78),
    GeographicRegion.BAY_OF_BENGAL: GeographicBounds(5, 22, 78, 100),
    GeographicRegion.SOUTHERN_OCEAN: GeographicBounds(-60, -30, 20, 120),
    GeographicRegion.EQUATORIAL: GeographicBounds(-10, 10, 60, 100),
}

# Parameter aliases for natural language processing
PARAMETER_ALIASES = {
    Parameter.TEMPERATURE: [
        "temperature", "temp", "thermal", "heat", "sst", "sea surface temperature",
        "water temperature", "ocean temperature", "degrees", "celsius", "°c"
    ],
    Parameter.SALINITY: [
        "salinity", "salt", "psu", "practical salinity", "saltiness",
        "sea salt", "sodium", "conductivity"
    ],
    Parameter.PRESSURE: [
        "pressure", "depth", "dbar", "decibar", "deep", "shallow",
        "surface", "bottom", "meters", "m"
    ],
    Parameter.OXYGEN: [
        "oxygen", "o2", "dissolved oxygen", "do", "µmol/kg", "micromol",
        "hypoxia", "anoxia", "oxygenation"
    ],
    Parameter.PH: [
        "ph", "p-h", "acidity", "alkalinity", "acid", "ph scale"
    ],
    Parameter.NITRATE: [
        "nitrate", "no3", "nitrogen", "nutrients", "eutrophication"
    ],
    Parameter.CHLOROPHYLL_A: [
        "chlorophyll", "chl", "chla", "phytoplankton", "algae",
        "primary production", "biomass"
    ]
}

# Aggregation aliases
AGGREGATION_ALIASES = {
    AggregationType.AVERAGE: ["average", "avg", "mean"],
    AggregationType.MEAN: ["mean", "average", "avg"],
    AggregationType.MINIMUM: ["minimum", "min", "lowest", "smallest"],
    AggregationType.MAXIMUM: ["maximum", "max", "highest", "largest", "peak"],
    AggregationType.COUNT: ["count", "number of", "how many", "total"],
    AggregationType.SUM: ["sum", "total", "add up"],
    AggregationType.STANDARD_DEVIATION: ["std", "standard deviation", "variation", "variability"],
    AggregationType.MEDIAN: ["median", "middle", "50th percentile"],
    AggregationType.RANGE: ["range", "span", "difference", "variation"]
}

# Region aliases
REGION_ALIASES = {
    GeographicRegion.INDIAN_OCEAN: [
        "indian ocean", "indian", "io", "indian sea"
    ],
    GeographicRegion.ARABIAN_SEA: [
        "arabian sea", "arabian", "arabia", "west indian ocean"
    ],
    GeographicRegion.BAY_OF_BENGAL: [
        "bay of bengal", "bengal", "bob", "east indian ocean", "bengal sea"
    ],
    GeographicRegion.SOUTHERN_OCEAN: [
        "southern ocean", "antarctic", "south", "polar"
    ],
    GeographicRegion.EQUATORIAL: [
        "equatorial", "equator", "tropical", "tropics"
    ]
}