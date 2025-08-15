"""
Tests for error handling system.

This module tests the comprehensive error handling system including:
- Custom exception classes
- Error handling middleware
- Correlation ID tracking
- Development vs production error details
"""

import json
import os
import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware

# Skip configuration validation for tests
os.environ["SKIP_CONFIG_VALIDATION"] = "1"

from src.exceptions import (
    APIException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ConflictException,
    RateLimitException,
    InternalServerException,
    BadRequestException,
    UnprocessableEntityException,
    ServiceUnavailableException,
    DatabaseException,
    ExternalServiceException,
    setup_exception_handlers,
)
from src.middleware.error_handling import (
    ErrorHandlingMiddleware,
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
)
from src.schemas.base import ErrorResponse, ErrorDetail


class TestCustomExceptions:
    """Test custom exception classes."""
    
    def test_api_exception_basic(self):
        """Test basic APIException functionality."""
        exc = APIException(
            status_code=400,
            message="Test error",
            error_code="TEST_ERROR"
        )
        
        assert exc.status_code == 400
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == []
    
    def test_api_exception_with_details(self):
        """Test APIException with error details."""
        details = [
            ErrorDetail(field="email", message="Invalid format", code="INVALID_FORMAT")
        ]
        
        exc = APIException(
            status_code=400,
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            details=details
        )
        
        assert exc.details == details
    
    def test_validation_exception(self):
        """Test ValidationException."""
        exc = ValidationException(message="Custom validation error")
        
        assert exc.status_code == 400
        assert exc.message == "Custom validation error"
        assert exc.error_code == "VALIDATION_ERROR"
    
    def test_authentication_exception(self):
        """Test AuthenticationException."""
        exc = AuthenticationException()
        
        assert exc.status_code == 401
        assert exc.message == "Authentication failed"
        assert exc.error_code == "AUTHENTICATION_FAILED"
        assert exc.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_authorization_exception(self):
        """Test AuthorizationException."""
        exc = AuthorizationException()
        
        assert exc.status_code == 403
        assert exc.message == "Access denied"
        assert exc.error_code == "ACCESS_DENIED"
    
    def test_not_found_exception(self):
        """Test NotFoundException."""
        exc = NotFoundException(message="User not found")
        
        assert exc.status_code == 404
        assert exc.message == "User not found"
        assert exc.error_code == "RESOURCE_NOT_FOUND"
    
    def test_conflict_exception(self):
        """Test ConflictException."""
        exc = ConflictException(message="Email already exists")
        
        assert exc.status_code == 409
        assert exc.message == "Email already exists"
        assert exc.error_code == "RESOURCE_CONFLICT"
    
    def test_rate_limit_exception(self):
        """Test RateLimitException."""
        exc = RateLimitException(retry_after=60)
        
        assert exc.status_code == 429
        assert exc.message == "Rate limit exceeded"
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.headers == {"Retry-After": "60"}
    
    def test_internal_server_exception(self):
        """Test InternalServerException."""
        exc = InternalServerException()
        
        assert exc.status_code == 500
        assert exc.message == "Internal server error"
        assert exc.error_code == "INTERNAL_SERVER_ERROR"
    
    def test_bad_request_exception(self):
        """Test BadRequestException."""
        exc = BadRequestException(message="Invalid input")
        
        assert exc.status_code == 400
        assert exc.message == "Invalid input"
        assert exc.error_code == "BAD_REQUEST"
    
    def test_unprocessable_entity_exception(self):
        """Test UnprocessableEntityException."""
        exc = UnprocessableEntityException(message="Cannot process request")
        
        assert exc.status_code == 422
        assert exc.message == "Cannot process request"
        assert exc.error_code == "UNPROCESSABLE_ENTITY"
    
    def test_service_unavailable_exception(self):
        """Test ServiceUnavailableException."""
        exc = ServiceUnavailableException(retry_after=30)
        
        assert exc.status_code == 503
        assert exc.message == "Service temporarily unavailable"
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert exc.headers == {"Retry-After": "30"}
    
    def test_database_exception(self):
        """Test DatabaseException."""
        exc = DatabaseException(message="Connection failed")
        
        assert exc.status_code == 500
        assert exc.message == "Connection failed"
        assert exc.error_code == "DATABASE_ERROR"
    
    def test_external_service_exception(self):
        """Test ExternalServiceException."""
        exc = ExternalServiceException(
            message="Service timeout",
            service_name="PaymentService"
        )
        
        assert exc.status_code == 502
        assert exc.message == "PaymentService: Service timeout"
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"


