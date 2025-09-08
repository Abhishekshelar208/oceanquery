"""
Unit tests for ARGO NetCDF data ingestion pipeline.
"""

import pytest
import numpy as np
import xarray as xr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from tempfile import NamedTemporaryFile

from src.data.ingestion.config import (
    IngestionConfig, ValidationConfig, QCFlag, DataMode,
    FileProcessingResult, create_sample_config
)
from src.data.ingestion.parsers import (
    ArgoProfile, ArgoNetCDFParser, discover_argo_files, validate_netcdf_file
)
from src.data.ingestion.mappers import ArgoDataMapper, batch_map_profiles
from src.data.ingestion.database_ops import DatabaseOperations
from src.data.ingestion.service import ArgoIngestionService
from src.db.models import ArgoFloat, ArgoProfile as DbArgoProfile, ArgoMeasurement


class TestIngestionConfig:
    """Test ingestion configuration classes."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = IngestionConfig()
        assert config.batch_size == 1000
        assert config.max_workers == 4
        assert len(config.validation.required_variables) == 6
        assert QCFlag.GOOD_DATA in config.validation.accepted_qc_flags
    
    def test_validation_config(self):
        """Test validation configuration."""
        validation = ValidationConfig()
        assert validation.temp_min == -5.0
        assert validation.temp_max == 40.0
        assert validation.salinity_max == 45.0
        assert validation.pressure_max == 12000.0
    
    def test_sample_config(self):
        """Test sample configuration creation."""
        config = create_sample_config()
        assert config.batch_size == 500
        assert config.max_workers == 2
        assert config.geographic_bounds is not None
        assert config.date_range is not None
    
    @patch.dict('os.environ', {
        'ARGO_BATCH_SIZE': '2000',
        'ARGO_MAX_WORKERS': '8',
        'ARGO_LOG_LEVEL': 'DEBUG'
    })
    def test_config_from_env(self):
        """Test configuration loading from environment variables."""
        from src.data.ingestion.config import load_config_from_env
        config = load_config_from_env()
        assert config.batch_size == 2000
        assert config.max_workers == 8
        assert config.log_level == 'DEBUG'


class TestArgoNetCDFParser:
    """Test NetCDF parsing functionality."""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        return create_sample_config()
    
    @pytest.fixture
    def parser(self, sample_config):
        """Create parser instance for testing."""
        return ArgoNetCDFParser(sample_config)
    
    @pytest.fixture
    def mock_netcdf_dataset(self):
        """Create mock NetCDF dataset for testing."""
        # Create sample data arrays
        n_prof = 2
        n_levels = 50
        
        # Create coordinate arrays
        juld = np.array([25000.5, 25010.7])  # Julian days since 1950-01-01
        latitude = np.array([45.5, 45.6])
        longitude = np.array([-125.2, -125.1])
        pressure = np.random.uniform(0, 1000, (n_prof, n_levels))
        
        # Create measurement arrays
        temperature = np.random.uniform(2, 15, (n_prof, n_levels))
        salinity = np.random.uniform(34, 36, (n_prof, n_levels))
        oxygen = np.random.uniform(200, 300, (n_prof, n_levels))
        
        # Create QC arrays
        temp_qc = np.full((n_prof, n_levels), '1', dtype='<U1')
        sal_qc = np.full((n_prof, n_levels), '1', dtype='<U1')
        
        # Create string arrays
        platform_number = np.array([['7', '9', '0', '0', '5', '2', '2'], 
                                   ['7', '9', '0', '0', '5', '2', '3']], dtype='<U1')
        data_mode = np.array(['R', 'D'], dtype='<U1')
        
        # Create mock dataset
        dataset = Mock(spec=xr.Dataset)
        dataset.dims = {'N_PROF': n_prof, 'N_LEVELS': n_levels}
        dataset.variables = {
            'JULD', 'LATITUDE', 'LONGITUDE', 'PRES', 'TEMP', 'PSAL',
            'DOXY', 'TEMP_QC', 'PSAL_QC', 'PLATFORM_NUMBER', 'DATA_MODE',
            'CYCLE_NUMBER'
        }
        dataset.attrs = {
            'date_creation': '2023-11-01T00:00:00Z',
            'institution': 'TEST_INSTITUTION'
        }
        
        # Mock data access
        def getitem_side_effect(key):
            mock_var = Mock()
            if key == 'JULD':
                mock_var.__getitem__.return_value.values = juld
                return mock_var
            elif key == 'LATITUDE':
                mock_var.__getitem__.return_value.values = latitude
                return mock_var
            elif key == 'LONGITUDE':
                mock_var.__getitem__.return_value.values = longitude
                return mock_var
            elif key == 'PRES':
                mock_var.__getitem__.return_value.values = pressure
                return mock_var
            elif key == 'TEMP':
                mock_var.__getitem__.return_value.values = temperature
                return mock_var
            elif key == 'PSAL':
                mock_var.__getitem__.return_value.values = salinity
                return mock_var
            elif key == 'DOXY':
                mock_var.__getitem__.return_value.values = oxygen
                return mock_var
            elif key == 'PLATFORM_NUMBER':
                mock_var.__getitem__.return_value.values = platform_number
                return mock_var
            elif key == 'DATA_MODE':
                mock_var.__getitem__.return_value.values = data_mode
                return mock_var
            elif key == 'CYCLE_NUMBER':
                mock_var.__getitem__.return_value.values = np.array([1, 2])
                return mock_var
            elif key in ['TEMP_QC', 'PSAL_QC']:
                mock_var.__getitem__.return_value.values = temp_qc
                return mock_var
            else:
                raise KeyError(key)
        
        dataset.__getitem__.side_effect = getitem_side_effect
        return dataset
    
    def test_julian_to_datetime(self, parser):
        """Test Julian day to datetime conversion."""
        # Test known Julian day value
        julian_day = 25000.5  # Approximately 2018-06-14
        result = parser._julian_to_datetime(julian_day)
        
        assert isinstance(result, datetime)
        assert result.year == 2018
        assert result.month == 6
        assert result.day == 14
        assert result.tzinfo == timezone.utc
    
    def test_extract_string_value(self, parser):
        """Test string value extraction from NetCDF variables."""
        # Mock dataset
        mock_dataset = Mock()
        mock_var = Mock()
        
        # Test character array extraction
        char_array = np.array(['7', '9', '0', '0', '5', '2', '2'])
        mock_var.__getitem__.return_value.values = char_array
        mock_dataset.__getitem__.return_value = mock_var
        
        result = parser._extract_string_value(mock_dataset, 'TEST_VAR', 0)
        assert result == '7900522'
    
    def test_validate_required_variables(self, parser, mock_netcdf_dataset):
        """Test validation of required NetCDF variables."""
        missing_vars = parser._validate_required_variables(mock_netcdf_dataset)
        assert len(missing_vars) == 0  # All required variables present
        
        # Test with missing variables
        mock_netcdf_dataset.variables = {'LATITUDE', 'LONGITUDE'}  # Missing others
        missing_vars = parser._validate_required_variables(mock_netcdf_dataset)
        assert len(missing_vars) > 0
        assert 'JULD' in missing_vars
    
    @patch('xarray.open_dataset')
    def test_parse_file_success(self, mock_open_dataset, parser, mock_netcdf_dataset):
        """Test successful file parsing."""
        mock_open_dataset.return_value.__enter__.return_value = mock_netcdf_dataset
        
        test_file = Path('/test/file.nc')
        with patch.object(test_file, 'stat') as mock_stat:
            mock_stat.return_value.st_size = 1000
            with patch.object(test_file, 'exists', return_value=True):
                result = parser.parse_file(test_file)
        
        assert isinstance(result, FileProcessingResult)
        assert result.success
        assert result.records_processed > 0
        assert 'profiles' in result.metadata
    
    def test_profile_validation(self, parser):
        """Test profile validation against configuration rules."""
        # Create valid profile
        valid_profile = ArgoProfile(
            float_id='7900522',
            cycle_number=1,
            profile_id='7900522_001',
            data_mode='R',
            latitude=45.5,
            longitude=-125.2,
            date_time=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        result = FileProcessingResult(Path('/test/file.nc'), True)
        assert parser._validate_profile(valid_profile, result) is True
        
        # Test invalid latitude
        invalid_profile = ArgoProfile(
            float_id='7900522',
            cycle_number=1,
            profile_id='7900522_002',
            data_mode='R',
            latitude=95.0,  # Invalid latitude
            longitude=-125.2,
            date_time=datetime(2023, 1, 1, tzinfo=timezone.utc)
        )
        
        result = FileProcessingResult(Path('/test/file.nc'), True)
        assert parser._validate_profile(invalid_profile, result) is False
        assert len(result.errors) > 0


class TestArgoDataMapper:
    """Test data mapping to database models."""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        return create_sample_config()
    
    @pytest.fixture
    def mapper(self, sample_config):
        """Create mapper instance for testing."""
        return ArgoDataMapper(sample_config)
    
    @pytest.fixture
    def sample_profile(self):
        """Create sample ARGO profile for testing."""
        return ArgoProfile(
            float_id='7900522',
            cycle_number=1,
            profile_id='7900522_001',
            data_mode='R',
            latitude=45.5,
            longitude=-125.2,
            date_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            platform_number='7900522',
            project_name='Test Project',
            pi_name='Test Scientist',
            pressure=np.array([0.0, 10.0, 20.0, 30.0]),
            temperature=np.array([15.0, 14.5, 14.0, 13.5]),
            salinity=np.array([35.0, 35.1, 35.2, 35.3]),
            temperature_qc=np.array(['1', '1', '1', '1']),
            salinity_qc=np.array(['1', '1', '1', '1'])
        )
    
    def test_pressure_to_depth_conversion(self, mapper):
        """Test pressure to depth conversion."""
        pressure = 1000.0  # 1000 dbar
        depth = mapper._pressure_to_depth(pressure)
        assert abs(depth - 975.6) < 1.0  # Approximately 975.6 meters
    
    def test_float_model_creation(self, mapper, sample_profile):
        """Test ArgoFloat model creation."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        float_model = mapper._get_or_create_float(sample_profile, mock_session)
        
        assert isinstance(float_model, ArgoFloat)
        assert float_model.float_id == '7900522'
        assert float_model.platform_number == '7900522'
        assert float_model.project_name == 'Test Project'
        assert float_model.pi_name == 'Test Scientist'
        assert float_model.status == 'active'
    
    def test_profile_model_creation(self, mapper, sample_profile):
        """Test ArgoProfile model creation."""
        # Create mock float
        mock_float = ArgoFloat(float_id='7900522')
        
        profile_model = mapper._create_profile_model(sample_profile, mock_float)
        
        assert isinstance(profile_model, DbArgoProfile)
        assert profile_model.profile_id == '7900522_001'
        assert profile_model.float_id == '7900522'
        assert profile_model.cycle_number == 1
        assert profile_model.data_mode == 'R'
        assert profile_model.latitude == 45.5
        assert profile_model.longitude == -125.2
        assert profile_model.data_points == 4  # Number of valid pressure levels
    
    def test_measurement_model_creation(self, mapper, sample_profile):
        """Test ArgoMeasurement model creation."""
        # Create mock profile
        mock_profile = DbArgoProfile(profile_id='7900522_001')
        
        measurements = mapper._create_measurement_models(sample_profile, mock_profile)
        
        assert len(measurements) == 4  # 4 pressure levels
        
        for i, measurement in enumerate(measurements):
            assert isinstance(measurement, ArgoMeasurement)
            assert measurement.profile_id == '7900522_001'
            assert measurement.pressure == sample_profile.pressure[i]
            assert measurement.temperature == sample_profile.temperature[i]
            assert measurement.salinity == sample_profile.salinity[i]
            assert measurement.temperature_qc == '1'
            assert measurement.salinity_qc == '1'
            assert measurement.depth is not None
    
    def test_has_valid_data(self, mapper):
        """Test measurement validity checking."""
        # Valid measurement with temperature
        valid_measurement = ArgoMeasurement(
            profile_id='test',
            pressure=10.0,
            temperature=15.0,
            depth=10.0
        )
        assert mapper._has_valid_data(valid_measurement) is True
        
        # Invalid measurement with only pressure
        invalid_measurement = ArgoMeasurement(
            profile_id='test',
            pressure=10.0,
            depth=10.0
        )
        assert mapper._has_valid_data(invalid_measurement) is False
    
    def test_qc_flag_validation(self, mapper, sample_profile):
        """Test QC flag validation and statistics."""
        stats = mapper.validate_qc_flags(sample_profile)
        
        assert stats['total_measurements'] == 4
        assert stats['good_quality'] == 4  # All QC flags are '1'
        assert stats['questionable_quality'] == 0
        assert stats['bad_quality'] == 0


