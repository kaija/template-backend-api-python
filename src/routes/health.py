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
    description="""
    Basic health check endpoint that returns application status.

    This endpoint provides a simple way to verify that the application is running
    and responding to requests. It should always return 200 OK if the application
    is operational.

    **Use Cases:**
    - Container orchestration liveness probes
    - Load balancer health checks
    - Monitoring system status verification

    **Response Format:**
    Returns a JSON object with health status information including:
    - Application status
    - Version information
    - Environment details
    - Timestamp of the check
    """,
    response_description="Application health status with metadata",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Application is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Application is healthy",
                        "data": {
                            "status": "healthy",
                            "version": "1.0.0",
                            "environment": "production",
                            "timestamp": "2024-01-15T10:30:00Z"
                        },
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
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
    description="""
    Readiness check endpoint that verifies all dependencies are available.

    This endpoint performs comprehensive checks of all application dependencies
    to determine if the application is ready to serve traffic. It validates:

    **Dependency Checks:**
    - Database connectivity and responsiveness
    - Redis/cache availability (if configured)
    - External service connectivity
    - File system access

    **Use Cases:**
    - Kubernetes readiness probes
    - Load balancer traffic routing decisions
    - Deployment health verification
    - Service mesh health checks

    **Response Codes:**
    - `200 OK`: All dependencies are healthy and ready
    - `503 Service Unavailable`: One or more dependencies are unhealthy

    **Response Format:**
    Returns detailed information about each dependency check including
    response times and error details for failed checks.
    """,
    response_description="Detailed readiness status with dependency checks",
    responses={
        200: {
            "description": "Application is ready to serve traffic",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Application is ready",
                        "data": {
                            "status": "ready",
                            "version": "1.0.0",
                            "environment": "production",
                            "checks": {
                                "database": {
                                    "status": "healthy",
                                    "response_time_ms": 5.2,
                                    "details": "Database connection successful"
                                },
                                "redis": {
                                    "status": "healthy",
                                    "response_time_ms": 2.1,
                                    "details": "Redis connection successful"
                                }
                            },
                            "timestamp": "2024-01-15T10:30:00Z"
                        },
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        },
        503: {
            "description": "Application is not ready to serve traffic",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Application is not ready",
                        "data": {
                            "status": "not_ready",
                            "version": "1.0.0",
                            "environment": "production",
                            "checks": {
                                "database": {
                                    "status": "unhealthy",
                                    "response_time_ms": None,
                                    "error": "Connection timeout after 5 seconds"
                                },
                                "redis": {
                                    "status": "healthy",
                                    "response_time_ms": 2.1,
                                    "details": "Redis connection successful"
                                }
                            },
                            "timestamp": "2024-01-15T10:30:00Z"
                        },
                        "timestamp": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
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
