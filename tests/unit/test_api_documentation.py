"""
Tests for API documentation functionality.

This module tests the comprehensive API documentation system including
OpenAPI schema generation, access controls, and interactive documentation.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.app import create_app
from src.config.documentation import (
    get_docs_access_config,
    get_custom_openapi_schema,
    verify_docs_access,
    customize_openapi_responses,
)


class TestDocumentationConfiguration:
    """Test documentation configuration functionality."""
    
    def test_get_docs_access_config_development(self):
        """Test docs access config in development environment."""
        with patch('src.config.documentation.is_production', return_value=False):
            with patch('src.config.documentation.settings') as mock_settings:
                mock_settings.docs_require_auth = False
                mock_settings.docs_api_key = "test-key"
                mock_settings.docs_allowed_roles = ["admin", "developer"]
                
                config = get_docs_access_config()
                
                assert config["require_auth"] is False
                assert config["api_key"] == "test-key"
                assert "admin" in config["allowed_roles"]
                assert "developer" in config["allowed_roles"]
    
    def test_get_docs_access_config_production(self):
        """Test docs access config in production environment."""
        with patch('src.config.documentation.is_production', return_value=True):
            with patch('src.config.documentation.settings') as mock_settings:
                mock_settings.docs_require_auth = True
                mock_settings.docs_api_key = "prod-key"
                
                config = get_docs_access_config()
                
                assert config["require_auth"] is True
                assert config["api_key"] == "prod-key"
    
    def test_customize_openapi_responses(self):
        """Test custom OpenAPI response definitions."""
        responses = customize_openapi_responses()
        
        # Check that all standard HTTP error codes are included
        assert "400" in responses  # Validation Error
        assert "401" in responses  # Authentication Error
        assert "403" in responses  # Authorization Error
        assert "404" in responses  # Not Found Error
        assert "429" in responses  # Rate Limit Error
        assert "500" in responses  # Internal Server Error
        
        # Check response structure
        validation_error = responses["400"]
        assert "description" in validation_error
        assert "content" in validation_error
        assert "application/json" in validation_error["content"]


class TestOpenAPISchemaGeneration:
    """Test OpenAPI schema generation and customization."""
    
    def test_get_custom_openapi_schema(self):
        """Test custom OpenAPI schema generation."""
        # Create a test app
        app = create_app("testing")
        
        # Generate schema
        schema = get_custom_openapi_schema(app)
        
        # Check basic schema structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "components" in schema
        
        # Check custom security schemes
        security_schemes = schema["components"]["securitySchemes"]
        assert "BearerAuth" in security_schemes
        assert "ApiKeyAuth" in security_schemes
        assert "OAuth2" in security_schemes
        
        # Check Bearer auth configuration
        bearer_auth = security_schemes["BearerAuth"]
        assert bearer_auth["type"] == "http"
        assert bearer_auth["scheme"] == "bearer"
        assert bearer_auth["bearerFormat"] == "JWT"
        
        # Check API key configuration
        api_key_auth = security_schemes["ApiKeyAuth"]
        assert api_key_auth["type"] == "apiKey"
        assert api_key_auth["in"] == "header"
        assert api_key_auth["name"] == "X-API-Key"
        
        # Check OAuth2 configuration
        oauth2_auth = security_schemes["OAuth2"]
        assert oauth2_auth["type"] == "oauth2"
        assert "flows" in oauth2_auth
        assert "authorizationCode" in oauth2_auth["flows"]
        
        # Check custom examples
        examples = schema["components"]["examples"]
        assert "ValidationError" in examples
        assert "AuthenticationError" in examples
        assert "AuthorizationError" in examples
        assert "NotFoundError" in examples
        assert "RateLimitError" in examples
        assert "SuccessResponse" in examples
        
        # Check rate limiting information
        assert "x-rate-limiting" in schema
        rate_limiting = schema["x-rate-limiting"]
        assert "default" in rate_limiting
        assert "authenticated" in rate_limiting
    
    def test_openapi_schema_caching(self):
        """Test that OpenAPI schema is cached properly."""
        app = create_app("testing")
        
        # First call should generate schema
        schema1 = get_custom_openapi_schema(app)
        
        # Second call should return cached schema
        schema2 = get_custom_openapi_schema(app)
        
        # Should be the same object (cached)
        assert schema1 is schema2


class TestDocumentationRoutes:
    """Test documentation routes and access control."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app("testing")
        return TestClient(app)
    
    def test_swagger_ui_access_development(self, client):
        """Test Swagger UI access in development environment."""
        with patch('src.config.documentation.is_development', return_value=True):
            with patch('src.config.documentation.get_docs_access_config') as mock_config:
                mock_config.return_value = {"require_auth": False}
                
                response = client.get("/docs")
                assert response.status_code == 200
                assert "text/html" in response.headers["content-type"]
                assert "swagger-ui" in response.text.lower()
    
    def test_redoc_access_development(self, client):
        """Test ReDoc access in development environment."""
        with patch('src.config.documentation.is_development', return_value=True):
            with patch('src.config.documentation.get_docs_access_config') as mock_config:
                mock_config.return_value = {"require_auth": False}
                
                response = client.get("/redoc")
                assert response.status_code == 200
                assert "text/html" in response.headers["content-type"]
                assert "redoc" in response.text.lower()
    
    def test_openapi_json_access(self, client):
        """Test OpenAPI JSON schema access."""
        with patch('src.config.documentation.is_development', return_value=True):
            with patch('src.config.documentation.get_docs_access_config') as mock_config:
                mock_config.return_value = {"require_auth": False}
                
                response = client.get("/openapi.json")
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/json"
                
                schema = response.json()
                assert "openapi" in schema
                assert "info" in schema
                assert "paths" in schema
    
    def test_docs_access_basic(self, client):
        """Test basic documentation access (simplified test)."""
        # Test that docs endpoint is accessible in development/test mode
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_oauth2_redirect_endpoint(self, client):
        """Test OAuth2 redirect endpoint for Swagger UI."""
        response = client.get("/docs/oauth2-redirect")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "oauth2" in response.text.lower()
        assert "swaggerUIRedirectOauth2" in response.text
    
    def test_docs_info_endpoint(self, client):
        """Test documentation info endpoint."""
        with patch('src.config.documentation.is_development', return_value=True):
            with patch('src.config.documentation.get_docs_access_config') as mock_config:
                mock_config.return_value = {"require_auth": False}
                
                response = client.get("/docs/info")
                assert response.status_code == 200
                
                info = response.json()
                assert "title" in info
                assert "version" in info
                assert "docs_url" in info
                assert "supported_auth_methods" in info
                assert "features" in info
    
    def test_docs_health_endpoint(self, client):
        """Test documentation health endpoint."""
        response = client.get("/docs/health")
        assert response.status_code == 200
        
        health = response.json()
        assert health["status"] == "healthy"
        assert health["service"] == "api-documentation"
        assert "endpoints" in health
        assert "swagger_ui" in health["endpoints"]
        assert "redoc" in health["endpoints"]
        assert "openapi_schema" in health["endpoints"]


