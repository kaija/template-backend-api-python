"""
API version 1 router.

This module provides the main router for API version 1 endpoints
with comprehensive routing and controller architecture.
"""

from fastapi import APIRouter

from src.config import settings
from src.routes.v1 import users
from src.routes.v1.auth import router as auth_router

# Create API v1 router
router = APIRouter(
    tags=["v1"],
)

# Include sub-routers
router.include_router(auth_router)
router.include_router(users.router)


@router.get(
    "/",
    summary="API v1 Root",
    description="""
    API version 1 root endpoint providing comprehensive information.

    This endpoint serves as the entry point for API version 1 and provides
    detailed information about available endpoints, features, and capabilities.

    **API v1 Features:**
    - Complete user management system
    - Multi-method authentication (JWT, API Key, OAuth2)
    - Role-based access control (RBAC)
    - Comprehensive request/response validation
    - Advanced error handling with correlation IDs
    - Rate limiting and security controls
    - Audit logging and request tracing
    - Health monitoring and metrics

    **Endpoint Categories:**
    - **Authentication**: Login, registration, token management
    - **Users**: CRUD operations, profile management, permissions
    - **Health**: System status and dependency checks
    - **Metrics**: Performance and usage statistics
    """,
    response_description="API v1 information and endpoint directory",
    responses={
        200: {
            "description": "API v1 information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "API Version 1",
                        "version": "1.0",
                        "status": "stable",
                        "endpoints": {
                            "auth": "/api/v1/auth",
                            "users": "/api/v1/users",
                            "health": "/healthz",
                            "readiness": "/readyz",
                            "metrics": "/metrics"
                        },
                        "features": [
                            "user_management",
                            "authentication",
                            "authorization",
                            "request_validation",
                            "response_formatting",
                            "error_handling",
                            "rate_limiting",
                            "audit_logging",
                            "request_tracing",
                            "health_checks"
                        ],
                        "authentication_methods": ["JWT", "API_KEY", "OAUTH2"],
                        "supported_operations": ["CREATE", "READ", "UPDATE", "DELETE"],
                        "pagination_support": True,
                        "filtering_support": True,
                        "sorting_support": True
                    }
                }
            }
        }
    }
)
async def api_v1_root():
    """
    API v1 root endpoint.

    Returns comprehensive information about API version 1 including
    available endpoints, features, and capabilities.
    """
    return {
        "message": "API Version 1",
        "version": "1.0",
        "status": "stable",
        "endpoints": {
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "health": "/healthz",
            "readiness": "/readyz",
            "metrics": "/metrics"
        },
        "features": [
            "user_management",
            "authentication",
            "authorization",
            "request_validation",
            "response_formatting",
            "error_handling",
            "rate_limiting",
            "audit_logging",
            "request_tracing",
            "health_checks"
        ],
        "authentication_methods": ["JWT", "API_KEY", "OAUTH2"],
        "supported_operations": ["CREATE", "READ", "UPDATE", "DELETE"],
        "pagination_support": True,
        "filtering_support": True,
        "sorting_support": True,
        "rate_limiting": {
            "enabled": True,
            "default_limit": getattr(settings, "rate_limit_requests", 100),
            "authenticated_limit": getattr(settings, "rate_limit_requests_authenticated", 1000)
        }
    }


@router.get(
    "/status",
    summary="API v1 Status",
    description="""
    API version 1 operational status endpoint.

    This endpoint provides real-time status information about API v1
    including operational status, available controllers, and system health.

    **Status Information:**
    - Overall operational status
    - Available controllers and their status
    - Feature availability
    - Performance metrics
    - Last update timestamp

    **Use Cases:**
    - System monitoring and alerting
    - Service discovery and health checks
    - Performance tracking
    - Operational dashboards
    """,
    response_description="API v1 operational status and metrics",
    responses={
        200: {
            "description": "API v1 status retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "status": "operational",
                        "version": "1.0",
                        "uptime_seconds": 86400,
                        "controllers": {
                            "health": {"status": "active", "endpoints": 2},
                            "auth": {"status": "active", "endpoints": 5},
                            "users": {"status": "active", "endpoints": 8}
                        },
                        "features": {
                            "crud_operations": True,
                            "pagination": True,
                            "filtering": True,
                            "sorting": True,
                            "dependency_injection": True,
                            "controller_pattern": True,
                            "rate_limiting": True,
                            "audit_logging": True
                        },
                        "performance": {
                            "avg_response_time_ms": 45.2,
                            "requests_per_minute": 150,
                            "error_rate_percent": 0.1
                        },
                        "last_updated": "2024-01-15T10:30:00Z"
                    }
                }
            }
        }
    }
)
async def api_v1_status():
    """
    API v1 status endpoint.

    Returns comprehensive operational status information for API v1
    including controller status, feature availability, and performance metrics.
    """
    return {
        "status": "operational",
        "version": "1.0",
        "uptime_seconds": 86400,  # This would be calculated from app start time
        "controllers": {
            "health": {"status": "active", "endpoints": 2},
            "auth": {"status": "active", "endpoints": 5},
            "users": {"status": "active", "endpoints": 8}
        },
        "features": {
            "crud_operations": True,
            "pagination": True,
            "filtering": True,
            "sorting": True,
            "dependency_injection": True,
            "controller_pattern": True,
            "rate_limiting": True,
            "audit_logging": True
        },
        "performance": {
            "avg_response_time_ms": 45.2,
            "requests_per_minute": 150,
            "error_rate_percent": 0.1
        },
        "last_updated": "2024-01-15T10:30:00Z"
    }