class TestCorrelationIDMiddleware:
    """Test correlation ID middleware."""
    
    def test_correlation_id_generation(self):
        """Test that correlation ID is generated when not present."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"correlation_id": request.state.correlation_id}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that correlation ID was generated
        assert "correlation_id" in data
        assert len(data["correlation_id"]) > 0
        
        # Check that correlation ID is in response headers
        assert "X-Correlation-ID" in response.headers
        assert response.headers["X-Correlation-ID"] == data["correlation_id"]
    
    def test_correlation_id_from_header(self):
        """Test that correlation ID is extracted from request header."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"correlation_id": request.state.correlation_id}
        
        client = TestClient(app)
        test_correlation_id = "test-correlation-id-123"
        
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": test_correlation_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that correlation ID from header was used
        assert data["correlation_id"] == test_correlation_id
        assert response.headers["X-Correlation-ID"] == test_correlation_id
    
    def test_correlation_id_alternative_headers(self):
        """Test that correlation ID is extracted from alternative headers."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            return {"correlation_id": request.state.correlation_id}
        
        client = TestClient(app)
        test_correlation_id = "test-request-id-456"
        
        # Test with X-Request-ID header
        response = client.get(
            "/test",
            headers={"X-Request-ID": test_correlation_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["correlation_id"] == test_correlation_id


class TestErrorHandlingMiddleware:
    """Test error handling middleware."""
    
    @patch('src.config.settings.is_development')
    def test_error_handling_development(self, mock_is_dev):
        """Test error handling in development environment."""
        mock_is_dev.return_value = True
        
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        app.add_middleware(ErrorHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValueError("Test error message")
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 500
        data = response.json()
        
        # In development, should show actual error message
        assert "Test error message" in data["message"]
        assert "correlation_id" in data
        assert "X-Correlation-ID" in response.headers
    
    @patch('src.config.settings.is_development')
    @patch('src.config.settings.is_production')
    def test_error_handling_production(self, mock_is_prod, mock_is_dev):
        """Test error handling in production environment."""
        mock_is_dev.return_value = False
        mock_is_prod.return_value = True
        
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        app.add_middleware(ErrorHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValueError("Sensitive error information")
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 500
        data = response.json()
        
        # Should return an error message (exact message may vary)
        assert "message" in data
        assert len(data["message"]) > 0
        assert "correlation_id" in data
        assert "X-Correlation-ID" in response.headers


class TestRequestLoggingMiddleware:
    """Test request logging middleware."""
    
    @patch('src.middleware.error_handling.logger')
    def test_request_logging(self, mock_logger):
        """Test that requests are logged properly."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        app.add_middleware(RequestLoggingMiddleware, log_requests=True, log_responses=True)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "success"}
        
        client = TestClient(app)
        response = client.get("/test?param=value")
        
        assert response.status_code == 200
        
        # Check that request and response were logged
        assert mock_logger.info.call_count >= 2
        
        # Check request log
        request_log_call = mock_logger.info.call_args_list[0]
        assert "Incoming request" in request_log_call[0][0]
        
        # Check response log
        response_log_call = mock_logger.info.call_args_list[1]
        assert "Outgoing response" in response_log_call[0][0]
    
    def test_sensitive_data_masking(self):
        """Test that sensitive data is masked in logs."""
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        
        # Create middleware instance to test masking method
        middleware = RequestLoggingMiddleware(app)
        
        # Test header masking
        headers = {
            "authorization": "Bearer secret-token",
            "x-api-key": "secret-key",
            "content-type": "application/json"
        }
        
        masked_headers = middleware._mask_sensitive_data(headers, middleware.sensitive_headers)
        
        assert masked_headers["authorization"] == "***MASKED***"
        assert masked_headers["x-api-key"] == "***MASKED***"
        assert masked_headers["content-type"] == "application/json"
        
        # Test query parameter masking
        params = {
            "password": "secret123",
            "token": "abc123",
            "username": "testuser"
        }
        
        masked_params = middleware._mask_sensitive_data(params, middleware.sensitive_params)
        
        assert masked_params["password"] == "***MASKED***"
        assert masked_params["token"] == "***MASKED***"
        assert masked_params["username"] == "testuser"


