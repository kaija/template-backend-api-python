"""
Tests for observability and monitoring functionality.

This module tests the structured logging, metrics collection,
and monitoring middleware functionality.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.utils.logging import (
    get_logger,
    log_request,
    log_response,
    configure_structlog,
    SensitiveDataProcessor,
    CorrelationIDProcessor,
)
from src.monitoring.metrics import (
    metrics_collector,
    get_metrics_data,
    MetricsTimer,
    track_http_request,
)
from src.middleware.observability import ObservabilityMiddleware


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_get_logger(self):
        """Test getting a structured logger."""
        logger = get_logger("test")
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
    
    def test_sensitive_data_processor(self):
        """Test sensitive data masking in logs."""
        processor = SensitiveDataProcessor()
        
        # Test sensitive data masking
        event_dict = {
            "password": "secret123",
            "token": "abc123",
            "normal_field": "normal_value",
            "nested": {
                "api_key": "key123",
                "safe_field": "safe_value"
            }
        }
        
        result = processor(Mock(), "info", event_dict)
        
        assert result["password"] == "***MASKED***"
        assert result["token"] == "***MASKED***"
        assert result["normal_field"] == "normal_value"
        assert result["nested"]["api_key"] == "***MASKED***"
        assert result["nested"]["safe_field"] == "safe_value"
    
    def test_correlation_id_processor(self):
        """Test correlation ID processing."""
        processor = CorrelationIDProcessor()
        
        # Test with correlation ID in event dict
        event_dict = {"correlation_id": "test-123", "message": "test"}
        result = processor(Mock(), "info", event_dict)
        assert result["correlation_id"] == "test-123"
        
        # Test without correlation ID
        event_dict = {"message": "test"}
        result = processor(Mock(), "info", event_dict)
        # Should not add correlation ID if not present
        assert "correlation_id" not in result or result["correlation_id"] is None
    
    @patch('src.utils.logging.logger')
    def test_log_request(self, mock_logger):
        """Test HTTP request logging."""
        log_request(
            method="GET",
            path="/test",
            query_params={"param": "value"},
            headers={"authorization": "Bearer token123"},
            client_ip="127.0.0.1",
            user_id="user123",
            correlation_id="corr-123"
        )
        
        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "HTTP request" in call_args[0][0]
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["path"] == "/test"
        assert call_args[1]["correlation_id"] == "corr-123"
    
    @patch('src.utils.logging.logger')
    def test_log_response(self, mock_logger):
        """Test HTTP response logging."""
        log_response(
            method="GET",
            path="/test",
            status_code=200,
            response_time_ms=123.45,
            correlation_id="corr-123"
        )
        
        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "HTTP response" in call_args[0][0]
        assert call_args[1]["status_code"] == 200
        assert call_args[1]["response_time_ms"] == 123.45


class TestMetrics:
    """Test Prometheus metrics functionality."""
    
    def test_metrics_collector_http_request(self):
        """Test HTTP request metrics tracking."""
        # Track a request
        metrics_collector.track_http_request(
            method="GET",
            endpoint="/test",
            status_code=200,
            duration_seconds=0.123,
            request_size=1024,
            response_size=2048
        )
        
        # Get metrics data
        metrics_data = get_metrics_data()
        
        # Verify metrics are present
        assert "http_requests_total" in metrics_data
        assert "http_request_duration_seconds" in metrics_data
        assert "http_request_size_bytes" in metrics_data
        assert "http_response_size_bytes" in metrics_data
    
    def test_metrics_collector_auth_attempt(self):
        """Test authentication metrics tracking."""
        metrics_collector.track_auth_attempt("jwt", "success")
        metrics_collector.track_auth_attempt("api_key", "failure")
        
        metrics_data = get_metrics_data()
        assert "auth_attempts_total" in metrics_data
    
    def test_metrics_collector_db_query(self):
        """Test database query metrics tracking."""
        metrics_collector.track_db_query(
            operation="SELECT",
            table="users",
            duration_seconds=0.05,
            status="success"
        )
        
        metrics_data = get_metrics_data()
        assert "db_queries_total" in metrics_data
        assert "db_query_duration_seconds" in metrics_data
    
    def test_metrics_timer(self):
        """Test metrics timer context manager."""
        import time
        
        with MetricsTimer() as timer:
            time.sleep(0.01)  # Small delay
        
        assert timer.duration is not None
        assert timer.duration > 0
        assert timer.duration < 1  # Should be less than 1 second
    
    def test_track_http_request_convenience_function(self):
        """Test convenience function for HTTP request tracking."""
        track_http_request("POST", "/api/users", 201, 0.234)
        
        metrics_data = get_metrics_data()
        assert "http_requests_total" in metrics_data
        assert "http_request_duration_seconds" in metrics_data


class TestObservabilityMiddleware:
    """Test observability middleware functionality."""
    
    def test_middleware_initialization(self):
        """Test middleware initialization with different options."""
        app = FastAPI()
        
        middleware = ObservabilityMiddleware(
            app,
            log_requests=True,
            log_responses=True,
            mask_sensitive_data=True,
            track_performance=True
        )
        
        assert middleware.log_requests is True
        assert middleware.log_responses is True
        assert middleware.mask_sensitive_data is True
        assert middleware.track_performance is True
    
    def test_sensitive_data_masking(self):
        """Test sensitive data masking in middleware."""
        app = FastAPI()
        middleware = ObservabilityMiddleware(app, mask_sensitive_data=True)
        
        # Test header masking
        headers = {
            "authorization": "Bearer token123",
            "x-api-key": "key123",
            "content-type": "application/json",
            "user-agent": "test-client"
        }
        
        masked = middleware._mask_sensitive_data(headers, middleware.sensitive_headers)
        
        assert masked["authorization"] == "***MASKED***"
        assert masked["x-api-key"] == "***MASKED***"
        assert masked["content-type"] == "application/json"
        assert masked["user-agent"] == "test-client"
    
    def test_client_ip_extraction(self):
        """Test client IP extraction from various headers."""
        from fastapi import Request
        
        app = FastAPI()
        middleware = ObservabilityMiddleware(app)
        
        # Mock request with X-Forwarded-For header
        mock_request = Mock(spec=Request)
        mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        mock_request.client = None
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.1"
        
        # Mock request with X-Real-IP header
        mock_request.headers = {"x-real-ip": "192.168.1.2"}
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.2"
        
        # Mock request with client info
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.3"
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.3"
    
    def test_sensitive_pattern_detection(self):
        """Test sensitive pattern detection in values."""
        app = FastAPI()
        middleware = ObservabilityMiddleware(app)
        
        # Test sensitive patterns
        assert middleware._contains_sensitive_pattern("Bearer abc123") is True
        assert middleware._contains_sensitive_pattern("Basic dXNlcjpwYXNz") is True
        assert middleware._contains_sensitive_pattern("token=abc123") is True
        assert middleware._contains_sensitive_pattern("normal value") is False
        assert middleware._contains_sensitive_pattern("application/json") is False


class TestMetricsEndpoint:
    """Test metrics endpoint functionality."""
    
    def test_metrics_endpoint_response_format(self):
        """Test that metrics endpoint returns proper Prometheus format."""
        from src.routes.metrics import router
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        
        # Check for basic Prometheus metrics format
        content = response.text
        assert "# HELP" in content or "# TYPE" in content or "_total" in content
    
    def test_metrics_endpoint_caching_headers(self):
        """Test that metrics endpoint has proper caching headers."""
        from src.routes.metrics import router
        
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        
        response = client.get("/metrics")
        
        assert response.status_code == 200
        assert "no-cache" in response.headers.get("cache-control", "")
        assert "no-store" in response.headers.get("cache-control", "")


@pytest.fixture
def app_with_observability():
    """Create FastAPI app with observability middleware for testing."""
    app = FastAPI()
    
    # Add observability middleware
    app.add_middleware(
        ObservabilityMiddleware,
        log_requests=True,
        log_responses=True,
        mask_sensitive_data=True,
        track_performance=True
    )
    
    # Add a test endpoint
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.post("/test-post")
    async def test_post_endpoint(data: dict):
        return {"received": data}
    
    return app


class TestObservabilityIntegration:
    """Test observability integration with FastAPI."""
    
    def test_request_response_logging_integration(self, app_with_observability):
        """Test that requests and responses are logged properly."""
        client = TestClient(app_with_observability)
        
        with patch('src.utils.logging.log_request') as mock_log_request, \
             patch('src.utils.logging.log_response') as mock_log_response:
            
            response = client.get("/test")
            
            assert response.status_code == 200
            
            # Verify request logging was called
            mock_log_request.assert_called_once()
            call_args = mock_log_request.call_args[1]
            assert call_args["method"] == "GET"
            assert call_args["path"] == "/test"
            
            # Verify response logging was called
            mock_log_response.assert_called_once()
            call_args = mock_log_response.call_args[1]
            assert call_args["method"] == "GET"
            assert call_args["path"] == "/test"
            assert call_args["status_code"] == 200
    
    def test_performance_tracking_integration(self, app_with_observability):
        """Test that performance metrics are tracked."""
        client = TestClient(app_with_observability)
        
        with patch('src.monitoring.metrics.metrics_collector.track_http_request') as mock_track:
            response = client.get("/test")
            
            assert response.status_code == 200
            
            # Verify performance tracking was called
            mock_track.assert_called_once()
            call_args = mock_track.call_args[1]
            assert call_args["method"] == "GET"
            assert call_args["endpoint"] == "/test"
            assert call_args["status_code"] == 200
            assert "duration_seconds" in call_args
    
    def test_response_time_header(self, app_with_observability):
        """Test that response time header is added."""
        client = TestClient(app_with_observability)
        
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Response-Time" in response.headers
        assert "ms" in response.headers["X-Response-Time"]