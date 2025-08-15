"""
Error handling middleware for centralized error processing.

This module provides comprehensive error handling middleware that:
- Catches all unhandled exceptions
- Provides consistent JSON error responses
- Implements correlation ID tracking
- Handles development vs production error details
- Logs errors with proper context
"""

import logging
import traceback
import uuid
from typing import Any, Dict, Optional, Union

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Import configuration functions with fallback for testing
try:
    from src.config.settings import is_development, is_production
except Exception:
    # Fallback for testing when configuration is not available
    def is_development():
        return True

    def is_production():
        return False
from src.schemas.base import ErrorResponse, ErrorDetail


logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for centralized error handling.

    This middleware catches all unhandled exceptions and converts them
    to consistent JSON error responses with proper logging and correlation tracking.
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize error handling middleware.

        Args:
            app: ASGI application instance
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and handle any exceptions.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response object
        """
        # Generate or extract correlation ID
        correlation_id = self._get_or_generate_correlation_id(request)

        # Add correlation ID to request state for use in handlers
        request.state.correlation_id = correlation_id

        try:
            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            return response

        except Exception as exc:
            # Log the exception with context
            await self._log_exception(request, exc, correlation_id)

            # Create error response
            error_response = await self._create_error_response(
                request, exc, correlation_id
            )

            return error_response

    def _get_or_generate_correlation_id(self, request: Request) -> str:
        """
        Get correlation ID from request headers or generate a new one.

        Args:
            request: FastAPI request object

        Returns:
            Correlation ID string
        """
        # Try to get correlation ID from various header names
        correlation_headers = [
            "x-correlation-id",
            "x-request-id",
            "x-trace-id",
            "correlation-id",
            "request-id",
            "trace-id"
        ]

        for header in correlation_headers:
            correlation_id = request.headers.get(header)
            if correlation_id:
                return correlation_id

        # Generate new correlation ID if not found
        return str(uuid.uuid4())

    async def _log_exception(
        self,
        request: Request,
        exc: Exception,
        correlation_id: str
    ) -> None:
        """
        Log exception with request context.

        Args:
            request: FastAPI request object
            exc: Exception that occurred
            correlation_id: Request correlation ID
        """
        # Extract request information
        request_info = {
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "correlation_id": correlation_id,
        }

        # Get client IP
        client_ip = self._get_client_ip(request)
        if client_ip:
            request_info["client_ip"] = client_ip

        # Get user information if available
        user_info = getattr(request.state, "user", None)
        if user_info:
            request_info["user_id"] = getattr(user_info, "id", None)
            request_info["user_email"] = getattr(user_info, "email", None)

        # Log exception with context
        logger.error(
            f"Unhandled exception in {request.method} {request.url.path}",
            extra={
                "exception_type": type(exc).__name__,
                "exception_message": str(exc),
                "request_info": request_info,
                "correlation_id": correlation_id,
            },
            exc_info=exc
        )

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address or None
        """
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",  # Cloudflare
            "x-client-ip",
        ]

        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one
                return ip.split(",")[0].strip()

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None

    async def _create_error_response(
        self,
        request: Request,
        exc: Exception,
        correlation_id: str
    ) -> JSONResponse:
        """
        Create standardized error response.

        Args:
            request: FastAPI request object
            exc: Exception that occurred
            correlation_id: Request correlation ID

        Returns:
            JSON error response
        """
        # Determine error details based on environment
        # Check if we're in development or test environment
        try:
            from src.config.settings import get_environment
            current_env = get_environment()
            is_dev_or_test = current_env in ["development", "test"]
        except Exception:
            # Fallback to development behavior for tests
            is_dev_or_test = True
            
        if is_dev_or_test:
            # In development/test, include full error details
            error_details = self._get_development_error_details(exc)
            message = str(exc) if str(exc) else "An unexpected error occurred"
        else:
            # In production, use generic error message
            error_details = None
            message = "An internal server error occurred"

        # Create error response
        error_response = ErrorResponse(
            message=message,
            error_code="INTERNAL_SERVER_ERROR",
            details=error_details
        )

        # Add correlation ID to response data
        response_data = error_response.model_dump()
        response_data["correlation_id"] = correlation_id

        # Convert datetime to ISO format for JSON serialization
        if "timestamp" in response_data and hasattr(response_data["timestamp"], "isoformat"):
            response_data["timestamp"] = response_data["timestamp"].isoformat()

        return JSONResponse(
            status_code=500,
            content=response_data,
            headers={"X-Correlation-ID": correlation_id}
        )

    def _get_development_error_details(self, exc: Exception) -> Optional[list]:
        """
        Get detailed error information for development environment.

        Args:
            exc: Exception that occurred

        Returns:
            List of error details or None
        """
        try:
            # Get traceback information
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)

            # Create error detail with traceback
            error_detail = ErrorDetail(
                field="exception",
                message=str(exc),
                code=type(exc).__name__
            )

            # Add traceback as additional detail
            traceback_detail = ErrorDetail(
                field="traceback",
                message="".join(tb_lines),
                code="TRACEBACK"
            )

            return [error_detail, traceback_detail]

        except Exception:
            # If we can't format the error details, return None
            return None


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware for correlation ID handling.

    This middleware ensures every request has a correlation ID for tracking
    across services and logs.
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize correlation ID middleware.

        Args:
            app: ASGI application instance
        """
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and ensure correlation ID is present.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response object
        """
        # Generate or extract correlation ID
        correlation_id = self._get_or_generate_correlation_id(request)

        # Add correlation ID to request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response

    def _get_or_generate_correlation_id(self, request: Request) -> str:
        """
        Get correlation ID from request headers or generate a new one.

        Args:
            request: FastAPI request object

        Returns:
            Correlation ID string
        """
        # Try to get correlation ID from various header names
        correlation_headers = [
            "x-correlation-id",
            "x-request-id",
            "x-trace-id",
            "correlation-id",
            "request-id",
            "trace-id"
        ]

        for header in correlation_headers:
            correlation_id = request.headers.get(header)
            if correlation_id:
                return correlation_id

        # Generate new correlation ID if not found
        return str(uuid.uuid4())


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request/response logging.

    This middleware logs all requests and responses with correlation IDs
    and sensitive data masking.
    """

    def __init__(self, app: ASGIApp, log_requests: bool = True, log_responses: bool = True):
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application instance
            log_requests: Whether to log requests
            log_responses: Whether to log responses
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses

        # Sensitive headers to mask
        self.sensitive_headers = {
            "authorization",
            "x-api-key",
            "cookie",
            "set-cookie",
            "x-auth-token",
            "x-access-token",
        }

        # Sensitive query parameters to mask
        self.sensitive_params = {
            "password",
            "token",
            "api_key",
            "secret",
            "key",
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with logging.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response object
        """
        # Get correlation ID from request state
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        # Log request if enabled
        if self.log_requests:
            await self._log_request(request, correlation_id)

        # Process request
        response = await call_next(request)

        # Log response if enabled
        if self.log_responses:
            await self._log_response(request, response, correlation_id)

        return response

    async def _log_request(self, request: Request, correlation_id: str) -> None:
        """
        Log incoming request.

        Args:
            request: FastAPI request object
            correlation_id: Request correlation ID
        """
        # Mask sensitive headers
        headers = self._mask_sensitive_data(dict(request.headers), self.sensitive_headers)

        # Mask sensitive query parameters
        query_params = self._mask_sensitive_data(dict(request.query_params), self.sensitive_params)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Log request
        logger.info(
            f"Incoming request: {request.method} {request.url.path}",
            extra={
                "event_type": "request",
                "method": request.method,
                "path": request.url.path,
                "query_params": query_params,
                "headers": headers,
                "client_ip": client_ip,
                "correlation_id": correlation_id,
            }
        )

    async def _log_response(
        self,
        request: Request,
        response: Response,
        correlation_id: str
    ) -> None:
        """
        Log outgoing response.

        Args:
            request: FastAPI request object
            response: FastAPI response object
            correlation_id: Request correlation ID
        """
        # Log response
        logger.info(
            f"Outgoing response: {request.method} {request.url.path} -> {response.status_code}",
            extra={
                "event_type": "response",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "correlation_id": correlation_id,
            }
        )

    def _mask_sensitive_data(self, data: Dict[str, Any], sensitive_keys: set) -> Dict[str, Any]:
        """
        Mask sensitive data in dictionary.

        Args:
            data: Dictionary to mask
            sensitive_keys: Set of sensitive keys to mask

        Returns:
            Dictionary with sensitive values masked
        """
        masked_data = {}

        for key, value in data.items():
            if key.lower() in sensitive_keys:
                masked_data[key] = "***MASKED***"
            else:
                masked_data[key] = value

        return masked_data

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address or None
        """
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",  # Cloudflare
            "x-client-ip",
        ]

        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one
                return ip.split(",")[0].strip()

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None