class TestDatabaseOperations:
    """Test database operations for bulk insert/upsert."""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        return create_sample_config()
    
    @pytest.fixture
    def db_ops(self, sample_config):
        """Create database operations instance for testing."""
        return DatabaseOperations(sample_config)
    
    def test_database_operations_init(self, db_ops):
        """Test DatabaseOperations initialization."""
        assert db_ops.config is not None
        assert db_ops.logger is not None
    
    @patch('src.data.ingestion.database_ops.get_db_session')
    def test_get_session_context_manager(self, mock_get_db_session, db_ops):
        """Test database session context manager."""
        mock_session = Mock()
        mock_get_db_session.return_value = mock_session
        
        with db_ops.get_session() as session:
            assert session == mock_session
        
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
    
    def test_bulk_insert_models_structure(self, db_ops):
        """Test bulk insert models structure validation."""
        # Create sample models dictionary
        models_dict = {
            'floats': [Mock(spec=ArgoFloat)],
            'profiles': [Mock(spec=DbArgoProfile)],
            'measurements': [Mock(spec=ArgoMeasurement) for _ in range(5)]
        }
        
        mock_session = Mock()
        
        # Mock the upsert methods
        with patch.object(db_ops, '_upsert_floats', return_value=1) as mock_upsert_floats:
            with patch.object(db_ops, '_upsert_profiles', return_value=1) as mock_upsert_profiles:
                with patch.object(db_ops, '_bulk_insert_measurements', return_value=5) as mock_bulk_measurements:
                    floats_inserted, profiles_inserted, measurements_inserted = \
                        db_ops.bulk_insert_models(models_dict, mock_session)
        
        assert floats_inserted == 1
        assert profiles_inserted == 1
        assert measurements_inserted == 5
        
        mock_upsert_floats.assert_called_once()
        mock_upsert_profiles.assert_called_once()
        mock_bulk_measurements.assert_called_once()


