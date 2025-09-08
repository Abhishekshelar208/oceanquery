"""
Database operations for bulk insert/upsert with transaction handling.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.dialects.postgresql import insert as postgres_insert

from ...db.models import (
    ArgoFloat, ArgoProfile, ArgoMeasurement, DataIngestionLog
)
from ...db.init_db import get_db_session
from .config import IngestionConfig, FileProcessingResult
from .mappers import create_ingestion_log_entry

logger = logging.getLogger(__name__)


class DatabaseOperations:
    """Handles bulk database operations for ARGO data ingestion."""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def get_session(self):
        """Get database session context manager."""
        return get_db_session()
    
    def bulk_insert_models(
        self, 
        models_dict: Dict[str, List[Any]], 
        session: Session
    ) -> Tuple[int, int, int]:
        """
        Bulk insert models with conflict resolution.
        
        Args:
            models_dict: Dictionary with model lists: {'floats': [...], 'profiles': [...], 'measurements': [...]}
            session: Database session
            
        Returns:
            Tuple of (floats_inserted, profiles_inserted, measurements_inserted)
        """
        
        floats_inserted = 0
        profiles_inserted = 0
        measurements_inserted = 0
        
        try:
            # Insert floats first (they are referenced by profiles)
            if models_dict.get('floats'):
                floats_inserted = self._upsert_floats(models_dict['floats'], session)
                
            # Insert profiles (they are referenced by measurements)
            if models_dict.get('profiles'):
                profiles_inserted = self._upsert_profiles(models_dict['profiles'], session)
                
            # Insert measurements
            if models_dict.get('measurements'):
                measurements_inserted = self._bulk_insert_measurements(
                    models_dict['measurements'], session
                )
            
            self.logger.info(f"Bulk insert completed: {floats_inserted} floats, "
                           f"{profiles_inserted} profiles, {measurements_inserted} measurements")
            
        except Exception as e:
            self.logger.error(f"Error in bulk insert: {str(e)}")
            raise
            
        return floats_inserted, profiles_inserted, measurements_inserted
    
    def _upsert_floats(self, floats: List[ArgoFloat], session: Session) -> int:
        """Upsert float records using PostgreSQL ON CONFLICT."""
        
        if not floats:
            return 0
        
        try:
            # Prepare data for bulk upsert
            float_data = []
            for float_model in floats:
                float_dict = {
                    'float_id': float_model.float_id,
                    'platform_number': float_model.platform_number,
                    'project_name': float_model.project_name,
                    'pi_name': float_model.pi_name,
                    'status': float_model.status,
                    'deployment_date': float_model.deployment_date,
                    'last_contact_date': float_model.last_contact_date,
                    'total_profiles': float_model.total_profiles,
                }
                float_data.append(float_dict)
            
            # Use PostgreSQL UPSERT
            stmt = postgres_insert(ArgoFloat).values(float_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['float_id'],
                set_={
                    'last_contact_date': stmt.excluded.last_contact_date,
                    'total_profiles': stmt.excluded.total_profiles,
                    'status': stmt.excluded.status,
                    'last_profile_date': stmt.excluded.last_profile_date,
                }
            )
            
            result = session.execute(stmt)
            upserted_count = result.rowcount
            
            self.logger.debug(f"Upserted {upserted_count} float records")
            return upserted_count
            
        except Exception as e:
            self.logger.error(f"Error upserting floats: {str(e)}")
            raise
    
    def _upsert_profiles(self, profiles: List[ArgoProfile], session: Session) -> int:
        """Upsert profile records using PostgreSQL ON CONFLICT."""
        
        if not profiles:
            return 0
            
        try:
            # Prepare data for bulk upsert
            profile_data = []
            for profile_model in profiles:
                profile_dict = {
                    'profile_id': profile_model.profile_id,
                    'float_id': profile_model.float_id,
                    'cycle_number': profile_model.cycle_number,
                    'data_mode': profile_model.data_mode,
                    'latitude': profile_model.latitude,
                    'longitude': profile_model.longitude,
                    'measurement_date': profile_model.measurement_date,
                    'data_points': profile_model.data_points,
                    'max_pressure': profile_model.max_pressure,
                    'min_pressure': profile_model.min_pressure,
                    'quality_flag': profile_model.quality_flag,
                }
                profile_data.append(profile_dict)
            
            # Use PostgreSQL UPSERT
            stmt = postgres_insert(ArgoProfile).values(profile_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['profile_id'],
                set_={
                    'data_mode': stmt.excluded.data_mode,
                    'data_points': stmt.excluded.data_points,
                    'max_pressure': stmt.excluded.max_pressure,
                    'min_pressure': stmt.excluded.min_pressure,
                    'quality_flag': stmt.excluded.quality_flag,
                }
            )
            
            result = session.execute(stmt)
            upserted_count = result.rowcount
            
            self.logger.debug(f"Upserted {upserted_count} profile records")
            return upserted_count
            
        except Exception as e:
            self.logger.error(f"Error upserting profiles: {str(e)}")
            raise
    
    def _bulk_insert_measurements(self, measurements: List[ArgoMeasurement], session: Session) -> int:
        """Bulk insert measurement records with batching."""
        
        if not measurements:
            return 0
        
        total_inserted = 0
        batch_size = self.config.batch_size
        
        try:
            # Process in batches to avoid memory issues
            for i in range(0, len(measurements), batch_size):
                batch = measurements[i:i + batch_size]
                
                # Prepare batch data
                measurement_data = []
                for measurement in batch:
                    measurement_dict = {
                        'profile_id': measurement.profile_id,
                        'pressure': measurement.pressure,
                        'depth': measurement.depth,
                        'pressure_qc': measurement.pressure_qc,
                        'temperature': measurement.temperature,
                        'temperature_qc': measurement.temperature_qc,
                        'temperature_adjusted': measurement.temperature_adjusted,
                        'salinity': measurement.salinity,
                        'salinity_qc': measurement.salinity_qc,
                        'salinity_adjusted': measurement.salinity_adjusted,
                        'oxygen': measurement.oxygen,
                        'oxygen_qc': measurement.oxygen_qc,
                        'chlorophyll_a': measurement.chlorophyll_a,
                        'chlorophyll_a_qc': measurement.chlorophyll_a_qc,
                    }
                    measurement_data.append(measurement_dict)
                
                # Use PostgreSQL UPSERT for measurements
                stmt = postgres_insert(ArgoMeasurement).values(measurement_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['profile_id', 'pressure'],
                    set_={
                        'depth': stmt.excluded.depth,
                        'pressure_qc': stmt.excluded.pressure_qc,
                        'temperature': stmt.excluded.temperature,
                        'temperature_qc': stmt.excluded.temperature_qc,
                        'temperature_adjusted': stmt.excluded.temperature_adjusted,
                        'salinity': stmt.excluded.salinity,
                        'salinity_qc': stmt.excluded.salinity_qc,
                        'salinity_adjusted': stmt.excluded.salinity_adjusted,
                        'oxygen': stmt.excluded.oxygen,
                        'oxygen_qc': stmt.excluded.oxygen_qc,
                        'chlorophyll_a': stmt.excluded.chlorophyll_a,
                        'chlorophyll_a_qc': stmt.excluded.chlorophyll_a_qc,
                    }
                )
                
                result = session.execute(stmt)
                batch_inserted = result.rowcount
                total_inserted += batch_inserted
                
                if i % (batch_size * 10) == 0:  # Log every 10 batches
                    self.logger.debug(f"Processed {i + len(batch)} / {len(measurements)} measurements")
            
            self.logger.debug(f"Bulk inserted {total_inserted} measurement records")
            return total_inserted
            
        except Exception as e:
            self.logger.error(f"Error bulk inserting measurements: {str(e)}")
            raise
    
    def log_ingestion_result(self, result: FileProcessingResult, session: Session) -> None:
        """Log ingestion result to database."""
        
        try:
            # Create log entry
            log_entry = create_ingestion_log_entry(
                file_path=str(result.file_path),
                success=result.success,
                records_processed=result.records_processed,
                records_inserted=result.records_inserted,
                errors=result.errors,
                processing_time=result.processing_time,
                metadata=result.metadata
            )
            
            # Insert log record
            log_model = DataIngestionLog(
                filename=Path(log_entry['file_path']).name,
                file_path=log_entry['file_path'],
                status=log_entry['status'],
                profiles_processed=log_entry['records_processed'],
                started_at=log_entry['ingested_at'],
                completed_at=log_entry['ingested_at'] if log_entry['status'] == 'success' else None,
                error_message='\n'.join(log_entry['error_messages']) if log_entry['error_messages'] else None,
            )
            session.add(log_model)
            session.flush()
            
            self.logger.debug(f"Logged ingestion result for {result.file_path}")
            
        except Exception as e:
            self.logger.error(f"Error logging ingestion result: {str(e)}")
            # Don't reraise - logging failures shouldn't break ingestion
    
    def get_ingestion_status(self, file_path: str, session: Session) -> Optional[DataIngestionLog]:
        """Get the latest ingestion status for a file."""
        
        try:
            return session.query(DataIngestionLog)\
                .filter(DataIngestionLog.file_path == file_path)\
                .order_by(DataIngestionLog.started_at.desc())\
                .first()
        except Exception as e:
            self.logger.error(f"Error getting ingestion status: {str(e)}")
            return None
    
    def cleanup_old_logs(self, days: int, session: Session) -> int:
        """Clean up ingestion logs older than specified days."""
        
        try:
            cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            result = session.query(DataIngestionLog)\
                .filter(DataIngestionLog.started_at < cutoff_date)\
                .delete()
            
            self.logger.info(f"Cleaned up {result} old ingestion log entries")
            return result
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {str(e)}")
            return 0
    
    def get_database_stats(self, session: Session) -> Dict[str, Any]:
        """Get database statistics."""
        
        try:
            stats = {}
            
            # Count records
            stats['float_count'] = session.query(ArgoFloat).count()
            stats['profile_count'] = session.query(ArgoProfile).count()
            stats['measurement_count'] = session.query(ArgoMeasurement).count()
            stats['ingestion_log_count'] = session.query(DataIngestionLog).count()
            
            # Get date ranges
            date_range = session.query(
                ArgoProfile.measurement_date.min().label('min_date'),
                ArgoProfile.measurement_date.max().label('max_date')
            ).first()
            
            if date_range and date_range.min_date:
                stats['date_range'] = {
                    'min_date': date_range.min_date.isoformat(),
                    'max_date': date_range.max_date.isoformat() if date_range.max_date else None
                }
            
            # Get geographic bounds
            geo_bounds = session.query(
                ArgoProfile.latitude.min().label('min_lat'),
                ArgoProfile.latitude.max().label('max_lat'),
                ArgoProfile.longitude.min().label('min_lon'),
                ArgoProfile.longitude.max().label('max_lon')
            ).first()
            
            if geo_bounds and geo_bounds.min_lat is not None:
                stats['geographic_bounds'] = {
                    'min_lat': float(geo_bounds.min_lat),
                    'max_lat': float(geo_bounds.max_lat),
                    'min_lon': float(geo_bounds.min_lon),
                    'max_lon': float(geo_bounds.max_lon)
                }
            
            # Get recent ingestion activity
            recent_logs = session.query(DataIngestionLog)\
                .filter(DataIngestionLog.status == 'completed')\
                .order_by(DataIngestionLog.completed_at.desc())\
                .limit(10)\
                .all()
            
            stats['recent_ingestions'] = [
                {
                    'file_path': log.file_path,
                    'records_inserted': log.profiles_processed or 0,
                    'ingested_at': log.completed_at.isoformat() if log.completed_at else log.started_at.isoformat()
                }
                for log in recent_logs
            ]
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting database stats: {str(e)}")
            return {}
    
    def optimize_database(self, session: Session) -> Dict[str, Any]:
        """Optimize database performance (analyze tables, update statistics)."""
        
        try:
            results = {}
            
            # Analyze tables to update statistics
            tables = ['argo_floats', 'argo_profiles', 'argo_measurements']
            
            for table in tables:
                session.execute(text(f"ANALYZE {table}"))
                results[f"{table}_analyzed"] = True
            
            # Vacuum tables if needed (only if user has permissions)
            try:
                for table in tables:
                    session.execute(text(f"VACUUM ANALYZE {table}"))
                    results[f"{table}_vacuumed"] = True
            except Exception as e:
                self.logger.warning(f"Could not vacuum tables (may require superuser): {e}")
                results["vacuum_skipped"] = True
            
            session.commit()
            self.logger.info("Database optimization completed")
            return results
            
        except Exception as e:
            self.logger.error(f"Error optimizing database: {str(e)}")
            session.rollback()
            return {'error': str(e)}


class TransactionManager:
    """Manages database transactions for ingestion operations."""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @contextmanager
    def transaction(self, session: Session, description: str = ""):
        """Context manager for database transactions with rollback on error."""
        
        savepoint = None
        try:
            # Create savepoint for nested transactions
            savepoint = session.begin_nested()
            
            self.logger.debug(f"Starting transaction: {description}")
            yield session
            
            # Commit the savepoint
            savepoint.commit()
            self.logger.debug(f"Committed transaction: {description}")
            
        except Exception as e:
            if savepoint:
                savepoint.rollback()
            self.logger.error(f"Rolling back transaction '{description}': {str(e)}")
            raise
    
    def execute_with_retry(
        self, 
        operation_func, 
        *args, 
        max_retries: Optional[int] = None,
        **kwargs
    ):
        """Execute database operation with retry logic."""
        
        max_retries = max_retries or self.config.max_retries
        retry_delay = self.config.retry_delay
        
        for attempt in range(max_retries + 1):
            try:
                return operation_func(*args, **kwargs)
                
            except (SQLAlchemyError, IntegrityError) as e:
                if attempt == max_retries:
                    self.logger.error(f"Operation failed after {max_retries} retries: {str(e)}")
                    raise
                
                self.logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
                
                if self.config.exponential_backoff:
                    delay = retry_delay * (2 ** attempt)
                else:
                    delay = retry_delay
                
                import time
                time.sleep(delay)
