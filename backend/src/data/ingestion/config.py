"""
Configuration classes for ARGO data ingestion pipeline.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


class DataMode(Enum):
    """ARGO data mode enumeration."""
    REAL_TIME = "R"
    DELAYED_MODE = "D"
    ADJUSTED = "A"


class QCFlag(Enum):
    """Quality Control flag enumeration."""
    NO_QC = "0"
    GOOD_DATA = "1" 
    PROBABLY_GOOD = "2"
    BAD_DATA_CORRECTABLE = "3"
    BAD_DATA = "4"
    VALUE_CHANGED = "5"
    NOT_USED = "6"
    NOMINAL = "7"
    INTERPOLATED = "8"
    MISSING_VALUE = "9"


@dataclass
class ValidationConfig:
    """Configuration for data validation rules."""
    
    # Temperature validation (Celsius)
    temp_min: float = -5.0
    temp_max: float = 40.0
    
    # Salinity validation (PSU)
    salinity_min: float = 0.0
    salinity_max: float = 45.0
    
    # Pressure validation (dbar)
    pressure_min: float = -10.0
    pressure_max: float = 12000.0
    
    # Oxygen validation (μmol/kg)
    oxygen_min: float = 0.0
    oxygen_max: float = 1000.0
    
    # Geographic bounds (degrees)
    latitude_min: float = -90.0
    latitude_max: float = 90.0
    longitude_min: float = -180.0
    longitude_max: float = 180.0
    
    # Date validation
    min_date: str = "1990-01-01"
    max_date: Optional[str] = None  # None means current date
    
    # QC flags to accept
    accepted_qc_flags: Set[QCFlag] = field(default_factory=lambda: {
        QCFlag.GOOD_DATA, 
        QCFlag.PROBABLY_GOOD, 
        QCFlag.BAD_DATA_CORRECTABLE
    })
    
    # Required variables in NetCDF file
    required_variables: Set[str] = field(default_factory=lambda: {
        "JULD", "LATITUDE", "LONGITUDE", "PRES", "TEMP", "PSAL"
    })
    
    # Optional variables
    optional_variables: Set[str] = field(default_factory=lambda: {
        "DOXY", "CHLA", "BBP700", "PH_IN_SITU_TOTAL", "NITRATE"
    })


@dataclass
class IngestionConfig:
    """Main configuration for ARGO data ingestion."""
    
    # Input/output paths
    input_directory: Path = field(default_factory=lambda: Path("data/raw/argo"))
    output_directory: Path = field(default_factory=lambda: Path("data/processed"))
    log_directory: Path = field(default_factory=lambda: Path("logs/ingestion"))
    
    # File patterns
    file_patterns: List[str] = field(default_factory=lambda: [
        "*.nc", "**/*.nc", "*profiles*.nc", "*Sprof*.nc"
    ])
    
    # Processing configuration
    batch_size: int = 1000  # Records per batch
    max_workers: int = 4    # Parallel processing threads
    chunk_size: int = 10000 # NetCDF reading chunk size
    
    # Database configuration
    connection_pool_size: int = 10
    max_overflow: int = 20
    connection_timeout: int = 30
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    exponential_backoff: bool = True
    
    # Progress tracking
    progress_update_interval: int = 100  # Records
    checkpoint_interval: int = 5000     # Records
    
    # Error handling
    skip_malformed_files: bool = True
    max_errors_per_file: int = 10
    continue_on_error: bool = True
    
    # Data filtering
    data_modes: Set[DataMode] = field(default_factory=lambda: {
        DataMode.REAL_TIME, DataMode.DELAYED_MODE, DataMode.ADJUSTED
    })
    
    # Geographic filtering (optional)
    geographic_bounds: Optional[Dict[str, float]] = None  # {"lat_min": -90, "lat_max": 90, ...}
    
    # Time filtering (optional)
    date_range: Optional[Dict[str, str]] = None  # {"start": "2020-01-01", "end": "2023-12-31"}
    
    # Validation configuration
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = True
    log_rotation: str = "midnight"  # daily rotation
    log_retention: int = 30  # days
    
    def __post_init__(self):
        """Validate and prepare configuration after initialization."""
        # Ensure directories exist
        self.input_directory.mkdir(parents=True, exist_ok=True)
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Validate batch size
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        
        # Validate worker count
        if self.max_workers <= 0:
            self.max_workers = os.cpu_count() or 1
            
        # Set max_date to current if not specified
        if self.validation.max_date is None:
            from datetime import date
            self.validation.max_date = date.today().isoformat()


@dataclass
class FileProcessingResult:
    """Result of processing a single NetCDF file."""
    
    file_path: Path
    success: bool
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    file_size: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class IngestionSummary:
    """Summary of complete ingestion process."""
    
    start_time: str
    end_time: str
    duration: float
    files_processed: int
    files_successful: int
    files_failed: int
    total_records_processed: int
    total_records_inserted: int
    total_records_updated: int
    total_records_skipped: int
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    performance_metrics: Dict = field(default_factory=dict)


def load_config_from_env() -> IngestionConfig:
    """Load ingestion configuration from environment variables."""
    config = IngestionConfig()
    
    # Update paths from environment
    if input_dir := os.getenv("ARGO_INPUT_DIR"):
        config.input_directory = Path(input_dir)
    
    if output_dir := os.getenv("ARGO_OUTPUT_DIR"):
        config.output_directory = Path(output_dir)
        
    if log_dir := os.getenv("ARGO_LOG_DIR"):
        config.log_directory = Path(log_dir)
    
    # Update processing parameters
    if batch_size := os.getenv("ARGO_BATCH_SIZE"):
        config.batch_size = int(batch_size)
        
    if max_workers := os.getenv("ARGO_MAX_WORKERS"):
        config.max_workers = int(max_workers)
        
    # Update database parameters
    if pool_size := os.getenv("ARGO_POOL_SIZE"):
        config.connection_pool_size = int(pool_size)
        
    # Update logging
    if log_level := os.getenv("ARGO_LOG_LEVEL"):
        config.log_level = log_level.upper()
        
    return config


def create_sample_config() -> IngestionConfig:
    """Create a sample configuration for testing/development."""
    config = IngestionConfig(
        input_directory=Path("data/samples/argo"),
        batch_size=500,
        max_workers=2,
        max_errors_per_file=5,
        geographic_bounds={
            "lat_min": 30.0,
            "lat_max": 50.0,
            "lon_min": -80.0,
            "lon_max": -40.0,
        },
        date_range={
            "start": "2020-01-01",
            "end": "2023-12-31"
        }
    )
    
    # Relax validation for sample data
    config.validation.accepted_qc_flags.add(QCFlag.BAD_DATA_CORRECTABLE)
    
    return config
