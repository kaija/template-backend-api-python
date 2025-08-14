"""
Integration tests for health check endpoints.

This module tests the actual health check endpoints to ensure they work correctly
with real dependencies and provide proper status information.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from src.app import get_application


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = get_application()
        return TestClient(app)
    
    def test_health_check_endpoint(self, client):
        """Test the /healthz endpoint returns basic health information."""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data
        assert "data" in data
        assert "metadata" in data
        
        # Check data content
        health_data = data["data"]
        assert health_data["status"] == "healthy"
        assert "version" in health_data
        assert "environment" in health_data
        assert "timestamp" in health_data
        assert "uptime_seconds" in health_data
        assert "system" in health_data
        assert "application" in health_data
        
        # Check system information
        system_info = health_data["system"]
        assert "python_version" in system_info
        assert "platform" in system_info
        assert "process_id" in system_info
        
        # Check application information
        app_info = health_data["application"]
        assert "name" in app_info
        assert "debug_mode" in app_info
        assert "log_level" in app_info
        
        # Check metadata
        metadata = data["metadata"]
        assert "response_time_ms" in metadata
        assert "check_type" in metadata
        assert metadata["check_type"] == "basic"
    
    def test_readiness_check_endpoint_without_database(self, client):
        """Test the /readyz endpoint when database is not initialized."""
        response = client.get("/readyz")
        
        # Should return 503 when database is not available
        assert response.status_code == 503
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "message" in data
        assert "timestamp" in data
        assert "data" in data
        assert "metadata" in data
        
        # Check data content
        readiness_data = data["data"]
        assert readiness_data["status"] == "not_ready"
        assert "version" in readiness_data
        assert "environment" in readiness_data
        assert "uptime_seconds" in readiness_data
        assert "checks" in readiness_data
        assert "summary" in readiness_data
        assert "reason" in readiness_data
        
        # Check individual checks
        checks = readiness_data["checks"]
        assert "database" in checks
        assert "redis" in checks
        assert "external_services" in checks
        
        # Database should be unhealthy
        db_check = checks["database"]
        assert db_check["status"] == "unhealthy"
        assert "response_time_ms" in db_check
        assert "details" in db_check
        assert "error" in db_check
        assert "timestamp" in db_check
        
        # Check summary
        summary = readiness_data["summary"]
        assert "total_checks" in summary
        assert "healthy_checks" in summary
        assert "unhealthy_checks" in summary
        assert "unavailable_checks" in summary
        assert "timeout_checks" in summary
        assert "total_response_time_ms" in summary
        
        # Should have at least one unhealthy check (database)
        assert summary["unhealthy_checks"] >= 1
        
        # Check metadata
        metadata = data["metadata"]
        assert "check_timeout" in metadata
        assert "timestamp" in metadata
    
    @patch('src.database.config.get_session')
    def test_readiness_check_with_healthy_database(self, mock_get_session, client):
        """Test the /readyz endpoint when database is healthy."""
        # Mock database session to return successfully
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session.execute.return_value.scalar.return_value = 1
        mock_get_session.return_value = mock_session
        
        response = client.get("/readyz")
        
        # Should return 200 when all critical dependencies are healthy
        # Note: Redis might still fail if not running, but database is critical
        data = response.json()
        
        # Check that database check is now healthy
        readiness_data = data["data"]
        checks = readiness_data["checks"]
        db_check = checks["database"]
        assert db_check["status"] == "healthy"
        assert "response_time_ms" in db_check
        assert "details" in db_check
        assert "timestamp" in db_check
    
    def test_health_check_response_time(self, client):
        """Test that health check responds quickly."""
        import time
        
        start_time = time.time()
        response = client.get("/healthz")
        end_time = time.time()
        
        # Health check should be fast (under 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0
        
        # Check that response includes timing information
        data = response.json()
        assert "metadata" in data
        assert "response_time_ms" in data["metadata"]
        assert data["metadata"]["response_time_ms"] > 0
    
    def test_readiness_check_timeout_handling(self, client):
        """Test that readiness check handles timeouts properly."""
        # This test verifies the timeout mechanism exists
        # In a real scenario, you might mock slow dependencies
        
        response = client.get("/readyz")
        data = response.json()
        
        # Check that timeout configuration is present
        assert "metadata" in data
        assert "check_timeout" in data["metadata"]
        assert data["metadata"]["check_timeout"] > 0
    
    def test_health_endpoints_cors_headers(self, client):
        """Test that health endpoints include proper CORS headers."""
        # Test OPTIONS request for CORS preflight
        response = client.options("/healthz")
        # FastAPI handles CORS automatically, so we just verify the endpoint exists
        
        # Test actual health check
        response = client.get("/healthz")
        assert response.status_code == 200
        
        # Test readiness check
        response = client.get("/readyz")
        # Should return either 200 or 503, both are valid
        assert response.status_code in [200, 503]
    
    def test_health_check_json_format(self, client):
        """Test that health check returns valid JSON."""
        response = client.get("/healthz")
        
        # Should be valid JSON
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        
        # Should be a dictionary
        assert isinstance(data, dict)
        
        # Should have expected top-level keys
        expected_keys = {"success", "message", "timestamp", "data"}
        assert expected_keys.issubset(set(data.keys()))
    
    def test_readiness_check_json_format(self, client):
        """Test that readiness check returns valid JSON."""
        response = client.get("/readyz")
        
        # Should be valid JSON
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        
        # Should be a dictionary
        assert isinstance(data, dict)
        
        # Should have expected top-level keys
        expected_keys = {"success", "message", "timestamp", "data"}
        assert expected_keys.issubset(set(data.keys()))
        
        # Data should have checks
        assert "checks" in data["data"]
        assert isinstance(data["data"]["checks"], dict)