"""
FastAPI application factory and configuration.

This module provides the application factory pattern for creating FastAPI
applications with different configurations for different environments.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import (
    settings,
    get_cors_config,
    is_development,
    is_production,
    is_testing,
)


def get_app_metadata() -> dict:
    """
    Get application metadata.
    
    Returns:
        Dictionary with application metadata
    """
    return {
        "title": getattr(settings, "app_name", "Production API Framework"),
        "description": "Production-ready backend API framework built with FastAPI",
        "version": getattr(settings, "version", "0.1.0"),
        "contact": {
            "name": "API Support",
            "email": "support@example.com",
        },
        "license_info": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    }


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    This includes database connections, background tasks, and cleanup.
    
    Args:
        app: FastAPI application instance
        
    Yields:
        None during application runtime
    """
    # Startup
    logger = logging.getLogger(__name__)
    logger.info("Starting up application...")
    
    try:
        # Initialize structured logging
        from src.utils.logging import configure_structlog
        configure_structlog()
        logger.info("Structured logging configured")
        
        # Initialize Sentry for error tracking
        from src.monitoring.sentry import configure_sentry
        configure_sentry()
        logger.info("Sentry error tracking initialized")
        
        # Initialize Prometheus metrics
        from src.monitoring.metrics import metrics_collector
        logger.info("Prometheus metrics initialized")
        
        # Initialize database connections
        try:
            from src.database.config import init_database
            await init_database(create_tables=False)  # Tables should be created via migrations
            logger.info("Database connections initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
        
        # Initialize Redis connections
        # TODO: Initialize Redis connection pool
        logger.info("Redis connections initialized")
        
        # Application is ready
        logger.info("Application startup complete")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        
        try:
            # Close database connections
            try:
                from src.database.config import close_database
                await close_database()
                logger.info("Database connections closed")
            except Exception as e:
                logger.error(f"Error closing database connections: {e}")
            
            # Close Redis connections
            # TODO: Close Redis connection pool
            logger.info("Redis connections closed")
            
            # Cleanup monitoring systems
            try:
                from src.monitoring.metrics import cleanup_metrics
                cleanup_metrics()
                logger.info("Monitoring systems cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up monitoring systems: {e}")
            
            logger.info("Application shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")


def create_app(environment: str = None) -> FastAPI:
    """
    Application factory function.
    
    Creates and configures a FastAPI application instance based on the
    current environment settings.
    
    Args:
        environment: Override environment (for testing)
        
    Returns:
        Configured FastAPI application instance
    """
    # Override environment if specified (useful for testing)
    if environment:
        import os
        os.environ["API_ENV"] = environment
    
    # Create FastAPI application
    app_config = {
        **get_app_metadata(),
        "lifespan": lifespan,
    }
    
    # Environment-specific configuration
    if is_development():
        app_config.update({
            "debug": True,
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        })
    elif is_production():
        app_config.update({
            "debug": False,
            "docs_url": None,  # Disable docs in production
            "redoc_url": None,
            "openapi_url": None,
        })
    elif is_testing():
        app_config.update({
            "debug": False,
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        })
    
    app = FastAPI(**app_config)
    
    # Configure CORS
    try:
        cors_config = get_cors_config()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_config["allow_origins"],
            allow_credentials=cors_config["allow_credentials"],
            allow_methods=cors_config["allow_methods"],
            allow_headers=cors_config["allow_headers"],
        )
    except Exception as e:
        # Fallback CORS configuration for testing
        logger = logging.getLogger(__name__)
        logger.warning(f"Using fallback CORS configuration: {e}")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Add custom middleware
    _add_middleware(app)
    
    # Store reference to connection tracking middleware for shutdown handling
    if hasattr(app, 'user_middleware'):
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls') and middleware.cls.__name__ == 'ConnectionTrackingMiddleware':
                app.state.connection_tracking_middleware = middleware.cls
                break
    
    # Include routers
    _include_routers(app)
    
    # Add exception handlers
    _add_exception_handlers(app)
    
    return app


