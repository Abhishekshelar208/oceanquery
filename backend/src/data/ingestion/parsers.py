"""
NetCDF parser utilities for ARGO data extraction and validation.
"""

import logging
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Iterator, Any
from dataclasses import dataclass

from .config import (
    IngestionConfig, ValidationConfig, QCFlag, DataMode,
    FileProcessingResult
)

logger = logging.getLogger(__name__)


@dataclass
class ArgoProfile:
    """Represents a single ARGO profile with measurements."""
    
    # Profile metadata
    float_id: str
    cycle_number: int
    profile_id: str
    data_mode: str
    
    # Location and time
    latitude: float
    longitude: float
    date_time: datetime
    
    # Platform information
    platform_number: Optional[str] = None
    project_name: Optional[str] = None
    pi_name: Optional[str] = None
    
    # Measurements (arrays indexed by level)
    pressure: Optional[np.ndarray] = None
    pressure_qc: Optional[np.ndarray] = None
    
    temperature: Optional[np.ndarray] = None
    temperature_qc: Optional[np.ndarray] = None
    temperature_adjusted: Optional[np.ndarray] = None
    temperature_adjusted_qc: Optional[np.ndarray] = None
    
    salinity: Optional[np.ndarray] = None
    salinity_qc: Optional[np.ndarray] = None
    salinity_adjusted: Optional[np.ndarray] = None
    salinity_adjusted_qc: Optional[np.ndarray] = None
    
    # Optional measurements
    oxygen: Optional[np.ndarray] = None
    oxygen_qc: Optional[np.ndarray] = None
    
    chlorophyll: Optional[np.ndarray] = None
    chlorophyll_qc: Optional[np.ndarray] = None
    
    # Quality flags
    position_qc: Optional[str] = None
    date_qc: Optional[str] = None
    
    # Additional metadata
    raw_metadata: Dict[str, Any] = None


