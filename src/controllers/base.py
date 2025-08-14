"""
Base controller classes with common functionality.

This module provides base controller classes that include common functionality
such as dependency injection, error handling, and response formatting.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, Generic
from datetime import datetime, timezone

from fastapi import HTTPException, status
from pydantic import BaseModel

from src.config import settings


# Type variables for generic controllers
T = TypeVar('T', bound=BaseModel)
CreateT = TypeVar('CreateT', bound=BaseModel)
UpdateT = TypeVar('UpdateT', bound=BaseModel)


class BaseController(ABC):
    """
    Base controller class with common functionality.

    This class provides common functionality that all controllers can inherit,
    including logging, error handling, and response formatting.
    """

    def __init__(self):
        """Initialize the base controller."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def _log_request(self, method: str, endpoint: str, **kwargs) -> None:
        """
        Log incoming requests.

        Args:
            method: HTTP method
            endpoint: Endpoint path
            **kwargs: Additional context to log
        """
        self.logger.info(
            f"{method} {endpoint}",
            extra={
                "method": method,
                "endpoint": endpoint,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **kwargs
            }
        )

    def _log_response(self, method: str, endpoint: str, status_code: int, **kwargs) -> None:
        """
        Log outgoing responses.

        Args:
            method: HTTP method
            endpoint: Endpoint path
            status_code: HTTP status code
            **kwargs: Additional context to log
        """
        self.logger.info(
            f"{method} {endpoint} -> {status_code}",
            extra={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **kwargs
            }
        )

    def _handle_error(self, error: Exception, context: str = "") -> HTTPException:
        """
        Handle and format errors consistently.

        Args:
            error: The exception that occurred
            context: Additional context about where the error occurred

        Returns:
            HTTPException with appropriate status code and message
        """
        error_id = f"{datetime.now(timezone.utc).timestamp()}"

        self.logger.error(
            f"Error in {context}: {str(error)}",
            extra={
                "error_id": error_id,
                "error_type": type(error).__name__,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            exc_info=True
        )

        # Return appropriate HTTP exception based on error type
        if isinstance(error, ValueError):
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid input provided",
                    "error_id": error_id,
                    "details": str(error) if settings.debug else None
                }
            )
        elif isinstance(error, PermissionError):
            return HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Access denied",
                    "error_id": error_id,
                    "details": str(error) if settings.debug else None
                }
            )
        elif isinstance(error, FileNotFoundError):
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Resource not found",
                    "error_id": error_id,
                    "details": str(error) if settings.debug else None
                }
            )
        else:
            return HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Internal server error",
                    "error_id": error_id,
                    "details": str(error) if settings.debug else None
                }
            )

    def _create_response(
        self,
        data: Any = None,
        message: str = "Success",
        status_code: int = status.HTTP_200_OK,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a standardized response format.

        Args:
            data: Response data
            message: Response message
            status_code: HTTP status code
            metadata: Additional metadata

        Returns:
            Standardized response dictionary
        """
        response = {
            "success": 200 <= status_code < 300,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if data is not None:
            response["data"] = data

        if metadata:
            response["metadata"] = metadata

        return response


class CRUDController(BaseController, Generic[T, CreateT, UpdateT]):
    """
    Base CRUD controller with common CRUD operations.

    This class provides a template for controllers that need to implement
    Create, Read, Update, Delete operations.
    """

    def __init__(self, model_class: Type[T]):
        """
        Initialize the CRUD controller.

        Args:
            model_class: The model class this controller manages
        """
        super().__init__()
        self.model_class = model_class

    @abstractmethod
    async def create(self, data: CreateT) -> T:
        """
        Create a new resource.

        Args:
            data: Data for creating the resource

        Returns:
            Created resource
        """
        pass

    @abstractmethod
    async def get_by_id(self, resource_id: str) -> Optional[T]:
        """
        Get a resource by ID.

        Args:
            resource_id: ID of the resource

        Returns:
            Resource if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get all resources with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply

        Returns:
            Dictionary with resources and pagination info
        """
        pass

    @abstractmethod
    async def update(self, resource_id: str, data: UpdateT) -> Optional[T]:
        """
        Update a resource.

        Args:
            resource_id: ID of the resource to update
            data: Data for updating the resource

        Returns:
            Updated resource if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, resource_id: str) -> bool:
        """
        Delete a resource.

        Args:
            resource_id: ID of the resource to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    def _validate_pagination(self, skip: int, limit: int) -> None:
        """
        Validate pagination parameters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Raises:
            ValueError: If pagination parameters are invalid
        """
        if skip < 0:
            raise ValueError("Skip parameter must be non-negative")

        if limit <= 0:
            raise ValueError("Limit parameter must be positive")

        max_limit = getattr(settings, "max_page_size", 1000)
        if limit > max_limit:
            raise ValueError(f"Limit parameter cannot exceed {max_limit}")

    def _create_paginated_response(
        self,
        items: list,
        total: int,
        skip: int,
        limit: int
    ) -> Dict[str, Any]:
        """
        Create a paginated response.

        Args:
            items: List of items for current page
            total: Total number of items
            skip: Number of records skipped
            limit: Maximum number of records per page

        Returns:
            Paginated response dictionary
        """
        return {
            "items": items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "page": (skip // limit) + 1,
                "pages": (total + limit - 1) // limit,
                "has_next": skip + limit < total,
                "has_prev": skip > 0,
            }
        }


class HealthController(BaseController):
    """
    Health check controller.

    Provides health and readiness check functionality.
    """

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform basic health check.

        This is a lightweight check that only verifies the application is running
        and can process requests. It does not check external dependencies.

        Returns:
            Health status information
        """
        self._log_request("GET", "/healthz")

        try:
            import time
            import os
            import sys

            start_time = time.time()

            # Basic application health information
            health_data = {
                "status": "healthy",
                "version": getattr(settings, "version", "0.1.0"),
                "environment": getattr(settings, "env", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime_seconds": self._get_uptime_seconds(),
                "system": {
                    "python_version": sys.version.split()[0],
                    "platform": sys.platform,
                    "process_id": os.getpid(),
                },
                "application": {
                    "name": getattr(settings, "app_name", "Production API Framework"),
                    "debug_mode": getattr(settings, "debug", False),
                    "log_level": getattr(settings, "log_level", "INFO"),
                }
            }

            # System metrics are not included (psutil dependency removed)
            # For production monitoring, use external tools like Prometheus

            response_time = round((time.time() - start_time) * 1000, 2)

            response_data = self._create_response(
                data=health_data,
                message="Application is healthy",
                metadata={
                    "response_time_ms": response_time,
                    "check_type": "basic",
                }
            )

            self._log_response("GET", "/healthz", status.HTTP_200_OK)
            return response_data

        except Exception as e:
            raise self._handle_error(e, "health_check")

    async def readiness_check(self) -> Dict[str, Any]:
        """
        Perform readiness check with dependency validation.

        Returns:
            Readiness status information
        """
        self._log_request("GET", "/readyz")

        try:
            import asyncio
            import time

            start_time = time.time()

            # Get health check timeout from settings
            timeout = getattr(settings, "health_check_timeout", 10)

            # Perform dependency checks with timeout
            try:
                checks = await asyncio.wait_for(
                    self._perform_all_checks(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                checks = {
                    "database": {
                        "status": "timeout",
                        "error": f"Health check timed out after {timeout}s",
                        "response_time_ms": timeout * 1000,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "redis": {
                        "status": "timeout",
                        "error": f"Health check timed out after {timeout}s",
                        "response_time_ms": timeout * 1000,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "external_services": {
                        "status": "timeout",
                        "error": f"Health check timed out after {timeout}s",
                        "response_time_ms": timeout * 1000,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                }

            # Determine overall status with more nuanced logic
            overall_status, status_reason = self._determine_readiness_status(checks)

            # Calculate total response time
            total_response_time = round((time.time() - start_time) * 1000, 2)

            # Create detailed response
            response_data = self._create_response(
                data={
                    "status": overall_status,
                    "version": getattr(settings, "version", "0.1.0"),
                    "environment": getattr(settings, "env", "unknown"),
                    "uptime_seconds": self._get_uptime_seconds(),
                    "checks": checks,
                    "summary": {
                        "total_checks": len(checks),
                        "healthy_checks": sum(1 for check in checks.values() if check["status"] == "healthy"),
                        "unhealthy_checks": sum(1 for check in checks.values() if check["status"] == "unhealthy"),
                        "unavailable_checks": sum(1 for check in checks.values() if check["status"] == "unavailable"),
                        "timeout_checks": sum(1 for check in checks.values() if check["status"] == "timeout"),
                        "total_response_time_ms": total_response_time,
                    },
                    "reason": status_reason,
                },
                message=f"Application is {overall_status}",
                metadata={
                    "check_timeout": timeout,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Determine HTTP status code
            if overall_status == "ready":
                status_code = status.HTTP_200_OK
            elif overall_status == "degraded":
                status_code = status.HTTP_200_OK  # Still serving traffic but with warnings
            else:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE

            self._log_response("GET", "/readyz", status_code)

            return response_data

        except Exception as e:
            raise self._handle_error(e, "readiness_check")

    async def _perform_all_checks(self) -> Dict[str, Any]:
        """
        Perform all health checks concurrently.

        Returns:
            Dictionary with all check results
        """
        import asyncio

        # Run all checks concurrently for better performance
        database_task = asyncio.create_task(self._check_database())
        redis_task = asyncio.create_task(self._check_redis())
        external_task = asyncio.create_task(self._check_external_services())

        # Wait for all checks to complete
        database_result, redis_result, external_result = await asyncio.gather(
            database_task,
            redis_task,
            external_task,
            return_exceptions=True
        )

        # Handle any exceptions from the checks
        checks = {}

        if isinstance(database_result, Exception):
            checks["database"] = {
                "status": "error",
                "error": str(database_result),
                "response_time_ms": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            checks["database"] = database_result

        if isinstance(redis_result, Exception):
            checks["redis"] = {
                "status": "error",
                "error": str(redis_result),
                "response_time_ms": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            checks["redis"] = redis_result

        if isinstance(external_result, Exception):
            checks["external_services"] = {
                "status": "error",
                "error": str(external_result),
                "response_time_ms": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            checks["external_services"] = external_result

        return checks

    def _determine_readiness_status(self, checks: Dict[str, Any]) -> tuple[str, str]:
        """
        Determine overall readiness status based on individual checks.

        Args:
            checks: Dictionary of individual check results

        Returns:
            Tuple of (status, reason)
        """
        # Critical dependencies that must be healthy for readiness
        critical_deps = ["database"]

        # Optional dependencies that can be degraded
        optional_deps = ["redis", "external_services"]

        # Check critical dependencies
        critical_issues = []
        for dep in critical_deps:
            if dep in checks:
                check_status = checks[dep]["status"]
                if check_status not in ["healthy"]:
                    critical_issues.append(f"{dep}: {check_status}")

        if critical_issues:
            return "not_ready", f"Critical dependencies unhealthy: {', '.join(critical_issues)}"

        # Check optional dependencies
        optional_issues = []
        for dep in optional_deps:
            if dep in checks:
                check_status = checks[dep]["status"]
                if check_status == "unhealthy":
                    optional_issues.append(f"{dep}: {check_status}")
                elif check_status == "unavailable":
                    # Unavailable is acceptable for optional services
                    pass

        if optional_issues:
            return "degraded", f"Optional dependencies degraded: {', '.join(optional_issues)}"

        return "ready", "All dependencies healthy"

    def _get_uptime_seconds(self) -> float:
        """
        Get application uptime in seconds.

        Returns:
            Uptime in seconds (simplified implementation without psutil)
        """
        # Simple implementation without psutil dependency
        # In production, consider using external monitoring tools
        # or tracking application start time in a global variable
        import time

        # Return a basic uptime based on process existence
        # This is a simplified approach - for accurate uptime tracking,
        # consider storing the application start time when the app initializes
        try:
            # Try to read /proc/uptime on Linux systems
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                return uptime_seconds
        except (FileNotFoundError, OSError, ValueError):
            # Fallback for non-Linux systems or when /proc is not available
            # Return 0 to indicate uptime is not available
            return 0.0

    async def _check_database(self) -> Dict[str, Any]:
        """
        Check database connectivity.

        Returns:
            Database check results
        """
        import time
        from sqlalchemy import text

        start_time = time.time()

        try:
            # Import database utilities
            from src.database.config import get_session

            # Test database connectivity with a simple query
            async with get_session() as session:
                result = await session.execute(text("SELECT 1 as health_check"))
                result.scalar()

                response_time = round((time.time() - start_time) * 1000, 2)

                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "details": "Database connection successful",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            self.logger.error(f"Database health check failed: {e}")

            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "details": f"Database connection failed: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _check_redis(self) -> Dict[str, Any]:
        """
        Check Redis connectivity.

        Returns:
            Redis check results
        """
        import time

        start_time = time.time()

        try:
            # Try to import redis and create a connection
            import redis.asyncio as redis
            from src.config import get_redis_url

            # Create Redis client
            redis_client = redis.from_url(
                get_redis_url(),
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Test Redis connectivity with ping
            await redis_client.ping()

            # Test basic operations
            test_key = "health_check_test"
            await redis_client.set(test_key, "ok", ex=10)  # Expire in 10 seconds
            result = await redis_client.get(test_key)
            await redis_client.delete(test_key)

            await redis_client.aclose()

            response_time = round((time.time() - start_time) * 1000, 2)

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "details": "Redis connection successful",
                "operations": "ping, set, get, delete",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except ImportError:
            response_time = round((time.time() - start_time) * 1000, 2)
            self.logger.warning("Redis library not available")

            return {
                "status": "unavailable",
                "response_time_ms": response_time,
                "details": "Redis library not installed",
                "error": "redis library not available",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            self.logger.error(f"Redis health check failed: {e}")

            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "details": f"Redis connection failed: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _check_external_services(self) -> Dict[str, Any]:
        """
        Check external service dependencies.

        Returns:
            External service check results
        """
        import time
        import asyncio

        start_time = time.time()

        try:
            # Get external service URLs from configuration
            external_services = getattr(settings, "external_services", {})

            if not external_services:
                # No external services configured
                response_time = round((time.time() - start_time) * 1000, 2)
                return {
                    "status": "healthy",
                    "response_time_ms": response_time,
                    "details": "No external services configured",
                    "services": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            # Check each external service
            service_results = {}

            for service_name, service_config in external_services.items():
                service_start = time.time()

                try:
                    # Import httpx for async HTTP requests
                    import httpx

                    url = service_config.get("health_url") or service_config.get("url")
                    timeout = service_config.get("timeout", 5)

                    if not url:
                        service_results[service_name] = {
                            "status": "misconfigured",
                            "error": "No URL configured",
                            "response_time_ms": 0,
                        }
                        continue

                    # Make health check request
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.get(url)
                        response.raise_for_status()

                    service_time = round((time.time() - service_start) * 1000, 2)
                    service_results[service_name] = {
                        "status": "healthy",
                        "response_time_ms": service_time,
                        "status_code": response.status_code,
                        "url": url,
                    }

                except ImportError:
                    service_results[service_name] = {
                        "status": "unavailable",
                        "error": "httpx library not available",
                        "response_time_ms": 0,
                    }

                except Exception as e:
                    service_time = round((time.time() - service_start) * 1000, 2)
                    service_results[service_name] = {
                        "status": "unhealthy",
                        "error": str(e),
                        "response_time_ms": service_time,
                        "url": service_config.get("health_url") or service_config.get("url"),
                    }

            # Determine overall status
            all_healthy = all(
                result["status"] == "healthy"
                for result in service_results.values()
            )

            overall_status = "healthy" if all_healthy else "degraded"

            response_time = round((time.time() - start_time) * 1000, 2)

            return {
                "status": overall_status,
                "response_time_ms": response_time,
                "details": f"Checked {len(service_results)} external services",
                "services": service_results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)
            self.logger.error(f"External services health check failed: {e}")

            return {
                "status": "unhealthy",
                "response_time_ms": response_time,
                "details": f"External services check failed: {str(e)}",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