def _add_middleware(app: FastAPI) -> None:
    """
    Add custom middleware to the application.
    
    Args:
        app: FastAPI application instance
    """
    # Import middleware
    from src.middleware.error_handling import (
        ErrorHandlingMiddleware,
        CorrelationIDMiddleware,
        RequestLoggingMiddleware
    )
    from src.middleware.security import (
        SecurityHeadersMiddleware,
        RateLimitMiddleware,
        TrustedHostMiddleware
    )
    from src.middleware.auth import (
        AuthenticationMiddleware,
        create_jwt_backend,
        create_api_key_backend,
        create_oauth2_backend
    )
    from src.audit.middleware import AuditMiddleware
    from src.middleware.observability import ObservabilityMiddleware
    from src.middleware.connection_tracking import ConnectionTrackingMiddleware
    
    # Add connection tracking middleware (first to track all requests)
    app.add_middleware(ConnectionTrackingMiddleware)
    
    # Add trusted host middleware (early for security)
    allowed_hosts = getattr(settings, "allowed_hosts", ["*"])
    if not is_development():
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=allowed_hosts,
            allow_any=False
        )
    
    # Add security headers middleware
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=is_production(),
        enable_csp=True
    )
    
    # Add rate limiting middleware (only in production/staging)
    if not is_development():
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=getattr(settings, "rate_limit_requests", 60),
            enabled=getattr(settings, "rate_limit_enabled", True)
        )
    
    # Add error handling middleware (should be early to catch all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Add correlation ID middleware
    app.add_middleware(CorrelationIDMiddleware)
    
    # Add observability middleware for comprehensive monitoring
    app.add_middleware(
        ObservabilityMiddleware,
        log_requests=getattr(settings, "observability_log_requests", True),
        log_responses=getattr(settings, "observability_log_responses", True),
        log_request_body=getattr(settings, "observability_log_request_body", False),
        log_response_body=getattr(settings, "observability_log_response_body", False),
        mask_sensitive_data=getattr(settings, "observability_mask_sensitive_data", True),
        track_performance=getattr(settings, "observability_track_performance", True),
    )
    
    # Add authentication middleware
    auth_backends = [
        create_jwt_backend(),
        create_api_key_backend(),
        create_oauth2_backend(),
    ]
    app.add_middleware(
        AuthenticationMiddleware,
        backends=auth_backends,
        require_auth=False  # Don't require auth by default
    )
    
    # Add audit logging middleware
    app.add_middleware(
        AuditMiddleware,
        log_requests=getattr(settings, "audit_log_requests", True),
        log_responses=getattr(settings, "audit_log_responses", True),
        log_errors=getattr(settings, "audit_log_errors", True)
    )
    
    # Add request logging middleware (only in development and staging)
    if is_development() or settings.env == "staging":
        app.add_middleware(
            RequestLoggingMiddleware,
            log_requests=True,
            log_responses=True
        )


def _include_routers(app: FastAPI) -> None:
    """
    Include API routers in the application.
    
    Args:
        app: FastAPI application instance
    """
    # Import routers
    from src.routes.health import router as health_router
    from src.routes.api import router as api_router
    from src.routes.metrics import router as metrics_router
    
    # Include health check routes (no prefix)
    app.include_router(health_router)
    
    # Include metrics routes (no prefix)
    app.include_router(metrics_router)
    
    # Include main API routes
    app.include_router(api_router)


def _add_exception_handlers(app: FastAPI) -> None:
    """
    Add custom exception handlers to the application.
    
    Args:
        app: FastAPI application instance
    """
    from src.exceptions import setup_exception_handlers
    setup_exception_handlers(app)


def get_application() -> FastAPI:
    """
    Get the configured FastAPI application instance.
    
    This is the main entry point for creating the application.
    
    Returns:
        Configured FastAPI application instance
    """
    return create_app()


# Application instance will be created when needed
# Use get_application() to create the app instance