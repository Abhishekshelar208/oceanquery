"""
Main FastAPI application for OceanQuery backend.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import auth, export, ingestion, measurements
from src.api.routes import argo_real as argo
from src.api.routes import chat_real as chat
from src.core.config import settings


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("🌊 OceanQuery API starting up...")
    logger.info(f"Environment: {'Development' if settings.is_development else 'Production'}")
    
    # TODO: Initialize database connections
    # TODO: Initialize vector stores
    # TODO: Warm up ML models
    
    yield
    
    # Shutdown
    logger.info("🌊 OceanQuery API shutting down...")
    # TODO: Close database connections
    # TODO: Cleanup resources


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
    🌊 **OceanQuery API** - AI-powered ocean data exploration platform
    
    This API provides endpoints for:
    
    * **Natural language chat** with ocean data
    * **ARGO float data** querying and visualization  
    * **Data export** in various formats
    * **Authentication** and user management
    
    Built for researchers, students, and marine data enthusiasts.
    """,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
    lifespan=lifespan,
)

# Add security middleware
if not settings.is_development:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["oceanquery.app", "*.oceanquery.app", "localhost"],
    )

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error on {request.method} {request.url}: {exc}", exc_info=True)
    
    if settings.is_development:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "Something went wrong. Please try again later.",
            },
        )


# Health check endpoint
@app.get(
    settings.health_check_endpoint,
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and healthy.",
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": "development" if settings.is_development else "production",
    }


# Root endpoint
@app.get("/", tags=["Root"], summary="API Root")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "🌊 Welcome to OceanQuery API",
        "description": "AI-powered ocean data exploration platform",
        "version": settings.app_version,
        "docs": "/docs" if settings.is_development else "https://docs.oceanquery.app",
        "status": "operational",
    }


# Include API routers
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["AI Chat"],
)

app.include_router(
    argo.router,
    prefix="/api/v1/argo",
    tags=["ARGO Data"],
)

app.include_router(
    export.router,
    prefix="/api/v1/export",
    tags=["Data Export"],
)

app.include_router(
    ingestion.router,
    prefix="/api/v1/ingestion",
    tags=["Data Ingestion"],
)

app.include_router(
    measurements.router,
    prefix="/api/v1/measurements",
    tags=["ARGO Measurements"],
)


# Development-only endpoints
if settings.enable_test_endpoints and settings.is_development:
    @app.get("/debug/settings", tags=["Debug"])
    async def debug_settings():
        """Debug endpoint to view current settings (development only)."""
        return {
            "app_name": settings.app_name,
            "debug": settings.debug,
            "cors_origins": settings.get_cors_origins(),
            "database_url": settings.database_url_sync[:50] + "...",  # Truncate for security
            "openai_api_key_set": bool(settings.openai_api_key),
            "firebase_project_id": settings.firebase_project_id,
        }


def run_server():
    """Run the server (for CLI usage)."""
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers if not settings.reload else 1,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
        access_log=settings.is_development,
    )


if __name__ == "__main__":
    run_server()
