"""
Tests for FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app
import os
os.environ["API_ENV"] = "test"
os.environ["SKIP_CONFIG_INIT"] = "1"
os.environ["SKIP_CONFIG_VALIDATION"] = "1"

from src.app import create_app


class TestFastAPIApplication:
    """Test FastAPI application creation and configuration."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        return create_app("test")
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_create_app(self, app):
        """Test application creation."""
        assert app is not None
        assert app.title == "Production API Framework"
        assert app.version == "0.1.0"
    
    def test_health_check_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        
        response_data = response.json()
        assert response_data["success"] is True
        assert "data" in response_data
        
        data = response_data["data"]
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
    
    def test_readiness_check_endpoint(self, client):
        """Test readiness check endpoint."""
        response = client.get("/readyz")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
    
    def test_api_root_endpoint(self, client):
        """Test API root endpoint."""
        response = client.get("/api/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Production API Framework"
        assert "version" in data
        assert "health_url" in data
    
    def test_api_v1_root_endpoint(self, client):
        """Test API v1 root endpoint."""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "API Version 1"
        assert data["version"] == "1.0"
    
    def test_api_v1_status_endpoint(self, client):
        """Test API v1 status endpoint."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "operational"
        assert data["version"] == "1.0"
        assert "features" in data


class TestApplicationLifespan:
    """Test application lifespan management."""
    
    def test_lifespan_context_manager(self):
        """Test lifespan context manager."""
        from src.app import lifespan
        
        app = create_app("test")
        
        # Test that lifespan context manager can be created
        # Note: We can't easily test the actual startup/shutdown without
        # running the full application, but we can test the context manager exists
        assert lifespan is not None
        assert callable(lifespan)


class TestApplicationConfiguration:
    """Test application configuration for different environments."""
    
    def test_development_configuration(self):
        """Test development environment configuration."""
        app = create_app("development")
        
        # Development should have docs enabled
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"
    
    def test_production_configuration(self):
        """Test production environment configuration."""
        app = create_app("production")
        
        # Production should have docs disabled
        assert app.docs_url is None
        assert app.redoc_url is None
        assert app.openapi_url is None
    
    def test_test_configuration(self):
        """Test test environment configuration."""
        app = create_app("test")
        
        # Test should have docs enabled for testing
        assert app.docs_url == "/docs"
        assert app.redoc_url == "/redoc"
        assert app.openapi_url == "/openapi.json"