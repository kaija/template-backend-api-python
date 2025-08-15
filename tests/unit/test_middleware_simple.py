"""
Simple tests for error handling middleware.

This module tests the error handling middleware without requiring
the full configuration system.
"""

import os
import uuid
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# Skip configuration validation and initialization for tests
os.environ["SKIP_CONFIG_VALIDATION"] = "1"
os.environ["SKIP_CONFIG_INIT"] = "1"

from src.middleware.error_handling import (
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
)


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
    
    def test_client_ip_extraction(self):
        """Test client IP extraction from various headers."""
        app = FastAPI()
        middleware = RequestLoggingMiddleware(app)
        
        # Mock request with X-Forwarded-For header
        request = Mock()
        request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        request.client = None
        
        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"  # Should take the first IP
        
        # Mock request with X-Real-IP header
        request.headers = {"x-real-ip": "203.0.113.1"}
        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.1"
        
        # Mock request with client host fallback
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        ip = middleware._get_client_ip(request)
        assert ip == "127.0.0.1"


class TestErrorHandlingMiddleware:
    """Test error handling middleware."""
    
    @patch('src.middleware.error_handling.is_development')
    def test_error_handling_development(self, mock_is_dev):
        """Test error handling in development environment."""
        from src.middleware.error_handling import ErrorHandlingMiddleware
        
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
    
    @patch('src.middleware.error_handling.is_development')
    @patch('src.middleware.error_handling.is_production')
    def test_error_handling_production(self, mock_is_prod, mock_is_dev):
        """Test error handling in production environment."""
        from src.middleware.error_handling import ErrorHandlingMiddleware
        
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
    
    @patch('src.middleware.error_handling.is_development')
    @patch('src.middleware.error_handling.logger')
    def test_error_logging(self, mock_logger, mock_is_dev):
        """Test that errors are logged with proper context."""
        from src.middleware.error_handling import ErrorHandlingMiddleware
        
        mock_is_dev.return_value = True
        
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        app.add_middleware(ErrorHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValueError("Test error for logging")
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 500
        
        # Check that error was logged
        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args
        
        assert "Unhandled exception" in log_call[0][0]
        assert "correlation_id" in log_call[1]["extra"]
        assert "request_info" in log_call[1]["extra"]
    
    @patch('src.middleware.error_handling.is_development')
    def test_correlation_id_consistency(self, mock_is_dev):
        """Test that correlation ID is consistent across error handling."""
        from src.middleware.error_handling import ErrorHandlingMiddleware
        
        mock_is_dev.return_value = True
        
        app = FastAPI()
        app.add_middleware(CorrelationIDMiddleware)
        app.add_middleware(ErrorHandlingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            raise ValueError("Test error")
        
        client = TestClient(app)
        correlation_id = "test-correlation-123"
        
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": correlation_id}
        )
        
        assert response.status_code == 500
        data = response.json()
        
        # Check that the same correlation ID is used
        assert data["correlation_id"] == correlation_id
        assert response.headers["X-Correlation-ID"] == correlation_id