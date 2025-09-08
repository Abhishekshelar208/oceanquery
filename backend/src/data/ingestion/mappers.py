"""
Data mappers to convert ARGO profiles to SQLAlchemy models.
"""

import logging
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from ...db.models import ArgoFloat, ArgoProfile as DbArgoProfile, ArgoMeasurement
from .parsers import ArgoProfile
from .config import IngestionConfig, QCFlag

logger = logging.getLogger(__name__)


class ArgoDataMapper:
    """Maps parsed ARGO data to database models."""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Cache for float records to avoid duplicate lookups
        self._float_cache: Dict[str, ArgoFloat] = {}
        
    def clear_cache(self):
        """Clear the float cache."""
        self._float_cache.clear()
        
    def map_profile_to_models(
        self, 
        profile: ArgoProfile, 
        session: Session
    ) -> Tuple[ArgoFloat, DbArgoProfile, List[ArgoMeasurement]]:
        """
        Map a parsed ARGO profile to database models.
        
        Args:
            profile: Parsed ARGO profile
            session: Database session
            
        Returns:
            Tuple of (float_model, profile_model, measurements_list)
        """
        
        # Get or create float record
        float_model = self._get_or_create_float(profile, session)
        
        # Create profile record
        profile_model = self._create_profile_model(profile, float_model)
        
        # Create measurement records
        measurements = self._create_measurement_models(profile, profile_model)
        
        return float_model, profile_model, measurements
    
    def _get_or_create_float(self, profile: ArgoProfile, session: Session) -> ArgoFloat:
        """Get existing float or create new one."""
        
        # Check cache first
        if profile.float_id in self._float_cache:
            return self._float_cache[profile.float_id]
        
        # Query database
        float_model = session.query(ArgoFloat).filter(
            ArgoFloat.float_id == profile.float_id
        ).first()
        
        if float_model is None:
            # Create new float record
            float_model = ArgoFloat(
                float_id=profile.float_id,
                platform_number=profile.platform_number,
                project_name=profile.project_name[:200] if profile.project_name else None,
                pi_name=profile.pi_name[:200] if profile.pi_name else None,
                status='active',  # Default status
                deployment_date=profile.date_time,
                last_contact_date=profile.date_time,
                total_profiles=1,
                first_profile_date=profile.date_time,
                last_profile_date=profile.date_time
            )
            
            self.logger.debug(f"Created new float record: {profile.float_id}")
        else:
            # Update existing float record
            if float_model.last_contact_date is None or profile.date_time > float_model.last_contact_date:
                float_model.last_contact_date = profile.date_time
                float_model.last_latitude = profile.latitude
                float_model.last_longitude = profile.longitude
                
            # Update profile counts and date range
            float_model.total_profiles = (float_model.total_profiles or 0) + 1
            if float_model.first_profile_date is None or profile.date_time < float_model.first_profile_date:
                float_model.first_profile_date = profile.date_time
            if float_model.last_profile_date is None or profile.date_time > float_model.last_profile_date:
                float_model.last_profile_date = profile.date_time
                
            self.logger.debug(f"Updated existing float record: {profile.float_id}")
        
        # Cache the float model
        self._float_cache[profile.float_id] = float_model
        
        return float_model
    
    def _create_profile_model(self, profile: ArgoProfile, float_model: ArgoFloat) -> DbArgoProfile:
        """Create database profile model from parsed profile."""
        
        # Calculate measurement statistics
        n_levels = 0
        max_pressure = None
        
        if profile.pressure is not None:
            valid_pressure = ~np.isnan(profile.pressure)
            n_levels = np.sum(valid_pressure)
            if n_levels > 0:
                max_pressure = float(np.nanmax(profile.pressure))
        
        profile_model = DbArgoProfile(
            profile_id=profile.profile_id,
            float_id=profile.float_id,
            cycle_number=profile.cycle_number,
            data_mode=profile.data_mode,
            latitude=profile.latitude,
            longitude=profile.longitude,
            measurement_date=profile.date_time,
            data_points=n_levels,
            max_pressure=max_pressure,
            min_pressure=float(np.nanmin(profile.pressure)) if profile.pressure is not None and n_levels > 0 else None,
            quality_flag='A' if profile.position_qc == '1' else 'B',  # Map QC to quality flag
            # Reference to float model will be set by SQLAlchemy relationship
        )
        
        return profile_model
    
    def _create_measurement_models(
        self, 
        profile: ArgoProfile, 
        profile_model: DbArgoProfile
    ) -> List[ArgoMeasurement]:
        """Create measurement models from profile data."""
        
        measurements = []
        
        if profile.pressure is None:
            self.logger.warning(f"No pressure data for profile {profile.profile_id}")
            return measurements
        
        n_levels = len(profile.pressure)
        
        for level_idx in range(n_levels):
            # Skip if pressure is invalid
            pressure = profile.pressure[level_idx]
            if np.isnan(pressure):
                continue
                
            # Create measurement record  
            measurement = ArgoMeasurement(
                profile_id=profile.profile_id,
                pressure=float(pressure),
                depth=self._pressure_to_depth(pressure),  # Calculate depth from pressure
            )
            
            # Add pressure QC
            if profile.pressure_qc is not None and level_idx < len(profile.pressure_qc):
                measurement.pressure_qc = str(profile.pressure_qc[level_idx])
            
            # Add temperature data
            self._add_temperature_data(measurement, profile, level_idx)
            
            # Add salinity data
            self._add_salinity_data(measurement, profile, level_idx)
            
            # Add optional measurements
            self._add_optional_measurements(measurement, profile, level_idx)
            
            # Only add measurement if it has valid data
            if self._has_valid_data(measurement):
                measurements.append(measurement)
        
        self.logger.debug(f"Created {len(measurements)} measurements for profile {profile.profile_id}")
        return measurements
    
    def _add_temperature_data(self, measurement: ArgoMeasurement, profile: ArgoProfile, level_idx: int):
        """Add temperature data to measurement."""
        
        # Raw temperature
        if (profile.temperature is not None and 
            level_idx < len(profile.temperature) and 
            not np.isnan(profile.temperature[level_idx])):
            measurement.temperature = float(profile.temperature[level_idx])
            
            if (profile.temperature_qc is not None and 
                level_idx < len(profile.temperature_qc)):
                measurement.temperature_qc = str(profile.temperature_qc[level_idx])
        
        # Adjusted temperature
        if (profile.temperature_adjusted is not None and 
            level_idx < len(profile.temperature_adjusted) and 
            not np.isnan(profile.temperature_adjusted[level_idx])):
            measurement.temperature_adjusted = float(profile.temperature_adjusted[level_idx])
            
            if (profile.temperature_adjusted_qc is not None and 
                level_idx < len(profile.temperature_adjusted_qc)):
                measurement.temperature_adjusted_qc = str(profile.temperature_adjusted_qc[level_idx])
    
    def _add_salinity_data(self, measurement: ArgoMeasurement, profile: ArgoProfile, level_idx: int):
        """Add salinity data to measurement."""
        
        # Raw salinity
        if (profile.salinity is not None and 
            level_idx < len(profile.salinity) and 
            not np.isnan(profile.salinity[level_idx])):
            measurement.salinity = float(profile.salinity[level_idx])
            
            if (profile.salinity_qc is not None and 
                level_idx < len(profile.salinity_qc)):
                measurement.salinity_qc = str(profile.salinity_qc[level_idx])
        
        # Adjusted salinity
        if (profile.salinity_adjusted is not None and 
            level_idx < len(profile.salinity_adjusted) and 
            not np.isnan(profile.salinity_adjusted[level_idx])):
            measurement.salinity_adjusted = float(profile.salinity_adjusted[level_idx])
            
            if (profile.salinity_adjusted_qc is not None and 
                level_idx < len(profile.salinity_adjusted_qc)):
                measurement.salinity_adjusted_qc = str(profile.salinity_adjusted_qc[level_idx])
    
    def _add_optional_measurements(self, measurement: ArgoMeasurement, profile: ArgoProfile, level_idx: int):
        """Add optional measurement data."""
        
        # Oxygen
        if (profile.oxygen is not None and 
            level_idx < len(profile.oxygen) and 
            not np.isnan(profile.oxygen[level_idx])):
            measurement.oxygen = float(profile.oxygen[level_idx])
            
            if (profile.oxygen_qc is not None and 
                level_idx < len(profile.oxygen_qc)):
                measurement.oxygen_qc = str(profile.oxygen_qc[level_idx])
        
        # Chlorophyll
        if (profile.chlorophyll is not None and 
            level_idx < len(profile.chlorophyll) and 
            not np.isnan(profile.chlorophyll[level_idx])):
            measurement.chlorophyll_a = float(profile.chlorophyll[level_idx])
            
            if (profile.chlorophyll_qc is not None and 
                level_idx < len(profile.chlorophyll_qc)):
                measurement.chlorophyll_a_qc = str(profile.chlorophyll_qc[level_idx])
    
    def _has_valid_data(self, measurement: ArgoMeasurement) -> bool:
        """Check if measurement has at least one valid data point."""
        
        # Must have pressure (already checked before calling this)
        if measurement.pressure is None:
            return False
        
        # Check if we have at least one other measurement
        has_temp = measurement.temperature is not None or measurement.temperature_adjusted is not None
        has_sal = measurement.salinity is not None or measurement.salinity_adjusted is not None
        has_oxygen = measurement.oxygen is not None
        has_chl = measurement.chlorophyll_a is not None
        
        return has_temp or has_sal or has_oxygen or has_chl
    
    def _pressure_to_depth(self, pressure: float) -> float:
        """Convert pressure (dbar) to depth (meters) using UNESCO formula."""
        # Simple approximation: depth ≈ pressure / 1.025
        # For more accuracy, use gsw.z_from_p(pressure, latitude)
        return pressure / 1.025
    
    def validate_qc_flags(self, profile: ArgoProfile) -> Dict[str, int]:
        """
        Validate QC flags in the profile and return statistics.
        
        Args:
            profile: ARGO profile to validate
            
        Returns:
            Dictionary with QC flag statistics
        """
        
        stats = {
            'total_measurements': 0,
            'good_quality': 0,
            'questionable_quality': 0,
            'bad_quality': 0,
            'missing_qc': 0
        }
        
        if profile.pressure is None:
            return stats
        
        n_levels = len(profile.pressure)
        stats['total_measurements'] = n_levels
        
        # Check temperature QC
        if profile.temperature_qc is not None:
            for qc_flag in profile.temperature_qc:
                if qc_flag in [QCFlag.GOOD_DATA.value, QCFlag.PROBABLY_GOOD.value]:
                    stats['good_quality'] += 1
                elif qc_flag in [QCFlag.BAD_DATA_CORRECTABLE.value]:
                    stats['questionable_quality'] += 1
                elif qc_flag in [QCFlag.BAD_DATA.value]:
                    stats['bad_quality'] += 1
                else:
                    stats['missing_qc'] += 1
        
        return stats


