"""
ARGO data API routes for oceanographic data access.
"""

from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

router = APIRouter()


# Data Models
class ArgoFloat(BaseModel):
    """ARGO float information."""
    float_id: str = Field(..., description="Unique float identifier")
    status: str = Field(..., description="Float status: active, inactive, dead")
    platform_number: Optional[str] = Field(None, description="Platform number")
    project_name: Optional[str] = Field(None, description="Project name")
    pi_name: Optional[str] = Field(None, description="Principal investigator")
    institution: Optional[str] = Field(None, description="Institution")
    wmo_inst_type: Optional[str] = Field(None, description="WMO instrument type")
    first_profile_date: Optional[date] = Field(None, description="Date of first profile")
    last_profile_date: Optional[date] = Field(None, description="Date of last profile")
    total_profiles: int = Field(0, description="Total number of profiles")
    last_position: Optional[dict] = Field(None, description="Last known position")


class ArgoProfile(BaseModel):
    """ARGO profile data."""
    profile_id: str = Field(..., description="Unique profile identifier")
    float_id: str = Field(..., description="Float identifier")
    cycle_number: int = Field(..., description="Cycle number")
    measurement_date: datetime = Field(..., description="Measurement date")
    latitude: float = Field(..., description="Latitude in degrees")
    longitude: float = Field(..., description="Longitude in degrees")
    data_points: int = Field(0, description="Number of data points in profile")
    max_pressure: Optional[float] = Field(None, description="Maximum pressure (depth)")
    quality_flag: Optional[str] = Field(None, description="Data quality flag")


class ArgoMeasurement(BaseModel):
    """Individual ARGO measurement."""
    pressure: float = Field(..., description="Pressure in dbar")
    depth: Optional[float] = Field(None, description="Depth in meters")
    temperature: Optional[float] = Field(None, description="Temperature in °C")
    salinity: Optional[float] = Field(None, description="Practical salinity")
    oxygen: Optional[float] = Field(None, description="Dissolved oxygen")
    quality_flags: Optional[dict] = Field(None, description="Quality flags for each parameter")


class ArgoProfileDetailed(ArgoProfile):
    """Detailed ARGO profile with measurements."""
    measurements: List[ArgoMeasurement] = Field(default=[], description="Profile measurements")


# Query Parameters
class ArgoQueryParams(BaseModel):
    """Parameters for ARGO data queries."""
    min_lat: Optional[float] = Field(None, ge=-90, le=90, description="Minimum latitude")
    max_lat: Optional[float] = Field(None, ge=-90, le=90, description="Maximum latitude")
    min_lon: Optional[float] = Field(None, ge=-180, le=180, description="Minimum longitude")
    max_lon: Optional[float] = Field(None, ge=-180, le=180, description="Maximum longitude")
    start_date: Optional[date] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="End date (YYYY-MM-DD)")
    max_depth: Optional[float] = Field(None, ge=0, description="Maximum depth in meters")
    parameters: Optional[List[str]] = Field(None, description="Parameters to include: temperature, salinity, oxygen")
    quality_control: bool = Field(True, description="Apply quality control filters")


# Mock data for demo
MOCK_FLOATS = [
    ArgoFloat(
        float_id="2902755",
        status="active",
        platform_number="7900522",
        project_name="Indian Ocean ARGO",
        pi_name="Dr. Marine Scientist",
        institution="Indian National Centre for Ocean Information Services",
        wmo_inst_type="863",
        first_profile_date=date(2022, 1, 15),
        last_profile_date=date(2024, 11, 1),
        total_profiles=147,
        last_position={"lat": 10.5, "lon": 77.2, "date": "2024-11-01"}
    ),
    ArgoFloat(
        float_id="2902756",
        status="active",
        platform_number="7900523",
        project_name="Arabian Sea Monitoring",
        pi_name="Dr. Ocean Explorer",
        institution="National Institute of Oceanography",
        wmo_inst_type="863",
        first_profile_date=date(2022, 3, 20),
        last_profile_date=date(2024, 10, 30),
        total_profiles=132,
        last_position={"lat": 8.3, "lon": 73.1, "date": "2024-10-30"}
    )
]