class TestArgoIngestionService:
    """Test the main ingestion service."""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        return create_sample_config()
    
    @pytest.fixture
    def service(self, sample_config):
        """Create ingestion service for testing."""
        return ArgoIngestionService(sample_config)
    
    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service.config is not None
        assert service.parser is not None
        assert service.db_ops is not None
        assert service.transaction_mgr is not None
        assert 'files_processed' in service.stats
    
    def test_statistics_tracking(self, service):
        """Test statistics tracking functionality."""
        initial_stats = service.stats.copy()
        
        # Simulate processing
        service.stats['files_processed'] = 5
        service.stats['files_successful'] = 4
        service.stats['files_failed'] = 1
        service.stats['total_records_processed'] = 1000
        
        assert service.stats['files_processed'] == 5
        assert service.stats['files_successful'] == 4
        assert service.stats['files_failed'] == 1
        assert service.stats['total_records_processed'] == 1000
    
    @patch('src.data.ingestion.service.discover_argo_files')
    def test_ingest_directory_no_files(self, mock_discover, service):
        """Test directory ingestion when no files are found."""
        mock_discover.return_value = []
        
        summary = service.ingest_directory(dry_run=True)
        
        assert summary.files_processed == 0
        assert summary.total_records_processed == 0
        mock_discover.assert_called_once()
    
    @patch('src.data.ingestion.service.validate_netcdf_file')
    def test_ingest_file_invalid(self, mock_validate, service):
        """Test ingestion of invalid NetCDF file."""
        mock_validate.return_value = (False, ['Invalid NetCDF format'])
        
        test_file = Path('/test/invalid.nc')
        result = service.ingest_file(test_file, dry_run=True)
        
        assert result.success is False
        assert len(result.errors) > 0
        assert 'Invalid NetCDF format' in result.errors