class TestDocumentationIntegration:
    """Test documentation integration with the main application."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app("testing")
        return TestClient(app)
    
    def test_api_root_includes_docs_links(self, client):
        """Test that API root includes documentation links."""
        response = client.get("/api/")
        assert response.status_code == 200
        
        data = response.json()
        assert "docs_url" in data
        assert "redoc_url" in data
        assert "openapi_url" in data
        assert data["docs_url"] == "/docs"
        assert data["redoc_url"] == "/redoc"
        assert data["openapi_url"] == "/openapi.json"
    
    def test_health_endpoints_have_detailed_docs(self, client):
        """Test that health endpoints have detailed documentation."""
        # Get OpenAPI schema
        with patch('src.config.documentation.is_development', return_value=True):
            with patch('src.config.documentation.get_docs_access_config') as mock_config:
                mock_config.return_value = {"require_auth": False}
                
                response = client.get("/openapi.json")
                assert response.status_code == 200
                
                schema = response.json()
                paths = schema["paths"]
                
                # Check health endpoint documentation
                assert "/healthz" in paths
                health_endpoint = paths["/healthz"]["get"]
                assert "summary" in health_endpoint
                assert "description" in health_endpoint
                assert len(health_endpoint["description"]) > 100  # Detailed description
                
                # Check readiness endpoint documentation
                assert "/readyz" in paths
                readiness_endpoint = paths["/readyz"]["get"]
                assert "summary" in readiness_endpoint
                assert "description" in readiness_endpoint
                assert len(readiness_endpoint["description"]) > 100  # Detailed description
    
    def test_api_endpoints_have_examples(self, client):
        """Test that API endpoints include response examples."""
        with patch('src.config.documentation.is_development', return_value=True):
            with patch('src.config.documentation.get_docs_access_config') as mock_config:
                mock_config.return_value = {"require_auth": False}
                
                response = client.get("/openapi.json")
                assert response.status_code == 200
                
                schema = response.json()
                
                # Check that custom examples are included
                examples = schema["components"]["examples"]
                
                # Verify example structure
                validation_error = examples["ValidationError"]
                assert "summary" in validation_error
                assert "description" in validation_error
                assert "value" in validation_error
                
                example_value = validation_error["value"]
                assert "success" in example_value
                assert "message" in example_value
                assert "error_code" in example_value
                assert "details" in example_value
                assert "correlation_id" in example_value
                assert "timestamp" in example_value


@pytest.mark.asyncio
class TestDocumentationAccessControl:
    """Test documentation access control functionality."""
    
    async def test_verify_docs_access_development_no_auth(self):
        """Test docs access verification in development without auth."""
        mock_request = MagicMock()
        
        with patch('src.config.documentation.is_development', return_value=True):
            with patch('src.config.documentation.get_docs_access_config') as mock_config:
                mock_config.return_value = {"require_auth": False}
                
                result = await verify_docs_access(mock_request, None)
                assert result is True
    
    async def test_verify_docs_access_with_api_key(self):
        """Test docs access verification with API key."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "valid-api-key"
        
        with patch('src.config.documentation.get_docs_access_config') as mock_config:
            mock_config.return_value = {
                "require_auth": True,
                "api_key": "valid-api-key",
                "api_key_header": "X-Docs-API-Key"
            }
            
            result = await verify_docs_access(mock_request, None)
            assert result is True
    
    async def test_verify_docs_access_with_bearer_token(self):
        """Test docs access verification with Bearer token."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        
        mock_credentials = MagicMock()
        mock_credentials.credentials = "valid-jwt-token-with-sufficient-length"
        
        with patch('src.config.documentation.get_docs_access_config') as mock_config:
            mock_config.return_value = {"require_auth": True, "api_key": None}
            
            result = await verify_docs_access(mock_request, mock_credentials)
            assert result is True
    
    async def test_verify_docs_access_denied(self):
        """Test docs access verification denial."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = ""
        
        with patch('src.config.documentation.get_docs_access_config') as mock_config:
            mock_config.return_value = {"require_auth": True, "api_key": None}
            
            with pytest.raises(Exception):  # Should raise HTTPException
                await verify_docs_access(mock_request, None)