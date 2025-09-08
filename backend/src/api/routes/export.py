"""
Export API routes for data download and file generation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io
import csv
import json

router = APIRouter()


class ExportFormat(str, Enum):
    """Supported export formats."""
    CSV = "csv"
    JSON = "json"
    NETCDF = "netcdf"
    EXCEL = "excel"


class ExportStatus(str, Enum):
    """Export job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportRequest(BaseModel):
    """Export request model."""
    format: ExportFormat = Field(..., description="Export format")
    query_params: Dict[str, Any] = Field(..., description="Query parameters for data selection")
    filename: Optional[str] = Field(None, description="Custom filename (without extension)")
    include_metadata: bool = Field(True, description="Include metadata in export")
    compress: bool = Field(False, description="Compress the output file")


class ExportJob(BaseModel):
    """Export job model."""
    job_id: str = Field(..., description="Unique job identifier")
    status: ExportStatus = Field(..., description="Current job status")
    format: ExportFormat = Field(..., description="Export format")
    filename: str = Field(..., description="Generated filename")
    created_at: datetime = Field(..., description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    download_url: Optional[str] = Field(None, description="Download URL")
    expires_at: Optional[datetime] = Field(None, description="Download expiration")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# Mock data for exports
MOCK_EXPORT_JOBS = {}
MOCK_DATA = [
    {
        "float_id": "2902755",
        "profile_id": "2902755_001",
        "measurement_date": "2024-11-01T12:00:00Z",
        "latitude": 10.5,
        "longitude": 77.2,
        "pressure": 0.0,
        "depth": 0.0,
        "temperature": 29.1,
        "salinity": 35.2,
        "oxygen": 210.5,
        "quality_flag": "A"
    },
    {
        "float_id": "2902755",
        "profile_id": "2902755_001",
        "measurement_date": "2024-11-01T12:00:00Z",
        "latitude": 10.5,
        "longitude": 77.2,
        "pressure": 10.0,
        "depth": 10.0,
        "temperature": 28.9,
        "salinity": 35.3,
        "oxygen": 208.2,
        "quality_flag": "A"
    },
    {
        "float_id": "2902756",
        "profile_id": "2902756_001",
        "measurement_date": "2024-10-30T12:00:00Z",
        "latitude": 8.3,
        "longitude": 73.1,
        "pressure": 0.0,
        "depth": 0.0,
        "temperature": 28.7,
        "salinity": 35.1,
        "oxygen": 212.1,
        "quality_flag": "A"
    },
]


def generate_csv_data(data: List[Dict[str, Any]]) -> str:
    """Generate CSV data from dictionary list."""
    if not data:
        return ""
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def generate_json_data(data: List[Dict[str, Any]], include_metadata: bool = True) -> str:
    """Generate JSON data with optional metadata."""
    result = {
        "data": data,
    }
    
    if include_metadata:
        result["metadata"] = {
            "total_records": len(data),
            "exported_at": datetime.utcnow().isoformat(),
            "source": "OceanQuery ARGO Database",
            "version": "1.0.0",
            "parameters": list(data[0].keys()) if data else [],
            "quality_info": "A=Accepted, B=Questionable, C=Bad data"
        }
    
    return json.dumps(result, indent=2)


@router.post("/request", response_model=ExportJob)
async def request_export(export_request: ExportRequest, background_tasks: BackgroundTasks):
    """Request a data export job."""
    # Generate job ID
    job_id = f"export_{int(datetime.utcnow().timestamp())}_{len(MOCK_EXPORT_JOBS)}"
    
    # Generate filename
    if export_request.filename:
        filename = f"{export_request.filename}.{export_request.format.value}"
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"oceanquery_data_{timestamp}.{export_request.format.value}"
    
    # Create job
    job = ExportJob(
        job_id=job_id,
        status=ExportStatus.PENDING,
        format=export_request.format,
        filename=filename,
        created_at=datetime.utcnow(),
    )
    
    MOCK_EXPORT_JOBS[job_id] = job
    
    # Start background processing
    background_tasks.add_task(
        process_export_job,
        job_id,
        export_request
    )
    
    return job


def process_export_job(job_id: str, export_request: ExportRequest):
    """Process export job in background."""
    import time
    
    job = MOCK_EXPORT_JOBS[job_id]
    job.status = ExportStatus.PROCESSING
    
    # Simulate processing time
    time.sleep(2)
    
    try:
        # Mock data filtering based on query_params
        filtered_data = MOCK_DATA.copy()  # In real app, apply filters
        
        # Calculate file size (mock)
        if export_request.format == ExportFormat.CSV:
            content = generate_csv_data(filtered_data)
            file_size = len(content.encode('utf-8'))
        elif export_request.format == ExportFormat.JSON:
            content = generate_json_data(filtered_data, export_request.include_metadata)
            file_size = len(content.encode('utf-8'))
        else:
            file_size = 1024 * 50  # Mock size for other formats
        
        # Update job status
        job.status = ExportStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        job.file_size = file_size
        job.download_url = f"/api/v1/export/download/{job_id}"
        job.expires_at = datetime.utcnow().replace(hour=23, minute=59, second=59)  # End of day
        
    except Exception as e:
        job.status = ExportStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()


@router.get("/jobs", response_model=List[ExportJob])
async def get_export_jobs():
    """Get list of user's export jobs."""
    return list(MOCK_EXPORT_JOBS.values())


@router.get("/jobs/{job_id}", response_model=ExportJob)
async def get_export_job(job_id: str):
    """Get specific export job details."""
    if job_id not in MOCK_EXPORT_JOBS:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return MOCK_EXPORT_JOBS[job_id]


@router.delete("/jobs/{job_id}")
async def cancel_export_job(job_id: str):
    """Cancel or delete export job."""
    if job_id not in MOCK_EXPORT_JOBS:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    job = MOCK_EXPORT_JOBS[job_id]
    
    if job.status == ExportStatus.PROCESSING:
        # In real app, cancel the background task
        job.status = ExportStatus.FAILED
        job.error_message = "Job cancelled by user"
        job.completed_at = datetime.utcnow()
    
    del MOCK_EXPORT_JOBS[job_id]
    
    return {"message": f"Export job {job_id} cancelled"}


@router.get("/download/{job_id}")
async def download_export_file(job_id: str):
    """Download completed export file."""
    if job_id not in MOCK_EXPORT_JOBS:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    job = MOCK_EXPORT_JOBS[job_id]
    
    if job.status != ExportStatus.COMPLETED:
        raise HTTPException(
            status_code=400, 
            detail=f"Export job is {job.status.value}, cannot download"
        )
    
    if job.expires_at and datetime.utcnow() > job.expires_at:
        raise HTTPException(status_code=410, detail="Download link has expired")
    
    # Generate file content based on format
    if job.format == ExportFormat.CSV:
        content = generate_csv_data(MOCK_DATA)
        media_type = "text/csv"
    elif job.format == ExportFormat.JSON:
        content = generate_json_data(MOCK_DATA, include_metadata=True)
        media_type = "application/json"
    elif job.format == ExportFormat.NETCDF:
        # Mock NetCDF content (in real app, use xarray to generate)
        content = "Mock NetCDF binary data..."
        media_type = "application/x-netcdf"
    else:
        # Excel or other formats
        content = "Mock Excel data..."
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    # Create streaming response
    content_bytes = content.encode('utf-8') if isinstance(content, str) else content
    
    return StreamingResponse(
        io.BytesIO(content_bytes),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={job.filename}",
            "Content-Length": str(len(content_bytes))
        }
    )