class TestFileDiscoveryAndValidation:
    """Test file discovery and validation utilities."""
    
    def test_discover_argo_files(self):
        """Test ARGO file discovery."""
        # Create temporary directory with mock files
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create some test files
            (temp_path / 'profile1.nc').touch()
            (temp_path / 'profile2.nc').touch()
            (temp_path / 'other.txt').touch()
            
            # Create subdirectory
            sub_dir = temp_path / 'subdir'
            sub_dir.mkdir()
            (sub_dir / 'profile3.nc').touch()
            
            # Test file discovery
            files = discover_argo_files(temp_path, ['*.nc', '**/*.nc'])
            
            # Should find all .nc files
            nc_files = [f for f in files if f.suffix == '.nc']
            assert len(nc_files) >= 2  # At least profile1.nc and profile2.nc
    
    def test_validate_netcdf_file_nonexistent(self):
        """Test validation of non-existent file."""
        non_existent = Path('/path/to/nonexistent.nc')
        is_valid, errors = validate_netcdf_file(non_existent)
        
        assert is_valid is False
        assert len(errors) > 0
        assert 'does not exist' in errors[0]
    
    def test_validate_netcdf_file_empty(self):
        """Test validation of empty file."""
        with NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
        
        try:
            is_valid, errors = validate_netcdf_file(temp_path)
            assert is_valid is False
            assert any('empty' in error for error in errors)
        finally:
            temp_path.unlink()