@router.get("/floats", response_model=List[ArgoFloat])
async def get_floats(
    status: Optional[str] = Query(None, description="Filter by status: active, inactive, dead"),
    region: Optional[str] = Query(None, description="Filter by region"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of floats to return"),
    offset: int = Query(0, ge=0, description="Number of floats to skip"),
):
    """Get list of ARGO floats with optional filtering."""
    floats = MOCK_FLOATS.copy()
    
    if status:
        floats = [f for f in floats if f.status == status]
    
    # Apply pagination
    return floats[offset:offset + limit]


@router.get("/floats/{float_id}", response_model=ArgoFloat)
async def get_float(float_id: str):
    """Get detailed information about a specific ARGO float."""
    for float_data in MOCK_FLOATS:
        if float_data.float_id == float_id:
            return float_data
    
    raise HTTPException(status_code=404, detail=f"Float {float_id} not found")


@router.get("/floats/{float_id}/profiles", response_model=List[ArgoProfile])
async def get_float_profiles(
    float_id: str,
    start_date: Optional[date] = Query(None, description="Start date filter"),
    end_date: Optional[date] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of profiles"),
):
    """Get profiles for a specific ARGO float."""
    # Check if float exists
    float_exists = any(f.float_id == float_id for f in MOCK_FLOATS)
    if not float_exists:
        raise HTTPException(status_code=404, detail=f"Float {float_id} not found")
    
    # Mock profiles
    mock_profiles = [
        ArgoProfile(
            profile_id=f"{float_id}_001",
            float_id=float_id,
            cycle_number=1,
            measurement_date=datetime(2024, 11, 1, 12, 0),
            latitude=10.5,
            longitude=77.2,
            data_points=150,
            max_pressure=2000.0,
            quality_flag="A"
        ),
        ArgoProfile(
            profile_id=f"{float_id}_002",
            float_id=float_id,
            cycle_number=2,
            measurement_date=datetime(2024, 10, 22, 12, 0),
            latitude=10.3,
            longitude=77.4,
            data_points=148,
            max_pressure=1950.0,
            quality_flag="A"
        ),
    ]
    
    return mock_profiles[:limit]


@router.get("/profiles/{profile_id}", response_model=ArgoProfileDetailed)
async def get_profile(profile_id: str):
    """Get detailed profile data including all measurements."""
    # Mock detailed profile with measurements
    mock_measurements = [
        ArgoMeasurement(
            pressure=0.0,
            depth=0.0,
            temperature=29.1,
            salinity=35.2,
            oxygen=210.5,
            quality_flags={"temp": "1", "sal": "1", "oxygen": "1"}
        ),
        ArgoMeasurement(
            pressure=10.0,
            depth=10.0,
            temperature=28.9,
            salinity=35.3,
            oxygen=208.2,
            quality_flags={"temp": "1", "sal": "1", "oxygen": "1"}
        ),
        ArgoMeasurement(
            pressure=50.0,
            depth=49.8,
            temperature=26.5,
            salinity=35.1,
            oxygen=195.8,
            quality_flags={"temp": "1", "sal": "1", "oxygen": "1"}
        ),
        ArgoMeasurement(
            pressure=100.0,
            depth=99.3,
            temperature=22.3,
            salinity=34.9,
            oxygen=180.3,
            quality_flags={"temp": "1", "sal": "1", "oxygen": "1"}
        ),
    ]
    
    return ArgoProfileDetailed(
        profile_id=profile_id,
        float_id="2902755",
        cycle_number=1,
        measurement_date=datetime(2024, 11, 1, 12, 0),
        latitude=10.5,
        longitude=77.2,
        data_points=len(mock_measurements),
        max_pressure=100.0,
        quality_flag="A",
        measurements=mock_measurements
    )


@router.post("/search", response_model=List[ArgoProfile])
async def search_profiles(query_params: ArgoQueryParams):
    """Search ARGO profiles with complex filtering."""
    # Mock search results based on parameters
    mock_results = [
        ArgoProfile(
            profile_id="search_001",
            float_id="2902755",
            cycle_number=1,
            measurement_date=datetime(2024, 11, 1, 12, 0),
            latitude=10.5,
            longitude=77.2,
            data_points=150,
            max_pressure=2000.0,
            quality_flag="A"
        ),
        ArgoProfile(
            profile_id="search_002",
            float_id="2902756",
            cycle_number=1,
            measurement_date=datetime(2024, 10, 30, 12, 0),
            latitude=8.3,
            longitude=73.1,
            data_points=145,
            max_pressure=1900.0,
            quality_flag="A"
        ),
    ]
    
    return mock_results


@router.get("/statistics")
async def get_statistics():
    """Get overall ARGO dataset statistics."""
    return {
        "total_floats": 47,
        "active_floats": 42,
        "total_profiles": 23847,
        "coverage": {
            "geographic_bounds": {
                "min_lat": -10.0,
                "max_lat": 30.0,
                "min_lon": 60.0,
                "max_lon": 100.0
            },
            "temporal_range": {
                "start_date": "2020-01-01",
                "end_date": "2024-11-01"
            },
            "depth_range": {
                "min_depth": 0.0,
                "max_depth": 2000.0
            }
        },
        "parameters_available": [
            "temperature",
            "salinity",
            "pressure",
            "oxygen"
        ],
        "data_quality": {
            "good_profiles": 22850,
            "questionable_profiles": 897,
            "bad_profiles": 100
        },
        "last_updated": datetime.utcnow().isoformat()
    }


@router.get("/regions")
async def get_regions():
    """Get predefined oceanographic regions."""
    return {
        "indian_ocean": {
            "name": "Indian Ocean",
            "bounds": {"min_lat": -40, "max_lat": 30, "min_lon": 20, "max_lon": 120},
            "floats": 47,
            "profiles": 23847
        },
        "arabian_sea": {
            "name": "Arabian Sea",
            "bounds": {"min_lat": 10, "max_lat": 25, "min_lon": 60, "max_lon": 78},
            "floats": 18,
            "profiles": 9245
        },
        "bay_of_bengal": {
            "name": "Bay of Bengal",
            "bounds": {"min_lat": 5, "max_lat": 22, "min_lon": 78, "max_lon": 100},
            "floats": 15,
            "profiles": 7832
        },
        "southern_ocean": {
            "name": "Southern Ocean (Indian Sector)",
            "bounds": {"min_lat": -60, "max_lat": -30, "min_lon": 20, "max_lon": 120},
            "floats": 14,
            "profiles": 6770
        }
    }
