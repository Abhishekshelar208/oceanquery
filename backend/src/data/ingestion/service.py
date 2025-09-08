"""
Main ingestion service orchestrating the entire ARGO data pipeline.
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from .config import IngestionConfig, IngestionSummary, FileProcessingResult
from .parsers import ArgoNetCDFParser, discover_argo_files, validate_netcdf_file
from .mappers import batch_map_profiles
from .database_ops import DatabaseOperations, TransactionManager

logger = logging.getLogger(__name__)


class ArgoIngestionService:
    """Main service for ARGO data ingestion."""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize components
        self.parser = ArgoNetCDFParser(config)
        self.db_ops = DatabaseOperations(config)
        self.transaction_mgr = TransactionManager(config)
        
        # Statistics
        self.stats = {
            'files_discovered': 0,
            'files_processed': 0,
            'files_successful': 0,
            'files_failed': 0,
            'files_skipped': 0,
            'total_records_processed': 0,
            'total_records_inserted': 0,
            'total_profiles': 0,
            'total_measurements': 0,
            'processing_start_time': None,
            'processing_end_time': None,
        }
        
    def ingest_directory(
        self, 
        directory: Optional[Path] = None,
        file_patterns: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> IngestionSummary:
        """
        Ingest all ARGO files from a directory.
        
        Args:
            directory: Input directory (uses config default if None)
            file_patterns: File patterns to match (uses config default if None)
            dry_run: If True, parse files but don't insert into database
            
        Returns:
            IngestionSummary with results
        """
        
        start_time = datetime.now()
        self.stats['processing_start_time'] = start_time.isoformat()
        
        directory = directory or self.config.input_directory
        file_patterns = file_patterns or self.config.file_patterns
        
        self.logger.info(f"Starting ARGO ingestion from {directory} (dry_run={dry_run})")
        
        try:
            # Discover files
            files = discover_argo_files(directory, file_patterns)
            self.stats['files_discovered'] = len(files)
            
            if not files:
                self.logger.warning(f"No ARGO files found in {directory}")
                return self._create_summary(start_time)
            
            # Process files
            if self.config.max_workers > 1:
                results = self._process_files_parallel(files, dry_run)
            else:
                results = self._process_files_sequential(files, dry_run)
            
            # Aggregate results
            self._aggregate_results(results)
            
        except Exception as e:
            self.logger.error(f"Error in ingestion service: {str(e)}", exc_info=True)
        
        finally:
            end_time = datetime.now()
            self.stats['processing_end_time'] = end_time.isoformat()
        
        return self._create_summary(start_time)
    
    def ingest_file(self, file_path: Path, dry_run: bool = False) -> FileProcessingResult:
        """
        Ingest a single ARGO file.
        
        Args:
            file_path: Path to NetCDF file
            dry_run: If True, parse file but don't insert into database
            
        Returns:
            FileProcessingResult
        """
        
        self.logger.info(f"Ingesting file: {file_path}")
        
        # Validate file first
        is_valid, validation_errors = validate_netcdf_file(file_path)
        if not is_valid:
            result = FileProcessingResult(
                file_path=file_path,
                success=False,
                errors=validation_errors
            )
            return result
        
        # Parse the file
        result = self.parser.parse_file(file_path)
        
        if not result.success:
            return result
        
        # Extract parsed profiles
        profiles = result.metadata.get('profiles', [])
        if not profiles:
            result.errors.append("No valid profiles found in file")
            result.success = False
            return result
        
        if dry_run:
            self.logger.info(f"Dry run: would process {len(profiles)} profiles from {file_path}")
            result.records_processed = len(profiles)
            return result
        
        # Insert into database
        try:
            with self.db_ops.get_session() as session:
                # Map profiles to database models
                models_dict = batch_map_profiles(profiles, self.config, session)
                
                # Bulk insert with transaction management
                with self.transaction_mgr.transaction(session, f"Insert {file_path.name}"):
                    floats_inserted, profiles_inserted, measurements_inserted = \
                        self.db_ops.bulk_insert_models(models_dict, session)
                    
                    result.records_inserted = profiles_inserted
                    result.records_processed = len(profiles)
                    
                    # Log the ingestion result
                    self.db_ops.log_ingestion_result(result, session)
                    
                self.logger.info(f"Successfully ingested {file_path}: "
                               f"{profiles_inserted} profiles, {measurements_inserted} measurements")
        
        except Exception as e:
            error_msg = f"Database error for {file_path}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            result.success = False
        
        return result
    
    def _process_files_parallel(self, files: List[Path], dry_run: bool) -> List[FileProcessingResult]:
        """Process files in parallel using ThreadPoolExecutor."""
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(self.ingest_file, file_path, dry_run): file_path
                for file_path in files
            }
            
            # Process completed futures
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    self.stats['files_processed'] += 1
                    if result.success:
                        self.stats['files_successful'] += 1
                    else:
                        self.stats['files_failed'] += 1
                        
                    # Log progress
                    if self.stats['files_processed'] % self.config.progress_update_interval == 0:
                        self.logger.info(f"Processed {self.stats['files_processed']}/{len(files)} files")
                        
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {str(e)}")
                    error_result = FileProcessingResult(
                        file_path=file_path,
                        success=False,
                        errors=[str(e)]
                    )
                    results.append(error_result)
                    self.stats['files_failed'] += 1
        
        return results
    
    def _process_files_sequential(self, files: List[Path], dry_run: bool) -> List[FileProcessingResult]:
        """Process files sequentially."""
        
        results = []
        
        for i, file_path in enumerate(files):
            try:
                result = self.ingest_file(file_path, dry_run)
                results.append(result)
                
                self.stats['files_processed'] += 1
                if result.success:
                    self.stats['files_successful'] += 1
                else:
                    self.stats['files_failed'] += 1
                
                # Log progress
                if (i + 1) % self.config.progress_update_interval == 0:
                    self.logger.info(f"Processed {i + 1}/{len(files)} files")
                    
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {str(e)}")
                error_result = FileProcessingResult(
                    file_path=file_path,
                    success=False,
                    errors=[str(e)]
                )
                results.append(error_result)
                self.stats['files_failed'] += 1
        
        return results
    
    def _aggregate_results(self, results: List[FileProcessingResult]):
        """Aggregate processing results into statistics."""
        
        total_records_processed = 0
        total_records_inserted = 0
        all_errors = []
        all_warnings = []
        
        for result in results:
            total_records_processed += result.records_processed
            total_records_inserted += result.records_inserted
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)
        
        self.stats['total_records_processed'] = total_records_processed
        self.stats['total_records_inserted'] = total_records_inserted
        
        # Log summary
        self.logger.info(f"Ingestion completed: {self.stats['files_successful']} successful, "
                        f"{self.stats['files_failed']} failed, "
                        f"{total_records_inserted} records inserted")
    
    def _create_summary(self, start_time: datetime) -> IngestionSummary:
        """Create ingestion summary from statistics."""
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return IngestionSummary(
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration=duration,
            files_processed=self.stats['files_processed'],
            files_successful=self.stats['files_successful'],
            files_failed=self.stats['files_failed'],
            total_records_processed=self.stats['total_records_processed'],
            total_records_inserted=self.stats['total_records_inserted'],
            total_records_updated=0,  # TODO: Track updates separately
            total_records_skipped=0,  # TODO: Track skips separately
            performance_metrics={
                'files_per_second': self.stats['files_processed'] / duration if duration > 0 else 0,
                'records_per_second': self.stats['total_records_processed'] / duration if duration > 0 else 0,
                'average_file_size': 0,  # TODO: Calculate from results
                'memory_usage': 0,       # TODO: Track memory usage
            }
        )
    
    def resume_ingestion(
        self, 
        directory: Optional[Path] = None,
        skip_successful: bool = True
    ) -> IngestionSummary:
        """
        Resume ingestion by skipping already processed files.
        
        Args:
            directory: Input directory
            skip_successful: Skip files that were successfully processed
            
        Returns:
            IngestionSummary
        """
        
        directory = directory or self.config.input_directory
        
        # Discover all files
        all_files = discover_argo_files(directory, self.config.file_patterns)
        
        # Filter out already processed files if requested
        if skip_successful:
            files_to_process = []
            
            with self.db_ops.get_session() as session:
                for file_path in all_files:
                    status = self.db_ops.get_ingestion_status(str(file_path), session)
                    
                    if status is None or status.status != 'success':
                        files_to_process.append(file_path)
                    else:
                        self.logger.debug(f"Skipping already processed file: {file_path}")
                        self.stats['files_skipped'] += 1
            
            self.logger.info(f"Resume ingestion: {len(files_to_process)} files to process, "
                           f"{len(all_files) - len(files_to_process)} files skipped")
        else:
            files_to_process = all_files
        
        # Process the remaining files
        return self.ingest_directory(
            directory=directory,
            file_patterns=self.config.file_patterns
        )
    
    def get_ingestion_statistics(self) -> Dict[str, Any]:
        """Get current ingestion statistics."""
        
        with self.db_ops.get_session() as session:
            db_stats = self.db_ops.get_database_stats(session)
        
        return {
            'processing_stats': self.stats,
            'database_stats': db_stats,
            'configuration': {
                'batch_size': self.config.batch_size,
                'max_workers': self.config.max_workers,
                'input_directory': str(self.config.input_directory),
                'file_patterns': self.config.file_patterns,
            }
        }
    
    def cleanup_and_optimize(self, cleanup_days: int = 30) -> Dict[str, Any]:
        """
        Cleanup old logs and optimize database performance.
        
        Args:
            cleanup_days: Remove ingestion logs older than this many days
            
        Returns:
            Dictionary with cleanup and optimization results
        """
        
        results = {}
        
        with self.db_ops.get_session() as session:
            # Cleanup old ingestion logs
            cleaned_logs = self.db_ops.cleanup_old_logs(cleanup_days, session)
            results['cleaned_logs'] = cleaned_logs
            
            # Optimize database
            optimization_results = self.db_ops.optimize_database(session)
            results['optimization'] = optimization_results
        
        return results


def create_ingestion_service(config_path: Optional[Path] = None) -> ArgoIngestionService:
    """
    Create and configure ingestion service.
    
    Args:
        config_path: Path to configuration file (uses defaults if None)
        
    Returns:
        Configured ArgoIngestionService
    """
    
    # Load configuration
    if config_path and config_path.exists():
        # TODO: Implement config file loading
        from .config import load_config_from_env
        config = load_config_from_env()
    else:
        from .config import load_config_from_env
        config = load_config_from_env()
    
    # Setup logging
    setup_ingestion_logging(config)
    
    return ArgoIngestionService(config)


def setup_ingestion_logging(config: IngestionConfig):
    """Setup logging for ingestion operations."""
    
    import logging.handlers
    
    # Create logger
    logger = logging.getLogger('argo_ingestion')
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(config.log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation (if enabled)
    if config.log_to_file:
        log_file = config.log_directory / 'argo_ingestion.log'
        
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when=config.log_rotation,
            backupCount=config.log_retention
        )
        file_formatter = logging.Formatter(config.log_format)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Set level for related loggers
    logging.getLogger('argo_ingestion.parsers').setLevel(logger.level)
    logging.getLogger('argo_ingestion.mappers').setLevel(logger.level)
    logging.getLogger('argo_ingestion.database_ops').setLevel(logger.level)
