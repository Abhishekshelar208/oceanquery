"""
ARGO measurement data API routes.
Provides endpoints for measurement statistics, profile data, and visualizations.
"""

import base64
import io
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# Import database dependencies
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from core.config import settings
from db.models import ArgoFloat, ArgoProfile, ArgoMeasurement
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

router = APIRouter()

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Response Models
class MeasurementStats(BaseModel):
    """Measurement statistics response model."""
    profile_id: str
    parameter: str
    count: int
    mean: float
    median: float
    std: float
    min_value: float
    max_value: float
    depth_range: Dict[str, float]


class ProfileData(BaseModel):
    """Profile measurement data response model."""
    profile_id: str
    float_id: str
    latitude: float
    longitude: float
    measurement_date: datetime
    measurements: List[Dict[str, Any]]


class PlotResponse(BaseModel):
    """Plot response model."""
    profile_id: str
    plot_type: str
    image_base64: str
    metadata: Dict[str, Any]


@router.get("/stats", response_model=List[MeasurementStats])
async def get_measurement_stats(
    profile_id: Optional[str] = Query(None, description="Specific profile ID"),
    parameter: str = Query("temperature", description="Parameter to analyze"),
    db: Session = Depends(get_db)
):
    """Get measurement statistics for a profile or parameter."""
    
    # Validate parameter
    valid_parameters = ['temperature', 'salinity', 'pressure', 'oxygen']
    if parameter not in valid_parameters:
        raise HTTPException(status_code=400, detail=f"Parameter must be one of: {valid_parameters}")
    
    # Build query
    query = db.query(ArgoMeasurement)
    
    if profile_id:
        query = query.filter(ArgoMeasurement.profile_id == profile_id)
    else:
        # Limit to recent profiles if no specific profile requested
        query = query.limit(1000)
    
    measurements = query.all()
    
    if not measurements:
        raise HTTPException(status_code=404, detail="No measurements found")
    
    # Group by profile and calculate stats
    profile_stats = {}
    
    for measurement in measurements:
        pid = measurement.profile_id
        if pid not in profile_stats:
            profile_stats[pid] = []
        
        # Get parameter value
        value = getattr(measurement, parameter, None)
        if value is not None:
            profile_stats[pid].append({
                'value': float(value),
                'depth': float(measurement.depth) if measurement.depth else 0.0
            })
    
    results = []
    for pid, values in profile_stats.items():
        if not values:
            continue
            
        vals = [v['value'] for v in values]
        depths = [v['depth'] for v in values]
        
        stats = MeasurementStats(
            profile_id=pid,
            parameter=parameter,
            count=len(vals),
            mean=float(np.mean(vals)),
            median=float(np.median(vals)),
            std=float(np.std(vals)),
            min_value=float(np.min(vals)),
            max_value=float(np.max(vals)),
            depth_range={
                "min_depth": float(np.min(depths)),
                "max_depth": float(np.max(depths))
            }
        )
        results.append(stats)
    
    return results


