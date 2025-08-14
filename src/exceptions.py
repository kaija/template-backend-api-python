"""
Custom exception classes and error handling.

This module provides custom exception classes and error handling
utilities for the application.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.config.settings import is_development, is_production
from src.schemas.base import ErrorResponse, ErrorDetail

logger = logging.getLogger(__name__)


class APIException(HTTPException):
    """
    Base API exception class.
    
    Provides a standardized way to raise HTTP exceptions with
    detailed error information.
    """
    
    def __init__(
        self,
        status_code: int,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize API exception.
        
        Args:
            status_code: HTTP status code
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Detailed error information
            headers: Optional HTTP headers
        """
        self.message = message
        self.error_code = error_code
        self.details = details or []
        
        super().__init__(
            status_code=status_code,
            detail=self._create_detail(),
            headers=headers
        )
    
    def _create_detail(self) -> Dict[str, Any]:
        """Create detailed error information."""
        return {
            "message": self.message,
            "error_code": self.error_code,
            "details": [detail.model_dump() for detail in self.details] if self.details else None
        }


class ValidationException(APIException):
    """Exception for validation errors."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[List[ErrorDetail]] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            error_code="VALIDATION_ERROR",
            details=details
        )


class AuthenticationException(APIException):
    """Exception for authentication errors."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTHENTICATION_FAILED"
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=message,
            error_code=error_code,
            headers={"WWW-Authenticate": "Bearer"}
        )


class AuthorizationException(APIException):
    """Exception for authorization errors."""
    
    def __init__(
        self,
        message: str = "Access denied",
        error_code: str = "ACCESS_DENIED"
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            message=message,
            error_code=error_code
        )


class NotFoundException(APIException):
    """Exception for resource not found errors."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        error_code: str = "RESOURCE_NOT_FOUND"
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            message=message,
            error_code=error_code
        )


class ConflictException(APIException):
    """Exception for resource conflict errors."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        error_code: str = "RESOURCE_CONFLICT"
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            message=message,
            error_code=error_code
        )


class RateLimitException(APIException):
    """Exception for rate limiting errors."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: Optional[int] = None
    ):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=message,
            error_code=error_code,
            headers=headers
        )


class InternalServerException(APIException):
    """Exception for internal server errors."""
    
    def __init__(
        self,
        message: str = "Internal server error",
        error_code: str = "INTERNAL_SERVER_ERROR"
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            error_code=error_code
        )


class BadRequestException(APIException):
    """Exception for bad request errors."""
    
    def __init__(
        self,
        message: str = "Bad request",
        error_code: str = "BAD_REQUEST",
        details: Optional[List[ErrorDetail]] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=message,
            error_code=error_code,
            details=details
        )


class UnprocessableEntityException(APIException):
    """Exception for unprocessable entity errors."""
    
    def __init__(
        self,
        message: str = "Unprocessable entity",
        error_code: str = "UNPROCESSABLE_ENTITY",
        details: Optional[List[ErrorDetail]] = None
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=message,
            error_code=error_code,
            details=details
        )


class ServiceUnavailableException(APIException):
    """Exception for service unavailable errors."""
    
    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        error_code: str = "SERVICE_UNAVAILABLE",
        retry_after: Optional[int] = None
    ):
        headers = {"Retry-After": str(retry_after)} if retry_after else None
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=message,
            error_code=error_code,
            headers=headers
        )


class DatabaseException(APIException):
    """Exception for database-related errors."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        error_code: str = "DATABASE_ERROR"
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=message,
            error_code=error_code
        )


class ExternalServiceException(APIException):
    """Exception for external service errors."""
    
    def __init__(
        self,
        message: str = "External service error",
        error_code: str = "EXTERNAL_SERVICE_ERROR",
        service_name: Optional[str] = None
    ):
        if service_name:
            message = f"{service_name}: {message}"
        
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            message=message,
            error_code=error_code
        )


def convert_pydantic_error_to_details(error: ValidationError) -> List[ErrorDetail]:
    """
    Convert Pydantic validation error to ErrorDetail list.
    
    Args:
        error: Pydantic validation error
        
    Returns:
        List of ErrorDetail objects
    """
    details = []
    
    for err in error.errors():
        field_path = ".".join(str(loc) for loc in err["loc"])
        
        detail = ErrorDetail(
            field=field_path,
            message=err["msg"],
            code=err["type"]
        )
        details.append(detail)
    
    return details


