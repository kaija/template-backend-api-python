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


@router.get(
    "/",
    summary="API Root",
    description="""
    API root endpoint providing basic information about the API.

    This endpoint serves as the main entry point for the API and provides
    essential information about available endpoints, documentation, and
    system status checks.

    **Information Provided:**
    - API name and version
    - Available API versions
    - Documentation URLs (environment-dependent)
    - Health check endpoints
    - Authentication information

    **Usage:**
    Use this endpoint to discover API capabilities and navigate to
    specific functionality or documentation.
    """,
    response_description="API information and navigation links",
    responses={
        200: {
            "description": "API information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Generic API Framework",
                        "version": "1.0.0",
                        "environment": "production",
                        "api_versions": ["v1"],
                        "docs_url": "/docs",
                        "health_url": "/healthz",
                        "readiness_url": "/readyz",
                        "authentication": {
                            "methods": ["JWT", "API Key", "OAuth2"],
                            "login_url": "/api/v1/auth/login"
                        },
                        "features": [
                            "User management",
                            "Authentication & authorization",
                            "Rate limiting",
                            "Request validation",
                            "Comprehensive error handling"
                        ]
                    }
                }
            }
        }
    }
)
async def api_root():
    """
    API root endpoint.

    Returns comprehensive information about the API including available
    endpoints, documentation links, and system capabilities.
    """
    api_prefix = getattr(settings, "api_prefix", "/api")
    env = getattr(settings, "env", "development")

    return {
        "message": "Generic API Framework",
        "version": getattr(settings, "version", "0.1.0"),
        "environment": env,
        "api_versions": ["v1"],
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
        "health_url": getattr(settings, "health_check_path", "/healthz"),
        "readiness_url": getattr(settings, "readiness_check_path", "/readyz"),
        "authentication": {
            "methods": ["JWT", "API Key"],
            "login_url": f"{api_prefix}/v1/auth/login",
        },
        "features": [
            "Example user management",
            "Basic authentication",
            "Request/response validation",
            "Error handling",
            "Health checks",
            "API documentation"
        ],
        "example_endpoints": {
            "users": f"{api_prefix}/v1/users",
            "health": "/healthz",
            "docs": "/docs"
        }
    }