@router.get("/formats")
async def get_export_formats():
    """Get available export formats and their descriptions."""
    return {
        "formats": [
            {
                "format": "csv",
                "name": "Comma-Separated Values",
                "description": "Plain text format suitable for Excel and data analysis tools",
                "file_extension": ".csv",
                "mime_type": "text/csv"
            },
            {
                "format": "json", 
                "name": "JSON",
                "description": "JavaScript Object Notation, ideal for web applications",
                "file_extension": ".json",
                "mime_type": "application/json"
            },
            {
                "format": "netcdf",
                "name": "NetCDF",
                "description": "Network Common Data Form, standard for scientific data",
                "file_extension": ".nc", 
                "mime_type": "application/x-netcdf"
            },
            {
                "format": "excel",
                "name": "Microsoft Excel",
                "description": "Excel spreadsheet format with formatting support",
                "file_extension": ".xlsx",
                "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            }
        ],
        "recommendations": {
            "data_analysis": ["csv", "excel"],
            "scientific_research": ["netcdf", "csv"],
            "web_applications": ["json"],
            "visualization": ["csv", "json"]
        }
    }


@router.get("/templates")
async def get_export_templates():
    """Get predefined export templates."""
    return {
        "templates": [
            {
                "id": "temperature_profile",
                "name": "Temperature Profile",
                "description": "Export temperature measurements with depth",
                "parameters": ["temperature", "pressure", "depth", "latitude", "longitude", "measurement_date"],
                "default_format": "csv"
            },
            {
                "id": "salinity_analysis", 
                "name": "Salinity Analysis",
                "description": "Export salinity data for water mass analysis",
                "parameters": ["salinity", "temperature", "pressure", "latitude", "longitude", "measurement_date"],
                "default_format": "netcdf"
            },
            {
                "id": "float_trajectory",
                "name": "Float Trajectory",
                "description": "Export float positions and metadata",
                "parameters": ["float_id", "latitude", "longitude", "measurement_date", "cycle_number"],
                "default_format": "json"
            },
            {
                "id": "quality_controlled",
                "name": "Quality Controlled Data",
                "description": "Export only high-quality measurements",
                "parameters": ["temperature", "salinity", "pressure", "oxygen", "quality_flag"],
                "filters": {"quality_flag": ["A"]},
                "default_format": "csv"
            }
        ]
    }