def convert_fastapi_validation_error_to_details(error: RequestValidationError) -> List[ErrorDetail]:
    """
    Convert FastAPI validation error to ErrorDetail list.
    
    Args:
        error: FastAPI request validation error
        
    Returns:
        List of ErrorDetail objects
    """
    details = []
    
    for err in error.errors():
        # Determine field location
        field_parts = []
        for loc in err["loc"]:
            if loc not in ("body", "query", "path", "header"):
                field_parts.append(str(loc))
        
        field_path = ".".join(field_parts) if field_parts else "unknown"
        
        detail = ErrorDetail(
            field=field_path,
            message=err["msg"],
            code=err["type"]
        )
        details.append(detail)
    
    return details


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle FastAPI validation errors.
    
    Args:
        request: FastAPI request object
        exc: Request validation error
        
    Returns:
        JSON response with error details
    """
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Log validation error
    logger.warning(
        f"Validation error in {request.method} {request.url.path}",
        extra={
            "event_type": "validation_error",
            "method": request.method,
            "path": request.url.path,
            "validation_errors": exc.errors(),
            "correlation_id": correlation_id,
        }
    )
    
    details = convert_fastapi_validation_error_to_details(exc)
    
    error_response = ErrorResponse(
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        details=details
    )
    
    # Add correlation ID to response
    response_data = error_response.model_dump()
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    headers = {"X-Correlation-ID": correlation_id} if correlation_id else None
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response_data,
        headers=headers
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Args:
        request: FastAPI request object
        exc: Pydantic validation error
        
    Returns:
        JSON response with error details
    """
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Log validation error
    logger.warning(
        f"Pydantic validation error in {request.method} {request.url.path}",
        extra={
            "event_type": "pydantic_validation_error",
            "method": request.method,
            "path": request.url.path,
            "validation_errors": exc.errors(),
            "correlation_id": correlation_id,
        }
    )
    
    details = convert_pydantic_error_to_details(exc)
    
    error_response = ErrorResponse(
        message="Data validation failed",
        error_code="VALIDATION_ERROR",
        details=details
    )
    
    # Add correlation ID to response
    response_data = error_response.model_dump()
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    headers = {"X-Correlation-ID": correlation_id} if correlation_id else None
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=response_data,
        headers=headers
    )


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle custom API exceptions.
    
    Args:
        request: FastAPI request object
        exc: API exception
        
    Returns:
        JSON response with error details
    """
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Log API exception based on severity
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    logger.log(
        log_level,
        f"API exception in {request.method} {request.url.path}: {exc.message}",
        extra={
            "event_type": "api_exception",
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "error_message": exc.message,
            "correlation_id": correlation_id,
        }
    )
    
    error_response = ErrorResponse(
        message=exc.message,
        error_code=exc.error_code,
        details=exc.details
    )
    
    # Add correlation ID to response
    response_data = error_response.model_dump()
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    # Merge correlation ID header with existing headers
    headers = exc.headers or {}
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=headers if headers else None
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]) -> JSONResponse:
    """
    Handle HTTP exceptions.
    
    Args:
        request: FastAPI request object
        exc: HTTP exception
        
    Returns:
        JSON response with error details
    """
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Extract message from detail
    if isinstance(exc.detail, dict):
        message = exc.detail.get("message", "HTTP error occurred")
        error_code = exc.detail.get("error_code")
        details = exc.detail.get("details")
    elif isinstance(exc.detail, str):
        message = exc.detail
        error_code = None
        details = None
    else:
        message = "HTTP error occurred"
        error_code = None
        details = None
    
    # Log HTTP exception based on severity
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    logger.log(
        log_level,
        f"HTTP exception in {request.method} {request.url.path}: {message}",
        extra={
            "event_type": "http_exception",
            "method": request.method,
            "path": request.url.path,
            "status_code": exc.status_code,
            "error_message": message,
            "correlation_id": correlation_id,
        }
    )
    
    error_response = ErrorResponse(
        message=message,
        error_code=error_code,
        details=details
    )
    
    # Add correlation ID to response
    response_data = error_response.model_dump()
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    # Merge correlation ID header with existing headers
    headers = getattr(exc, 'headers', None) or {}
    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_data,
        headers=headers if headers else None
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle generic exceptions.
    
    Args:
        request: FastAPI request object
        exc: Generic exception
        
    Returns:
        JSON response with error details
    """
    # Get correlation ID from request state
    correlation_id = getattr(request.state, "correlation_id", None)
    
    # Log the exception with full context
    logger.exception(
        f"Unhandled exception in {request.method} {request.url.path}",
        extra={
            "event_type": "unhandled_exception",
            "method": request.method,
            "path": request.url.path,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "correlation_id": correlation_id,
        }
    )
    
    # Determine error message based on environment
    if is_development():
        # In development, show actual error message
        message = str(exc) if str(exc) else "An unexpected error occurred"
        details = [
            ErrorDetail(
                field="exception",
                message=str(exc),
                code=type(exc).__name__
            )
        ]
    else:
        # In production, use generic message
        message = "An internal server error occurred"
        details = None
    
    error_response = ErrorResponse(
        message=message,
        error_code="INTERNAL_SERVER_ERROR",
        details=details
    )
    
    # Add correlation ID to response
    response_data = error_response.model_dump()
    if correlation_id:
        response_data["correlation_id"] = correlation_id
    
    headers = {"X-Correlation-ID": correlation_id} if correlation_id else None
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_data,
        headers=headers
    )


def setup_exception_handlers(app):
    """
    Set up exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)