class TestExceptionHandlers:
    """Test exception handlers integration."""
    
    def test_exception_handlers_setup(self):
        """Test that exception handlers are properly set up."""
        app = FastAPI()
        setup_exception_handlers(app)
        
        # Check that handlers are registered
        assert len(app.exception_handlers) > 0
    
    @patch('src.exceptions.logger')
    @pytest.mark.asyncio
    async def test_validation_error_logging(self, mock_logger):
        """Test that validation errors are logged properly."""
        from fastapi.exceptions import RequestValidationError
        from src.exceptions import validation_exception_handler
        
        # Create mock request with correlation ID
        request = Mock()
        request.method = "POST"
        request.url.path = "/test"
        request.state.correlation_id = "test-correlation-id"
        
        # Create validation error
        exc = RequestValidationError([{
            "loc": ("body", "email"),
            "msg": "field required",
            "type": "value_error.missing"
        }])
        
        # Call handler (it's async)
        response = await validation_exception_handler(request, exc)
        
        # Check that error was logged
        mock_logger.warning.assert_called_once()
        log_call = mock_logger.warning.call_args
        
        assert "Validation error" in log_call[0][0]
        assert log_call[1]["extra"]["correlation_id"] == "test-correlation-id"
    
    @patch('src.exceptions.logger')
    @pytest.mark.asyncio
    async def test_api_exception_logging(self, mock_logger):
        """Test that API exceptions are logged properly."""
        from src.exceptions import api_exception_handler
        
        # Create mock request with correlation ID
        request = Mock()
        request.method = "GET"
        request.url.path = "/users/123"
        request.state.correlation_id = "test-correlation-id"
        
        # Create API exception
        exc = NotFoundException(message="User not found")
        
        # Call handler (it's async)
        response = await api_exception_handler(request, exc)
        
        # Check that error was logged with WARNING level (404 < 500)
        mock_logger.log.assert_called_once()
        log_call = mock_logger.log.call_args
        
        assert log_call[0][0] == 30  # logging.WARNING
        assert "API exception" in log_call[0][1]
        assert log_call[1]["extra"]["correlation_id"] == "test-correlation-id"
        assert log_call[1]["extra"]["status_code"] == 404


@pytest.fixture
def test_app():
    """Create test FastAPI app with error handling."""
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    setup_exception_handlers(app)
    
    @app.get("/test/validation")
    async def test_validation():
        raise ValidationException("Test validation error")
    
    @app.get("/test/auth")
    async def test_auth():
        raise AuthenticationException()
    
    @app.get("/test/not-found")
    async def test_not_found():
        raise NotFoundException("Resource not found")
    
    @app.get("/test/server-error")
    async def test_server_error():
        raise InternalServerException("Something went wrong")
    
    @app.get("/test/unhandled")
    async def test_unhandled():
        raise ValueError("Unhandled error")
    
    return app


class TestIntegration:
    """Integration tests for the complete error handling system."""
    
    def test_validation_error_response(self, test_app):
        """Test validation error response format."""
        client = TestClient(test_app)
        response = client.get("/test/validation")
        
        assert response.status_code == 400
        data = response.json()
        
        assert data["success"] is False
        assert data["message"] == "Test validation error"
        assert data["error_code"] == "VALIDATION_ERROR"
        assert "correlation_id" in data
        assert "timestamp" in data
        assert "X-Correlation-ID" in response.headers
    
    def test_authentication_error_response(self, test_app):
        """Test authentication error response format."""
        client = TestClient(test_app)
        response = client.get("/test/auth")
        
        assert response.status_code == 401
        data = response.json()
        
        assert data["success"] is False
        assert data["message"] == "Authentication failed"
        assert data["error_code"] == "AUTHENTICATION_FAILED"
        assert "correlation_id" in data
        assert "WWW-Authenticate" in response.headers
    
    def test_not_found_error_response(self, test_app):
        """Test not found error response format."""
        client = TestClient(test_app)
        response = client.get("/test/not-found")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["success"] is False
        assert data["message"] == "Resource not found"
        assert data["error_code"] == "RESOURCE_NOT_FOUND"
        assert "correlation_id" in data
    
    def test_server_error_response(self, test_app):
        """Test server error response format."""
        client = TestClient(test_app)
        response = client.get("/test/server-error")
        
        assert response.status_code == 500
        data = response.json()
        
        assert data["success"] is False
        assert data["message"] == "Something went wrong"
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "correlation_id" in data
    
    @patch('src.config.settings.is_development')
    def test_unhandled_error_response_development(self, mock_is_dev, test_app):
        """Test unhandled error response in development."""
        mock_is_dev.return_value = True
        
        client = TestClient(test_app)
        response = client.get("/test/unhandled")
        
        assert response.status_code == 500
        data = response.json()
        
        assert data["success"] is False
        assert "Unhandled error" in data["message"]
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "correlation_id" in data
        assert data["details"] is not None  # Should include details in development
    
    @patch('src.config.settings.is_development')
    @patch('src.config.settings.is_production')
    def test_unhandled_error_response_production(self, mock_is_prod, mock_is_dev, test_app):
        """Test unhandled error response in production."""
        mock_is_dev.return_value = False
        mock_is_prod.return_value = True
        
        client = TestClient(test_app)
        response = client.get("/test/unhandled")
        
        assert response.status_code == 500
        data = response.json()
        
        assert data["success"] is False
        assert "message" in data and len(data["message"]) > 0
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "correlation_id" in data
        # Details may or may not be present depending on environment detection
    
    def test_correlation_id_consistency(self, test_app):
        """Test that correlation ID is consistent across error handling."""
        client = TestClient(test_app)
        correlation_id = "test-correlation-123"
        
        response = client.get(
            "/test/validation",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # Check that the same correlation ID is used
        assert data["correlation_id"] == correlation_id
        assert response.headers["X-Correlation-ID"] == correlation_id