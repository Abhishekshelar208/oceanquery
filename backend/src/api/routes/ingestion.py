"""
FastAPI routes for ARGO data ingestion management.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

from src.data.ingestion.service import create_ingestion_service
from src.data.ingestion.config import create_sample_config, load_config_from_env
from src.db.init_db import get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter()

# Global thread pool for background ingestion tasks
thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ingestion")


class IngestionJobRequest(BaseModel):
    """Request model for starting an ingestion job."""
    
    input_directory: Optional[str] = Field(None, description="Directory containing NetCDF files")
    file_patterns: Optional[List[str]] = Field(None, description="File patterns to match")
    dry_run: bool = Field(False, description="Parse files without database insertion")
    max_workers: Optional[int] = Field(None, description="Override maximum worker threads")
    batch_size: Optional[int] = Field(None, description="Override batch size for processing")
    use_sample_config: bool = Field(False, description="Use sample configuration for testing")


class IngestionJobResponse(BaseModel):
    """Response model for ingestion job status."""
    
    job_id: str
    status: str  # "started", "running", "completed", "failed"
    message: str


class IngestionSummaryResponse(BaseModel):
    """Response model for ingestion summary."""
    
    start_time: str
    end_time: str
    duration: float
    files_processed: int
    files_successful: int
    files_failed: int
    total_records_processed: int
    total_records_inserted: int
    total_records_updated: int
    total_records_skipped: int
    performance_metrics: Dict[str, Any]
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None


class IngestionStatsResponse(BaseModel):
    """Response model for ingestion statistics."""
    
    processing_stats: Dict[str, Any]
    database_stats: Dict[str, Any]
    configuration: Dict[str, Any]


# In-memory job tracking (in production, use Redis or database)
active_jobs: Dict[str, Dict[str, Any]] = {}


async def run_ingestion_job(job_id: str, request: IngestionJobRequest) -> None:
    """Run ingestion job in background thread."""
    
    try:
        active_jobs[job_id]["status"] = "running"
        active_jobs[job_id]["message"] = "Ingestion in progress..."
        
        # Configure ingestion service
        if request.use_sample_config:
            config = create_sample_config()
        else:
            config = load_config_from_env()
        
        # Apply overrides from request
        if request.max_workers:
            config.max_workers = request.max_workers
        if request.batch_size:
            config.batch_size = request.batch_size
        
        service = create_ingestion_service()
        
        # Run ingestion in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        def run_ingestion():
            directory = Path(request.input_directory) if request.input_directory else None
            return service.ingest_directory(
                directory=directory,
                file_patterns=request.file_patterns,
                dry_run=request.dry_run
            )
        
        summary = await loop.run_in_executor(thread_pool, run_ingestion)
        
        # Update job status
        active_jobs[job_id]["status"] = "completed"
        active_jobs[job_id]["message"] = f"Ingestion completed. Processed {summary.total_records_inserted} records."
        active_jobs[job_id]["summary"] = summary
        
        logger.info(f"Ingestion job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {str(e)}", exc_info=True)
        active_jobs[job_id]["status"] = "failed"
        active_jobs[job_id]["message"] = f"Ingestion failed: {str(e)}"
        active_jobs[job_id]["error"] = str(e)


@router.post("/start", response_model=IngestionJobResponse)
async def start_ingestion(
    request: IngestionJobRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(security)
) -> IngestionJobResponse:
    """
    Start an ARGO data ingestion job.
    
    This endpoint starts a background ingestion process that:
    - Discovers NetCDF files in the specified directory
    - Parses and validates ARGO data
    - Inserts data into the database using bulk operations
    - Provides progress tracking and error handling
    """
    
    import uuid
    job_id = str(uuid.uuid4())
    
    # Validate input directory if provided
    if request.input_directory:
        input_path = Path(request.input_directory)
        if not input_path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Input directory does not exist: {request.input_directory}"
            )
        if not input_path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Input path is not a directory: {request.input_directory}"
            )
    
    # Initialize job tracking
    active_jobs[job_id] = {
        "status": "started",
        "message": "Ingestion job queued",
        "request": request.dict(),
        "created_at": asyncio.get_event_loop().time()
    }
    
    # Start background task
    background_tasks.add_task(run_ingestion_job, job_id, request)
    
    logger.info(f"Started ingestion job {job_id}")
    
    return IngestionJobResponse(
        job_id=job_id,
        status="started",
        message="Ingestion job started successfully"
    )


@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
async def get_job_status(
    job_id: str,
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Get the status of a specific ingestion job."""
    
    if job_id not in active_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Ingestion job {job_id} not found"
        )
    
    job = active_jobs[job_id].copy()
    
    # Add runtime information
    current_time = asyncio.get_event_loop().time()
    job["runtime_seconds"] = current_time - job.get("created_at", current_time)
    
    return job


@router.get("/jobs", response_model=List[Dict[str, Any]])
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by job status"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of jobs to return"),
    token: str = Depends(security)
) -> List[Dict[str, Any]]:
    """List recent ingestion jobs."""
    
    jobs = []
    current_time = asyncio.get_event_loop().time()
    
    for job_id, job_data in active_jobs.items():
        if status and job_data.get("status") != status:
            continue
            
        job_info = {
            "job_id": job_id,
            "status": job_data.get("status"),
            "message": job_data.get("message"),
            "created_at": job_data.get("created_at"),
            "runtime_seconds": current_time - job_data.get("created_at", current_time)
        }
        
        # Add summary for completed jobs
        if job_data.get("summary"):
            job_info["summary"] = {
                "files_processed": job_data["summary"].files_processed,
                "records_inserted": job_data["summary"].total_records_inserted,
                "duration": job_data["summary"].duration
            }
        
        jobs.append(job_info)
    
    # Sort by creation time (newest first) and limit
    jobs.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return jobs[:limit]


