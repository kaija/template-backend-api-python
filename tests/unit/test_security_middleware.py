"""
Tests for security middleware.

This module tests the security middleware components including
security headers, rate limiting, and trusted hosts.
"""

import os
import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# Skip configuration validation and initialization for tests
os.environ["SKIP_CONFIG_VALIDATION"] = "1"
os.environ["SKIP_CONFIG_INIT"] = "1"

from src.middleware.security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    TrustedHostMiddleware,
)


class TestSecurityHeadersMiddleware:
    """Test security headers middleware."""
    
    @patch('src.middleware.security.is_development')
    @patch('src.middleware.security.is_production')
    def test_default_security_headers(self, mock_is_prod, mock_is_dev):
        """Test that default security headers are added."""
        mock_is_dev.return_value = True
        mock_is_prod.return_value = False
        
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        
        # Check security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Permissions-Policy" in response.headers
        assert "Content-Security-Policy" in response.headers
    
    @patch('src.middleware.security.is_development')
    @patch('src.middleware.security.is_production')
    def test_hsts_header_production(self, mock_is_prod, mock_is_dev):
        """Test HSTS header is added in production."""
        mock_is_dev.return_value = False
        mock_is_prod.return_value = True
        
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "Strict-Transport-Security" in response.headers
        assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    
    @patch('src.middleware.security.is_development')
    @patch('src.middleware.security.is_production')
    def test_no_hsts_header_development(self, mock_is_prod, mock_is_dev):
        """Test HSTS header is not added in development."""
        mock_is_dev.return_value = True
        mock_is_prod.return_value = False
        
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "Strict-Transport-Security" not in response.headers
    
    @patch('src.middleware.security.is_development')
    @patch('src.middleware.security.is_production')
    def test_custom_headers(self, mock_is_prod, mock_is_dev):
        """Test custom security headers."""
        mock_is_dev.return_value = True
        mock_is_prod.return_value = False
        
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "X-Another-Header": "another-value"
        }
        
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, custom_headers=custom_headers)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.headers["X-Custom-Header"] == "custom-value"
        assert response.headers["X-Another-Header"] == "another-value"
    
    @patch('src.middleware.security.is_development')
    @patch('src.middleware.security.is_production')
    def test_custom_csp_policy(self, mock_is_prod, mock_is_dev):
        """Test custom CSP policy."""
        mock_is_dev.return_value = True
        mock_is_prod.return_value = False
        
        custom_csp = "default-src 'self'; script-src 'self' 'unsafe-inline'"
        
        app = FastAPI()
        app.add_middleware(
            SecurityHeadersMiddleware, 
            csp_policy=custom_csp
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert response.headers["Content-Security-Policy"] == custom_csp


class TestRateLimitMiddleware:
    """Test rate limiting middleware."""
    
    def test_rate_limiting_disabled(self):
        """Test that requests pass through when rate limiting is disabled."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, enabled=False)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Make multiple requests
        for _ in range(10):
            response = client.get("/test")
            assert response.status_code == 200
    
    def test_rate_limiting_headers(self):
        """Test that rate limiting headers are added."""
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware, 
            requests_per_minute=10,
            enabled=True
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "10"
    
    def test_client_ip_extraction(self):
        """Test client IP extraction from headers."""
        app = FastAPI()
        middleware = RateLimitMiddleware(app, enabled=True)
        
        # Mock request with X-Forwarded-For header
        request = Mock()
        request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        request.client = None
        
        client_id = middleware._get_client_id(request)
        assert client_id == "192.168.1.1"
        
        # Mock request with X-Real-IP header
        request.headers = {"x-real-ip": "203.0.113.1"}
        client_id = middleware._get_client_id(request)
        assert client_id == "203.0.113.1"
        
        # Mock request with client host fallback
        request.headers = {}
        request.client = Mock()
        request.client.host = "127.0.0.1"
        
        client_id = middleware._get_client_id(request)
        assert client_id == "127.0.0.1"


class TestTrustedHostMiddleware:
    """Test trusted host middleware."""
    
    def test_allowed_host(self):
        """Test that allowed hosts pass through."""
        app = FastAPI()
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com", "api.example.com"],
            allow_any=False
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test", headers={"host": "example.com"})
        
        assert response.status_code == 200
    
    def test_disallowed_host(self):
        """Test that disallowed hosts are rejected."""
        app = FastAPI()
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com"],
            allow_any=False
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test", headers={"host": "malicious.com"})
        
        assert response.status_code == 400
        assert "Invalid host header" in response.json()["detail"]
    
    def test_wildcard_subdomain(self):
        """Test wildcard subdomain matching."""
        app = FastAPI()
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.example.com"],
            allow_any=False
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        
        # Should allow subdomains
        response = client.get("/test", headers={"host": "api.example.com"})
        assert response.status_code == 200
        
        response = client.get("/test", headers={"host": "www.example.com"})
        assert response.status_code == 200
        
        # Should allow root domain
        response = client.get("/test", headers={"host": "example.com"})
        assert response.status_code == 200
        
        # Should reject other domains
        response = client.get("/test", headers={"host": "malicious.com"})
        assert response.status_code == 400
        assert "Invalid host header" in response.json()["detail"]
    
    def test_allow_any_hosts(self):
        """Test allowing any host."""
        app = FastAPI()
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com"],
            allow_any=True
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test", headers={"host": "any-host.com"})
        
        assert response.status_code == 200
    
    def test_host_with_port(self):
        """Test host validation with port numbers."""
        app = FastAPI()
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com"],
            allow_any=False
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test", headers={"host": "example.com:8000"})
        
        assert response.status_code == 200
    
    def test_wildcard_all_hosts(self):
        """Test wildcard for all hosts."""
        app = FastAPI()
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],
            allow_any=False
        )
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        client = TestClient(app)
        response = client.get("/test", headers={"host": "any-host.com"})
        
        assert response.status_code == 200