class ArgoNetCDFParser:
    """Parser for ARGO NetCDF files with validation and error handling."""
    
    def __init__(self, config: IngestionConfig):
        self.config = config
        self.validation = config.validation
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def parse_file(self, file_path: Path) -> FileProcessingResult:
        """
        Parse a single ARGO NetCDF file.
        
        Args:
            file_path: Path to the NetCDF file
            
        Returns:
            FileProcessingResult with parsed profiles and metadata
        """
        result = FileProcessingResult(
            file_path=file_path,
            success=False,
            file_size=file_path.stat().st_size if file_path.exists() else 0
        )
        
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Parsing file: {file_path}")
            
            # Open and validate NetCDF file
            with xr.open_dataset(file_path) as ds:
                # Validate required variables
                missing_vars = self._validate_required_variables(ds)
                if missing_vars:
                    result.errors.append(f"Missing required variables: {missing_vars}")
                    return result
                
                # Extract file metadata
                result.metadata = self._extract_file_metadata(ds)
                
                # Parse profiles
                profiles = list(self._parse_profiles(ds, result))
                result.records_processed = len(profiles)
                
                # Store parsed profiles in result metadata for further processing
                result.metadata['profiles'] = profiles
                
                result.success = True
                self.logger.info(f"Successfully parsed {len(profiles)} profiles from {file_path}")
                
        except Exception as e:
            error_msg = f"Error parsing file {file_path}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            
        finally:
            result.processing_time = (datetime.now() - start_time).total_seconds()
            
        return result
    
    def _validate_required_variables(self, ds: xr.Dataset) -> List[str]:
        """Validate that all required variables are present in the dataset."""
        available_vars = set(ds.variables.keys())
        required_vars = self.validation.required_variables
        missing_vars = required_vars - available_vars
        
        if missing_vars:
            self.logger.warning(f"Missing required variables: {missing_vars}")
            
        return list(missing_vars)
    
    def _extract_file_metadata(self, ds: xr.Dataset) -> Dict[str, Any]:
        """Extract global metadata from NetCDF file."""
        metadata = {}
        
        # Global attributes
        for attr_name in ds.attrs:
            metadata[f"global_{attr_name}"] = ds.attrs[attr_name]
            
        # Data dimensions
        metadata['dimensions'] = dict(ds.dims)
        
        # Available variables
        metadata['variables'] = list(ds.variables.keys())
        
        # Data creation info
        if 'date_creation' in ds.attrs:
            metadata['file_creation_date'] = ds.attrs['date_creation']
            
        if 'date_update' in ds.attrs:
            metadata['file_update_date'] = ds.attrs['date_update']
            
        return metadata
    
    def _parse_profiles(self, ds: xr.Dataset, result: FileProcessingResult) -> Iterator[ArgoProfile]:
        """Parse individual profiles from the dataset."""
        
        # Determine the number of profiles
        n_prof = ds.dims.get('N_PROF', 0)
        n_levels = ds.dims.get('N_LEVELS', 0)
        
        self.logger.info(f"Processing {n_prof} profiles with {n_levels} levels each")
        
        for prof_idx in range(n_prof):
            try:
                profile = self._parse_single_profile(ds, prof_idx)
                if profile and self._validate_profile(profile, result):
                    yield profile
                else:
                    result.records_skipped += 1
                    
            except Exception as e:
                error_msg = f"Error parsing profile {prof_idx}: {str(e)}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                result.records_skipped += 1
                
                if len(result.errors) >= self.config.max_errors_per_file:
                    self.logger.error(f"Too many errors ({len(result.errors)}), stopping file processing")
                    break
    
    def _parse_single_profile(self, ds: xr.Dataset, prof_idx: int) -> Optional[ArgoProfile]:
        """Parse a single profile from the dataset."""
        
        try:
            # Extract basic profile information
            float_id = self._extract_string_value(ds, 'PLATFORM_NUMBER', prof_idx)
            cycle_number = int(ds['CYCLE_NUMBER'][prof_idx].values)
            
            # Create profile ID
            profile_id = f"{float_id}_{cycle_number}"
            
            # Data mode
            data_mode = self._extract_string_value(ds, 'DATA_MODE', prof_idx, default='R')
            
            # Location and time
            latitude = float(ds['LATITUDE'][prof_idx].values)
            longitude = float(ds['LONGITUDE'][prof_idx].values)
            
            # Convert Julian day to datetime
            julian_day = ds['JULD'][prof_idx].values
            if np.isnan(julian_day):
                self.logger.warning(f"Invalid date for profile {profile_id}")
                return None
                
            date_time = self._julian_to_datetime(julian_day)
            
            # Create profile object
            profile = ArgoProfile(
                float_id=float_id,
                cycle_number=cycle_number,
                profile_id=profile_id,
                data_mode=data_mode,
                latitude=latitude,
                longitude=longitude,
                date_time=date_time,
            )
            
            # Add optional metadata
            profile.platform_number = self._extract_string_value(ds, 'PLATFORM_NUMBER', prof_idx)
            profile.project_name = self._extract_string_value(ds, 'PROJECT_NAME', prof_idx)
            profile.pi_name = self._extract_string_value(ds, 'PI_NAME', prof_idx)
            
            # Extract measurements
            self._extract_measurements(ds, prof_idx, profile)
            
            # Quality flags
            profile.position_qc = self._extract_string_value(ds, 'POSITION_QC', prof_idx)
            profile.date_qc = self._extract_string_value(ds, 'JULD_QC', prof_idx)
            
            return profile
            
        except Exception as e:
            self.logger.error(f"Error parsing profile {prof_idx}: {str(e)}")
            return None
    
    def _extract_measurements(self, ds: xr.Dataset, prof_idx: int, profile: ArgoProfile):
        """Extract measurement arrays for a profile."""
        
        # Pressure (always required)
        if 'PRES' in ds.variables:
            profile.pressure = ds['PRES'][prof_idx].values
            profile.pressure_qc = self._extract_qc_array(ds, 'PRES_QC', prof_idx)
        
        # Temperature
        if 'TEMP' in ds.variables:
            profile.temperature = ds['TEMP'][prof_idx].values
            profile.temperature_qc = self._extract_qc_array(ds, 'TEMP_QC', prof_idx)
            
        if 'TEMP_ADJUSTED' in ds.variables:
            profile.temperature_adjusted = ds['TEMP_ADJUSTED'][prof_idx].values
            profile.temperature_adjusted_qc = self._extract_qc_array(ds, 'TEMP_ADJUSTED_QC', prof_idx)
        
        # Salinity
        if 'PSAL' in ds.variables:
            profile.salinity = ds['PSAL'][prof_idx].values
            profile.salinity_qc = self._extract_qc_array(ds, 'PSAL_QC', prof_idx)
            
        if 'PSAL_ADJUSTED' in ds.variables:
            profile.salinity_adjusted = ds['PSAL_ADJUSTED'][prof_idx].values
            profile.salinity_adjusted_qc = self._extract_qc_array(ds, 'PSAL_ADJUSTED_QC', prof_idx)
        
        # Optional measurements
        if 'DOXY' in ds.variables:
            profile.oxygen = ds['DOXY'][prof_idx].values
            profile.oxygen_qc = self._extract_qc_array(ds, 'DOXY_QC', prof_idx)
            
        if 'CHLA' in ds.variables:
            profile.chlorophyll = ds['CHLA'][prof_idx].values
            profile.chlorophyll_qc = self._extract_qc_array(ds, 'CHLA_QC', prof_idx)
    
    def _extract_string_value(self, ds: xr.Dataset, var_name: str, prof_idx: int, default: str = None) -> Optional[str]:
        """Extract string value from NetCDF variable."""
        if var_name not in ds.variables:
            return default
            
        try:
            value = ds[var_name][prof_idx].values
            if hasattr(value, 'decode'):
                return value.decode('utf-8').strip()
            elif isinstance(value, (np.ndarray, list)) and len(value) > 0:
                # Handle character arrays
                if isinstance(value[0], bytes):
                    return b''.join(value).decode('utf-8').strip()
                else:
                    return ''.join(str(v) for v in value).strip()
            else:
                return str(value).strip() if value is not None else default
        except Exception as e:
            self.logger.debug(f"Error extracting string {var_name}[{prof_idx}]: {e}")
            return default
    
    def _extract_qc_array(self, ds: xr.Dataset, var_name: str, prof_idx: int) -> Optional[np.ndarray]:
        """Extract quality control flag array."""
        if var_name not in ds.variables:
            return None
            
        try:
            qc_data = ds[var_name][prof_idx].values
            # Convert to string array if needed
            if qc_data.dtype.char in ['U', 'S']:  # Unicode or byte string
                return qc_data.astype(str)
            else:
                return qc_data.astype(str)
        except Exception as e:
            self.logger.debug(f"Error extracting QC array {var_name}[{prof_idx}]: {e}")
            return None
    
    def _julian_to_datetime(self, julian_day: float) -> datetime:
        """Convert ARGO Julian day (days since 1950-01-01) to datetime."""
        try:
            # ARGO reference date: 1950-01-01 00:00:00 UTC
            reference_date = datetime(1950, 1, 1, tzinfo=timezone.utc)
            delta_days = pd.Timedelta(days=julian_day)
            return reference_date + delta_days
        except Exception as e:
            self.logger.error(f"Error converting Julian day {julian_day}: {e}")
            raise
    
    def _validate_profile(self, profile: ArgoProfile, result: FileProcessingResult) -> bool:
        """Validate a parsed profile against configuration rules."""
        
        errors = []
        warnings = []
        
        # Geographic bounds
        if not (self.validation.latitude_min <= profile.latitude <= self.validation.latitude_max):
            errors.append(f"Latitude {profile.latitude} out of bounds")
            
        if not (self.validation.longitude_min <= profile.longitude <= self.validation.longitude_max):
            errors.append(f"Longitude {profile.longitude} out of bounds")
        
        # Date validation
        min_date = datetime.fromisoformat(self.validation.min_date).replace(tzinfo=timezone.utc)
        max_date = datetime.fromisoformat(self.validation.max_date).replace(tzinfo=timezone.utc)
        
        if not (min_date <= profile.date_time <= max_date):
            errors.append(f"Date {profile.date_time} out of range")
        
        # Geographic filtering if specified
        if self.config.geographic_bounds:
            bounds = self.config.geographic_bounds
            if not (bounds.get('lat_min', -90) <= profile.latitude <= bounds.get('lat_max', 90)):
                return False
            if not (bounds.get('lon_min', -180) <= profile.longitude <= bounds.get('lon_max', 180)):
                return False
        
        # Date range filtering if specified
        if self.config.date_range:
            start_date = datetime.fromisoformat(self.config.date_range['start']).replace(tzinfo=timezone.utc)
            end_date = datetime.fromisoformat(self.config.date_range['end']).replace(tzinfo=timezone.utc)
            if not (start_date <= profile.date_time <= end_date):
                return False
        
        # Data mode filtering
        if DataMode(profile.data_mode) not in self.config.data_modes:
            return False
        
        # Validate measurement ranges
        if profile.temperature is not None:
            valid_temp = np.logical_and(
                profile.temperature >= self.validation.temp_min,
                profile.temperature <= self.validation.temp_max
            )
            if not np.any(valid_temp):
                warnings.append("No valid temperature measurements")
        
        if profile.salinity is not None:
            valid_sal = np.logical_and(
                profile.salinity >= self.validation.salinity_min,
                profile.salinity <= self.validation.salinity_max
            )
            if not np.any(valid_sal):
                warnings.append("No valid salinity measurements")
        
        # Log validation results
        if errors:
            result.errors.extend([f"Profile {profile.profile_id}: {err}" for err in errors])
            return False
            
        if warnings:
            result.warnings.extend([f"Profile {profile.profile_id}: {warn}" for warn in warnings])
        
        return True