@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    token: str = Depends(security)
) -> Dict[str, str]:
    """Cancel or remove an ingestion job."""
    
    if job_id not in active_jobs:
        raise HTTPException(
            status_code=404,
            detail=f"Ingestion job {job_id} not found"
        )
    
    job_status = active_jobs[job_id].get("status")
    
    if job_status == "running":
        # Note: Actual cancellation would require more sophisticated task management
        # This is a simplified implementation
        active_jobs[job_id]["status"] = "cancelled"
        active_jobs[job_id]["message"] = "Job cancelled by user"
        return {"message": f"Ingestion job {job_id} marked for cancellation"}
    else:
        # Remove completed/failed jobs
        del active_jobs[job_id]
        return {"message": f"Ingestion job {job_id} removed"}


@router.post("/ingest-file", response_model=Dict[str, Any])
async def ingest_single_file(
    file_path: str,
    dry_run: bool = Query(False, description="Parse file without database insertion"),
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Ingest a single NetCDF file."""
    
    file_path_obj = Path(file_path)
    
    if not file_path_obj.exists():
        raise HTTPException(
            status_code=400,
            detail=f"File does not exist: {file_path}"
        )
    
    if not file_path_obj.is_file():
        raise HTTPException(
            status_code=400,
            detail=f"Path is not a file: {file_path}"
        )
    
    try:
        service = create_ingestion_service()
        result = service.ingest_file(file_path_obj, dry_run=dry_run)
        
        return {
            "file_path": str(result.file_path),
            "success": result.success,
            "records_processed": result.records_processed,
            "records_inserted": result.records_inserted,
            "records_skipped": result.records_skipped,
            "errors": result.errors,
            "warnings": result.warnings,
            "processing_time": result.processing_time,
            "file_size": result.file_size,
        }
    
    except Exception as e:
        logger.error(f"Error ingesting file {file_path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to ingest file: {str(e)}"
        )


@router.get("/stats", response_model=IngestionStatsResponse)
async def get_ingestion_stats(token: str = Depends(security)) -> IngestionStatsResponse:
    """Get current ingestion statistics."""
    
    try:
        service = create_ingestion_service()
        stats = service.get_ingestion_statistics()
        
        return IngestionStatsResponse(
            processing_stats=stats.get("processing_stats", {}),
            database_stats=stats.get("database_stats", {}),
            configuration=stats.get("configuration", {})
        )
    
    except Exception as e:
        logger.error(f"Error getting ingestion stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get ingestion statistics: {str(e)}"
        )


@router.post("/optimize")
async def optimize_database(
    cleanup_days: int = Query(30, ge=1, le=365, description="Days of logs to retain"),
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Optimize database and cleanup old ingestion logs."""
    
    try:
        service = create_ingestion_service()
        result = service.cleanup_and_optimize(cleanup_days=cleanup_days)
        
        return {
            "message": "Database optimization completed",
            "results": result
        }
    
    except Exception as e:
        logger.error(f"Error optimizing database: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize database: {str(e)}"
        )


@router.post("/resume", response_model=IngestionJobResponse)
async def resume_ingestion(
    input_directory: Optional[str] = None,
    skip_successful: bool = Query(True, description="Skip files that were successfully processed"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    token: str = Depends(security)
) -> IngestionJobResponse:
    """Resume interrupted ingestion by skipping already processed files."""
    
    import uuid
    job_id = str(uuid.uuid4())
    
    async def run_resume_job():
        try:
            active_jobs[job_id]["status"] = "running"
            active_jobs[job_id]["message"] = "Resuming ingestion..."
            
            service = create_ingestion_service()
            
            directory = Path(input_directory) if input_directory else None
            loop = asyncio.get_event_loop()
            
            def run_resume():
                return service.resume_ingestion(directory=directory, skip_successful=skip_successful)
            
            summary = await loop.run_in_executor(thread_pool, run_resume)
            
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["message"] = f"Resume completed. Processed {summary.total_records_inserted} records."
            active_jobs[job_id]["summary"] = summary
            
        except Exception as e:
            logger.error(f"Resume job {job_id} failed: {str(e)}", exc_info=True)
            active_jobs[job_id]["status"] = "failed"
            active_jobs[job_id]["message"] = f"Resume failed: {str(e)}"
    
    # Initialize job tracking
    active_jobs[job_id] = {
        "status": "started",
        "message": "Resume ingestion job queued",
        "created_at": asyncio.get_event_loop().time()
    }
    
    # Start background task
    background_tasks.add_task(run_resume_job)
    
    return IngestionJobResponse(
        job_id=job_id,
        status="started",
        message="Resume ingestion job started successfully"
    )


@router.get("/health")
async def ingestion_health() -> Dict[str, Any]:
    """Check ingestion service health and configuration."""
    
    try:
        # Test configuration loading
        config = load_config_from_env()
        
        # Check if input directory exists
        input_dir_exists = config.input_directory.exists() if config.input_directory else False
        
        # Count active jobs
        active_count = len([j for j in active_jobs.values() if j.get("status") == "running"])
        
        return {
            "status": "healthy",
            "service": "argo_ingestion",
            "configuration": {
                "input_directory": str(config.input_directory),
                "input_directory_exists": input_dir_exists,
                "batch_size": config.batch_size,
                "max_workers": config.max_workers,
                "log_level": config.log_level
            },
            "jobs": {
                "active": active_count,
                "total_tracked": len(active_jobs)
            }
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }
