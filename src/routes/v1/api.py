"""
API version 1 router.

This module provides the main router for API version 1 endpoints
with comprehensive routing and controller architecture.
"""

from fastapi import APIRouter

from src.routes.v1 import users
from src.routes.v1.auth import router as auth_router

# Create API v1 router
router = APIRouter(
    tags=["v1"],
)

# Include sub-routers
router.include_router(auth_router)
router.include_router(users.router)


@router.get("/")
async def api_v1_root():
    """
    API v1 root endpoint.
    
    Returns information about API version 1.
    """
    return {
        "message": "API Version 1",
        "version": "1.0",
        "endpoints": {
            "health": "/healthz",
            "readiness": "/readyz",
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
        },
        "features": [
            "health_checks",
            "user_management",
            "authentication",
            "authorization",
            "request_validation",
            "response_formatting",
            "error_handling",
            "rate_limiting",
            "request_tracing",
        ]
    }


@router.get("/status")
async def api_v1_status():
    """
    API v1 status endpoint.
    
    Returns the current status of API v1.
    """
    return {
        "status": "operational",
        "version": "1.0",
        "controllers": [
            "health",
            "auth",
            "users",
        ],
        "features": [
            "crud_operations",
            "pagination",
            "filtering",
            "dependency_injection",
            "controller_pattern",
        ]
    }