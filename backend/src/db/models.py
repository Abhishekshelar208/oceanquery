"""
SQLAlchemy models for OceanQuery database.
"""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    Float, 
    DateTime, 
    Boolean, 
    Text, 
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class ArgoFloat(Base):
    """ARGO float metadata model."""
    __tablename__ = "argo_floats"
    __table_args__ = (
        Index('ix_float_status', 'status'),
        Index('ix_float_project', 'project_name'),
        Index('ix_float_institution', 'institution'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    float_id = Column(String(50), unique=True, nullable=False, index=True)
    platform_number = Column(String(50), index=True)
    wmo_number = Column(String(50), index=True)
    
    # Metadata
    project_name = Column(String(200))
    pi_name = Column(String(200))
    institution = Column(String(200))
    wmo_inst_type = Column(String(50))
    
    # Status and timing
    status = Column(String(20), default='active')  # active, inactive, dead
    deployment_date = Column(DateTime(timezone=True))
    last_contact_date = Column(DateTime(timezone=True))
    
    # Location (last known position)
    last_latitude = Column(Float)
    last_longitude = Column(Float)
    
    # Statistics
    total_profiles = Column(Integer, default=0)
    first_profile_date = Column(DateTime(timezone=True))
    last_profile_date = Column(DateTime(timezone=True))
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    profiles = relationship("ArgoProfile", back_populates="float", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ArgoFloat(float_id='{self.float_id}', status='{self.status}')>"


class ArgoProfile(Base):
    """ARGO profile model (one profile per float cycle)."""
    __tablename__ = "argo_profiles"
    __table_args__ = (
        Index('ix_profile_float_cycle', 'float_id', 'cycle_number'),
        Index('ix_profile_date', 'measurement_date'),
        Index('ix_profile_location', 'latitude', 'longitude'),
        Index('ix_profile_quality', 'quality_flag'),
        CheckConstraint('latitude >= -90 AND latitude <= 90', name='valid_latitude'),
        CheckConstraint('longitude >= -180 AND longitude <= 180', name='valid_longitude'),
        CheckConstraint('cycle_number >= 0', name='valid_cycle_number'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(String(100), unique=True, nullable=False, index=True)
    float_id = Column(String(50), ForeignKey('argo_floats.float_id'), nullable=False, index=True)
    cycle_number = Column(Integer, nullable=False)
    
    # Profile metadata
    measurement_date = Column(DateTime(timezone=True), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Data characteristics
    data_points = Column(Integer, default=0)
    max_pressure = Column(Float)
    min_pressure = Column(Float)
    
    # Quality information
    quality_flag = Column(String(1), default='A')  # A=Accepted, B=Questionable, C=Bad, D=Missing
    data_mode = Column(String(1), default='R')     # R=Real-time, D=Delayed-mode, A=Adjusted
    
    # Processing information
    data_center = Column(String(10))
    processing_date = Column(DateTime(timezone=True))
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    float = relationship("ArgoFloat", back_populates="profiles")
    measurements = relationship("ArgoMeasurement", back_populates="profile", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ArgoProfile(profile_id='{self.profile_id}', date='{self.measurement_date}')>"


class ArgoMeasurement(Base):
    """Individual ARGO measurements at different pressure levels."""
    __tablename__ = "argo_measurements"
    __table_args__ = (
        Index('ix_measurement_profile_pressure', 'profile_id', 'pressure'),
        Index('ix_measurement_temperature', 'temperature'),
        Index('ix_measurement_salinity', 'salinity'),
        Index('ix_measurement_oxygen', 'oxygen'),
        CheckConstraint('pressure >= 0', name='valid_pressure'),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(String(100), ForeignKey('argo_profiles.profile_id'), nullable=False)
    
    # Measurement values
    pressure = Column(Float, nullable=False)  # in dbar
    depth = Column(Float)                     # in meters (calculated from pressure)
    temperature = Column(Float)               # in degrees Celsius
    salinity = Column(Float)                  # Practical Salinity Scale
    oxygen = Column(Float)                    # in µmol/kg
    
    # Additional biogeochemical parameters (if available)
    ph = Column(Float)                        # pH on total scale
    nitrate = Column(Float)                   # µmol/kg
    chlorophyll_a = Column(Float)             # mg/m³
    backscattering = Column(Float)            # m-1
    fluorescence = Column(Float)              # relative units
    
    # Quality flags for each parameter
    pressure_qc = Column(String(1), default='1')      # 1=Good, 2=Probably good, 3=Probably bad, 4=Bad
    temperature_qc = Column(String(1), default='1')
    salinity_qc = Column(String(1), default='1')
    oxygen_qc = Column(String(1), default='1')
    ph_qc = Column(String(1))
    nitrate_qc = Column(String(1))
    chlorophyll_a_qc = Column(String(1))
    
    # Adjusted values (delayed-mode processing)
    temperature_adjusted = Column(Float)
    salinity_adjusted = Column(Float)
    oxygen_adjusted = Column(Float)
    
    # Relationship
    profile = relationship("ArgoProfile", back_populates="measurements")

    def __repr__(self):
        return f"<ArgoMeasurement(profile='{self.profile_id}', pressure={self.pressure})>"


class DataIngestionLog(Base):
    """Log of data ingestion operations."""
    __tablename__ = "data_ingestion_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000))
    file_size = Column(Integer)
    file_hash = Column(String(64))  # SHA-256 hash
    
    # Ingestion details
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Statistics
    profiles_processed = Column(Integer, default=0)
    measurements_processed = Column(Integer, default=0)
    floats_processed = Column(Integer, default=0)
    
    # Processing metadata
    processor_version = Column(String(50))
    processing_parameters = Column(Text)  # JSON string
    
    def __repr__(self):
        return f"<DataIngestionLog(filename='{self.filename}', status='{self.status}')>"


class UserQuery(Base):
    """Log of user queries for analytics and improvement."""
    __tablename__ = "user_queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100))  # From auth system
    session_id = Column(String(100))
    
    # Query details
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text)
    query_type = Column(String(50))  # temperature, salinity, float_info, etc.
    
    # Execution details
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    execution_time_ms = Column(Float)
    results_count = Column(Integer)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # User feedback
    user_rating = Column(Integer)  # 1-5 rating
    user_feedback = Column(Text)
    
    def __repr__(self):
        return f"<UserQuery(id='{self.id}', query_type='{self.query_type}')>"


# Create indexes for common query patterns
Index('ix_measurements_temp_depth', ArgoMeasurement.temperature, ArgoMeasurement.depth)
Index('ix_measurements_sal_depth', ArgoMeasurement.salinity, ArgoMeasurement.depth)
Index('ix_profiles_date_location', ArgoProfile.measurement_date, ArgoProfile.latitude, ArgoProfile.longitude)
Index('ix_floats_last_contact', ArgoFloat.last_contact_date.desc())
Index('ix_queries_user_date', UserQuery.user_id, UserQuery.executed_at.desc())