def batch_map_profiles(
    profiles: List[ArgoProfile],
    config: IngestionConfig,
    session: Session
) -> Dict[str, List[Any]]:
    """
    Map a batch of profiles to database models.
    
    Args:
        profiles: List of parsed ARGO profiles
        config: Ingestion configuration
        session: Database session
        
    Returns:
        Dictionary with lists of models: {'floats': [...], 'profiles': [...], 'measurements': [...]}
    """
    
    mapper = ArgoDataMapper(config)
    
    floats = []
    db_profiles = []
    all_measurements = []
    
    logger.info(f"Mapping {len(profiles)} profiles to database models")
    
    for profile in profiles:
        try:
            float_model, profile_model, measurements = mapper.map_profile_to_models(profile, session)
            
            floats.append(float_model)
            db_profiles.append(profile_model)
            all_measurements.extend(measurements)
            
        except Exception as e:
            logger.error(f"Error mapping profile {profile.profile_id}: {str(e)}", exc_info=True)
            continue
    
    # Remove duplicate floats (keep unique by float_id)
    unique_floats = {}
    for float_model in floats:
        unique_floats[float_model.float_id] = float_model
    
    result = {
        'floats': list(unique_floats.values()),
        'profiles': db_profiles,
        'measurements': all_measurements
    }
    
    logger.info(f"Mapped to {len(result['floats'])} floats, {len(result['profiles'])} profiles, "
               f"{len(result['measurements'])} measurements")
    
    return result


def create_ingestion_log_entry(
    file_path: str,
    success: bool,
    records_processed: int,
    records_inserted: int,
    errors: List[str],
    processing_time: float,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Create an ingestion log entry for database storage."""
    
    return {
        'file_path': file_path,
        'status': 'success' if success else 'failed',
        'records_processed': records_processed,
        'records_inserted': records_inserted,
        'error_count': len(errors),
        'error_messages': errors[:10],  # Limit error messages
        'processing_time': processing_time,
        'ingested_at': datetime.utcnow(),
        'metadata': metadata
    }