class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample configuration for testing."""
        config = create_sample_config()
        config.batch_size = 10  # Small batch for testing
        config.max_workers = 1   # Single worker for predictable testing
        return config
    
    def test_end_to_end_dry_run(self, sample_config):
        """Test end-to-end pipeline in dry run mode."""
        service = ArgoIngestionService(sample_config)
        
        # Mock the file discovery to return empty list
        with patch('src.data.ingestion.service.discover_argo_files', return_value=[]):
            summary = service.ingest_directory(dry_run=True)
        
        assert summary.files_processed == 0
        assert summary.duration >= 0
        assert summary.start_time is not None
        assert summary.end_time is not None
    
    def test_configuration_consistency(self):
        """Test that all configuration classes work together consistently."""
        config = IngestionConfig()
        
        # Test that validation config is properly integrated
        assert config.validation is not None
        assert isinstance(config.validation, ValidationConfig)
        
        # Test that QC flags are properly defined
        qc_flags = config.validation.accepted_qc_flags
        assert QCFlag.GOOD_DATA in qc_flags
        assert QCFlag.PROBABLY_GOOD in qc_flags
        
        # Test that data modes are properly defined
        data_modes = config.data_modes
        assert DataMode.REAL_TIME in data_modes
        assert DataMode.DELAYED_MODE in data_modes


# Performance and stress tests
class TestPerformance:
    """Performance and stress tests."""
    
    def test_large_profile_processing(self):
        """Test processing of profiles with many measurements."""
        config = create_sample_config()
        mapper = ArgoDataMapper(config)
        
        # Create profile with many measurements
        n_levels = 1000
        large_profile = ArgoProfile(
            float_id='test_float',
            cycle_number=1,
            profile_id='test_profile',
            data_mode='R',
            latitude=45.0,
            longitude=-125.0,
            date_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
            pressure=np.linspace(0, 2000, n_levels),
            temperature=np.random.uniform(2, 15, n_levels),
            salinity=np.random.uniform(34, 36, n_levels),
            temperature_qc=np.full(n_levels, '1', dtype='<U1'),
            salinity_qc=np.full(n_levels, '1', dtype='<U1')
        )
        
        # Create mock profile model
        mock_profile = DbArgoProfile(profile_id='test_profile')
        
        # Test that we can process large numbers of measurements
        measurements = mapper._create_measurement_models(large_profile, mock_profile)
        
        assert len(measurements) == n_levels
        assert all(isinstance(m, ArgoMeasurement) for m in measurements)
    
    def test_batch_processing_efficiency(self):
        """Test that batch processing handles multiple profiles efficiently."""
        config = create_sample_config()
        
        # Create multiple profiles
        profiles = []
        for i in range(10):
            profile = ArgoProfile(
                float_id=f'test_float_{i}',
                cycle_number=1,
                profile_id=f'test_profile_{i}',
                data_mode='R',
                latitude=45.0 + i * 0.1,
                longitude=-125.0 + i * 0.1,
                date_time=datetime(2023, 1, i+1, tzinfo=timezone.utc),
                pressure=np.array([10.0, 20.0, 30.0]),
                temperature=np.array([15.0, 14.0, 13.0]),
                salinity=np.array([35.0, 35.1, 35.2])
            )
            profiles.append(profile)
        
        # Mock session
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test batch mapping
        models_dict = batch_map_profiles(profiles, config, mock_session)
        
        assert len(models_dict['profiles']) == 10
        assert len(models_dict['floats']) == 10  # Each profile creates a unique float
        assert len(models_dict['measurements']) == 30  # 10 profiles * 3 measurements each


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