@router.get("/profile/{profile_id}", response_model=ProfileData)
async def get_profile_data(
    profile_id: str,
    db: Session = Depends(get_db)
):
    """Get complete measurement data for a specific profile."""
    
    # Get profile metadata
    profile = db.query(ArgoProfile).filter(ArgoProfile.profile_id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile {profile_id} not found")
    
    # Get measurements
    measurements = db.query(ArgoMeasurement).filter(
        ArgoMeasurement.profile_id == profile_id
    ).order_by(ArgoMeasurement.pressure).all()
    
    if not measurements:
        raise HTTPException(status_code=404, detail=f"No measurements found for profile {profile_id}")
    
    # Format measurements
    measurement_data = []
    for m in measurements:
        measurement_data.append({
            "pressure": float(m.pressure),
            "depth": float(m.depth) if m.depth else None,
            "temperature": float(m.temperature) if m.temperature else None,
            "salinity": float(m.salinity) if m.salinity else None,
            "oxygen": float(m.oxygen) if m.oxygen else None,
            "temperature_qc": m.temperature_qc,
            "salinity_qc": m.salinity_qc,
            "oxygen_qc": m.oxygen_qc
        })
    
    return ProfileData(
        profile_id=profile.profile_id,
        float_id=profile.float_id,
        latitude=profile.latitude,
        longitude=profile.longitude,
        measurement_date=profile.measurement_date,
        measurements=measurement_data
    )


@router.get("/plot/{profile_id}", response_model=PlotResponse)
async def get_profile_plot(
    profile_id: str,
    plot_type: str = Query("temperature", description="Type of plot: temperature, salinity, ts_diagram"),
    width: int = Query(10, description="Plot width in inches"),
    height: int = Query(8, description="Plot height in inches"),
    db: Session = Depends(get_db)
):
    """Generate a plot for a specific profile."""
    
    # Get profile data
    try:
        profile_data = await get_profile_data(profile_id, db)
    except HTTPException as e:
        raise e
    
    measurements = profile_data.measurements
    if not measurements:
        raise HTTPException(status_code=404, detail="No measurements to plot")
    
    # Extract data arrays
    depths = [m['depth'] for m in measurements if m['depth'] is not None]
    temperatures = [m['temperature'] for m in measurements if m['temperature'] is not None]
    salinities = [m['salinity'] for m in measurements if m['salinity'] is not None]
    pressures = [m['pressure'] for m in measurements if m['pressure'] is not None]
    
    # Create plot
    plt.style.use('default')
    fig, ax = plt.subplots(figsize=(width, height))
    
    if plot_type == "temperature" and temperatures and depths:
        ax.plot(temperatures, depths, 'b-', linewidth=2, label='Temperature')
        ax.set_xlabel('Temperature (°C)', fontsize=12)
        ax.set_ylabel('Depth (m)', fontsize=12)
        ax.set_title(f'Temperature Profile - {profile_id}', fontsize=14, fontweight='bold')
        ax.invert_yaxis()  # Deeper is lower
        ax.grid(True, alpha=0.3)
        ax.legend()
        
    elif plot_type == "salinity" and salinities and depths:
        ax.plot(salinities, depths, 'g-', linewidth=2, label='Salinity')
        ax.set_xlabel('Salinity (PSU)', fontsize=12)
        ax.set_ylabel('Depth (m)', fontsize=12)
        ax.set_title(f'Salinity Profile - {profile_id}', fontsize=14, fontweight='bold')
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)
        ax.legend()
        
    elif plot_type == "ts_diagram" and temperatures and salinities:
        scatter = ax.scatter(salinities, temperatures, c=depths, cmap='viridis', s=30)
        ax.set_xlabel('Salinity (PSU)', fontsize=12)
        ax.set_ylabel('Temperature (°C)', fontsize=12)
        ax.set_title(f'T-S Diagram - {profile_id}', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Depth (m)', fontsize=10)
        
    else:
        raise HTTPException(status_code=400, detail=f"Invalid plot_type '{plot_type}' or insufficient data")
    
    # Add metadata text
    metadata_text = f"Lat: {profile_data.latitude:.2f}°, Lon: {profile_data.longitude:.2f}°\n"
    metadata_text += f"Date: {profile_data.measurement_date.strftime('%Y-%m-%d')}\n"
    metadata_text += f"Float: {profile_data.float_id}"
    ax.text(0.02, 0.98, metadata_text, transform=ax.transAxes, fontsize=10, 
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return PlotResponse(
        profile_id=profile_id,
        plot_type=plot_type,
        image_base64=image_base64,
        metadata={
            "latitude": profile_data.latitude,
            "longitude": profile_data.longitude,
            "measurement_date": profile_data.measurement_date.isoformat(),
            "float_id": profile_data.float_id,
            "measurement_count": len(measurements),
            "depth_range": {
                "min": min(depths) if depths else 0,
                "max": max(depths) if depths else 0
            },
            "parameter_ranges": {
                "temperature": {"min": min(temperatures), "max": max(temperatures)} if temperatures else None,
                "salinity": {"min": min(salinities), "max": max(salinities)} if salinities else None
            }
        }
    )


@router.get("/summary")
async def get_measurement_summary(db: Session = Depends(get_db)):
    """Get overall measurement summary statistics."""
    
    # Count measurements by parameter
    total_measurements = db.query(ArgoMeasurement).count()
    
    if total_measurements == 0:
        raise HTTPException(status_code=404, detail="No measurements found")
    
    # Temperature stats
    temp_stats = db.query(
        func.count(ArgoMeasurement.temperature).label('count'),
        func.avg(ArgoMeasurement.temperature).label('mean'),
        func.min(ArgoMeasurement.temperature).label('min'),
        func.max(ArgoMeasurement.temperature).label('max')
    ).filter(ArgoMeasurement.temperature.isnot(None)).first()
    
    # Salinity stats  
    sal_stats = db.query(
        func.count(ArgoMeasurement.salinity).label('count'),
        func.avg(ArgoMeasurement.salinity).label('mean'),
        func.min(ArgoMeasurement.salinity).label('min'),
        func.max(ArgoMeasurement.salinity).label('max')
    ).filter(ArgoMeasurement.salinity.isnot(None)).first()
    
    # Depth stats
    depth_stats = db.query(
        func.count(ArgoMeasurement.depth).label('count'),
        func.avg(ArgoMeasurement.depth).label('mean'),
        func.min(ArgoMeasurement.depth).label('min'),
        func.max(ArgoMeasurement.depth).label('max')
    ).filter(ArgoMeasurement.depth.isnot(None)).first()
    
    # Profile count with measurements
    profiles_with_measurements = db.query(func.count(func.distinct(ArgoMeasurement.profile_id))).scalar()
    
    return {
        "total_measurements": total_measurements,
        "profiles_with_measurements": profiles_with_measurements,
        "parameters": {
            "temperature": {
                "count": temp_stats.count if temp_stats else 0,
                "mean": float(temp_stats.mean) if temp_stats and temp_stats.mean else None,
                "range": {
                    "min": float(temp_stats.min) if temp_stats and temp_stats.min else None,
                    "max": float(temp_stats.max) if temp_stats and temp_stats.max else None
                }
            },
            "salinity": {
                "count": sal_stats.count if sal_stats else 0,
                "mean": float(sal_stats.mean) if sal_stats and sal_stats.mean else None,
                "range": {
                    "min": float(sal_stats.min) if sal_stats and sal_stats.min else None,
                    "max": float(sal_stats.max) if sal_stats and sal_stats.max else None
                }
            },
            "depth": {
                "count": depth_stats.count if depth_stats else 0,
                "mean": float(depth_stats.mean) if depth_stats and depth_stats.mean else None,
                "range": {
                    "min": float(depth_stats.min) if depth_stats and depth_stats.min else None,
                    "max": float(depth_stats.max) if depth_stats and depth_stats.max else None
                }
            }
        },
        "last_updated": datetime.utcnow().isoformat()
    }