def discover_argo_files(input_directory: Path, patterns: List[str]) -> List[Path]:
    """
    Discover ARGO NetCDF files in the input directory.
    
    Args:
        input_directory: Directory to search
        patterns: File patterns to match
        
    Returns:
        List of discovered file paths
    """
    files = []
    
    for pattern in patterns:
        found_files = list(input_directory.glob(pattern))
        files.extend(found_files)
        
    # Remove duplicates and sort
    unique_files = sorted(set(files))
    
    logger.info(f"Discovered {len(unique_files)} ARGO files in {input_directory}")
    return unique_files


def validate_netcdf_file(file_path: Path) -> Tuple[bool, List[str]]:
    """
    Quick validation of NetCDF file format and structure.
    
    Args:
        file_path: Path to NetCDF file
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    if not file_path.exists():
        errors.append(f"File does not exist: {file_path}")
        return False, errors
    
    if file_path.stat().st_size == 0:
        errors.append(f"File is empty: {file_path}")
        return False, errors
    
    try:
        with xr.open_dataset(file_path) as ds:
            # Check for basic ARGO structure
            required_dims = ['N_PROF']
            missing_dims = [dim for dim in required_dims if dim not in ds.dims]
            if missing_dims:
                errors.append(f"Missing required dimensions: {missing_dims}")
            
            # Check for some core variables
            core_vars = ['LATITUDE', 'LONGITUDE', 'JULD']
            missing_vars = [var for var in core_vars if var not in ds.variables]
            if missing_vars:
                errors.append(f"Missing core variables: {missing_vars}")
                
    except Exception as e:
        errors.append(f"Cannot open NetCDF file: {str(e)}")
        
    return len(errors) == 0, errors
