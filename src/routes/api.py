"""
Main API router.

This module provides the main API router that includes all API endpoints
with proper versioning and organization.
"""

from fastapi import APIRouter

from src.config import settings
from src.routes.v1 import api as api_v1


# Create main API router
router = APIRouter(
    prefix=getattr(settings, "api_prefix", "/api"),
)

# Include API version routers
router.include_router(
    api_v1.router,
    prefix=getattr(settings, "version_prefix", "/v1"),
)


@router.get("/")
async def api_root():
    """
    API root endpoint.
    
    Returns basic information about the API.
    """
    api_prefix = getattr(settings, "api_prefix", "/api")
    env = getattr(settings, "env", "development")
    
    return {
        "message": "Production API Framework",
        "version": getattr(settings, "version", "0.1.0"),
        "docs_url": f"{api_prefix}/docs" if env != "production" else None,
        "health_url": getattr(settings, "health_check_path", "/healthz"),
        "readiness_url": getattr(settings, "readiness_check_path", "/readyz"),
    }