"""
Health check routes.

This module provides health check endpoints for monitoring
application status and readiness using the controller pattern.
"""

from typing import Dict, Any

from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse

from src.config import settings
from src.controllers.base import HealthController
from src.dependencies import RequestContext, get_rate_limiter


# Initialize controller
health_controller = HealthController()

# Create router
router = APIRouter(
    prefix="",
    tags=["health"],
    dependencies=[Depends(get_rate_limiter)],
)


@router.get(
    getattr(settings, "health_check_path", "/healthz"),
    summary="Health Check",
    description="Basic health check endpoint that returns application status",
    response_description="Application health status",
    status_code=status.HTTP_200_OK,
)
async def health_check(
    context: RequestContext,
) -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns basic information about the application status.
    This endpoint should always return 200 OK if the application is running.
    
    Args:
        context: Request context from dependency injection
    
    Returns:
        Dictionary with health status information
    """
    return await health_controller.health_check()


@router.get(
    getattr(settings, "readiness_check_path", "/readyz"),
    summary="Readiness Check",
    description="Readiness check endpoint that verifies all dependencies are available",
    response_description="Application readiness status",
    responses={
        200: {"description": "Application is ready"},
        503: {"description": "Application is not ready"},
    }
)
async def readiness_check(
    context: RequestContext,
) -> JSONResponse:
    """
    Readiness check endpoint.
    
    Checks if the application is ready to serve requests by verifying
    that all required dependencies (database, cache, etc.) are available.
    
    Args:
        context: Request context from dependency injection
    
    Returns:
        JSON response with readiness status and dependency checks
    """
    response_data = await health_controller.readiness_check()
    
    # Determine status code based on readiness
    is_ready = response_data.get("data", {}).get("status") == "ready"
    status_code = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        content=response_data,
        status_code=status_code,
    )