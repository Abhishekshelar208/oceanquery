"""
ARGO NetCDF data ingestion package.

This package provides comprehensive functionality for ingesting ARGO oceanographic
data from NetCDF files into the PostgreSQL database.

Key Components:
- config: Configuration classes and environment loading
- parsers: NetCDF file parsing and validation using xarray
- mappers: Data transformation to SQLAlchemy models
- database_ops: Bulk database operations with PostgreSQL UPSERT
- service: Main ingestion orchestration service
"""

from .config import (
    IngestionConfig,
    ValidationConfig, 
    QCFlag,
    DataMode,
    FileProcessingResult,
    IngestionSummary,
    load_config_from_env,
    create_sample_config
)

from .parsers import (
    ArgoProfile,
    ArgoNetCDFParser,
    discover_argo_files,
    validate_netcdf_file
)

from .mappers import (
    ArgoDataMapper,
    batch_map_profiles
)

from .database_ops import (
    DatabaseOperations,
    TransactionManager
)

from .service import (
    ArgoIngestionService,
    create_ingestion_service
)

__all__ = [
    # Configuration
    'IngestionConfig',
    'ValidationConfig', 
    'QCFlag',
    'DataMode',
    'FileProcessingResult',
    'IngestionSummary',
    'load_config_from_env',
    'create_sample_config',
    
    # Parsing
    'ArgoProfile',
    'ArgoNetCDFParser',
    'discover_argo_files',
    'validate_netcdf_file',
    
    # Mapping
    'ArgoDataMapper',
    'batch_map_profiles',
    
    # Database Operations
    'DatabaseOperations',
    'TransactionManager',
    
    # Service
    'ArgoIngestionService',
    'create_ingestion_service'
]
