"""
Documentation configuration for FastAPI.

This module provides configuration and utilities for API documentation
including access controls, customization, and authentication support.
"""

from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.openapi.utils import get_openapi

from src.config import settings, is_production, is_development


# Security scheme for documentation access
docs_security = HTTPBearer(auto_error=False)


def get_docs_access_config() -> Dict[str, Any]:
    """
    Get documentation access configuration.

    Returns:
        Dictionary with documentation access settings
    """
    return {
        "require_auth": getattr(settings, "docs_require_auth", is_production()),
        "allowed_users": getattr(settings, "docs_allowed_users", []),
        "allowed_roles": getattr(settings, "docs_allowed_roles", ["admin", "developer"]),
        "api_key_header": getattr(settings, "docs_api_key_header", "X-Docs-API-Key"),
        "api_key": getattr(settings, "docs_api_key", None),
        "basic_auth_users": getattr(settings, "docs_basic_auth_users", {}),
        "enabled_in_production": getattr(settings, "docs_enabled_in_production", False),
        "rate_limit_enabled": getattr(settings, "docs_rate_limit_enabled", True),
        "rate_limit_requests": getattr(settings, "docs_rate_limit_requests", 30),
        "rate_limit_window": getattr(settings, "docs_rate_limit_window", 60),
    }


async def verify_docs_access(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(docs_security)
) -> bool:
    """
    Verify access to API documentation.

    Args:
        request: FastAPI request object
        credentials: HTTP authorization credentials

    Returns:
        True if access is granted

    Raises:
        HTTPException: If access is denied
    """
    config = get_docs_access_config()

    # Allow unrestricted access in development
    if is_development():
        return True

    # Check API key in header
    api_key_header = config.get("api_key_header", "X-Docs-API-Key")
    api_key = request.headers.get(api_key_header)
    if api_key and config.get("api_key") and api_key == config["api_key"]:
        return True

    # Check Bearer token
    if credentials:
        # In a real implementation, you would validate the JWT token here
        # For now, we'll just check if it's a valid format
        token = credentials.credentials
        if token and len(token) > 10:  # Basic validation
            # TODO: Implement proper JWT validation
            return True

    # Check basic auth (if implemented)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Basic "):
        # TODO: Implement basic auth validation
        pass

    # If we reach here and auth is required, deny access
    if config["require_auth"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access API documentation",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


def get_custom_openapi_schema(app) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation.

    Args:
        app: FastAPI application instance

    Returns:
        Custom OpenAPI schema dictionary
    """
    if app.openapi_schema:
        return app.openapi_schema

    # Get base OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=getattr(app, 'servers', None),
        tags=getattr(app, 'tags', None),
        terms_of_service=getattr(app, 'terms_of_service', None),
        contact=getattr(app, 'contact', None),
        license_info=getattr(app, 'license_info', None),
    )

    # Ensure components section exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    # Add comprehensive security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token authentication. Obtain a token from the `/api/v1/auth/login` endpoint.",
            "x-tokenUrl": "/api/v1/auth/login",
            "x-refreshUrl": "/api/v1/auth/refresh"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key authentication for service-to-service communication. Contact support to obtain an API key.",
            "x-keyFormat": "api_key_[a-zA-Z0-9]{32}"
        },
        "OAuth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "/api/v1/auth/oauth2/authorize",
                    "tokenUrl": "/api/v1/auth/oauth2/token",
                    "refreshUrl": "/api/v1/auth/oauth2/refresh",
                    "scopes": {
                        "read": "Read access to resources",
                        "write": "Write access to resources",
                        "admin": "Administrative access",
                        "user:profile": "Access to user profile information",
                        "user:email": "Access to user email address"
                    }
                },
                "clientCredentials": {
                    "tokenUrl": "/api/v1/auth/oauth2/token",
                    "scopes": {
                        "read": "Read access to resources",
                        "write": "Write access to resources"
                    }
                }
            },
            "description": "OAuth2 authentication with authorization code flow for user authentication and client credentials for service-to-service communication."
        }
    }

    # Add comprehensive response schemas
    _add_response_schemas(openapi_schema)

    # Add custom extensions for enhanced documentation
    openapi_schema["x-logo"] = {
        "url": "https://example.com/logo.png",
        "altText": "Production API Framework Logo"
    }

    # Add comprehensive API information
    openapi_schema["info"]["x-api-id"] = "generic-api-framework"
    openapi_schema["info"]["x-audience"] = "developers"
    openapi_schema["info"]["x-maturity"] = "stable"
    openapi_schema["info"]["x-category"] = "backend-api"

    # Add comprehensive response examples
    _add_custom_response_examples(openapi_schema)

    # Add rate limiting information
    _add_rate_limiting_info(openapi_schema)

    # Add authentication examples
    _add_authentication_examples(openapi_schema)

    # Add comprehensive error handling documentation
    _add_error_handling_docs(openapi_schema)

    # Add API usage guidelines
    _add_api_usage_guidelines(openapi_schema)

    # Cache the schema
    app.openapi_schema = openapi_schema
    return openapi_schema


def _add_custom_response_examples(openapi_schema: Dict[str, Any]) -> None:
    """
    Add custom response examples to the OpenAPI schema.

    Args:
        openapi_schema: OpenAPI schema dictionary to modify
    """
    # Add common error response examples
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    if "examples" not in openapi_schema["components"]:
        openapi_schema["components"]["examples"] = {}

    openapi_schema["components"]["examples"].update({
        "ValidationError": {
            "summary": "Validation Error Example",
            "description": "Example of a validation error response",
            "value": {
                "success": False,
                "message": "Validation failed",
                "error_code": "VALIDATION_ERROR",
                "details": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "INVALID_EMAIL"
                    }
                ],
                "correlation_id": "abc123-def456-ghi789",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        },
        "AuthenticationError": {
            "summary": "Authentication Error Example",
            "description": "Example of an authentication error response",
            "value": {
                "success": False,
                "message": "Authentication failed",
                "error_code": "AUTHENTICATION_ERROR",
                "details": [
                    {
                        "message": "Invalid or expired token",
                        "code": "INVALID_TOKEN"
                    }
                ],
                "correlation_id": "abc123-def456-ghi789",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        },
        "AuthorizationError": {
            "summary": "Authorization Error Example",
            "description": "Example of an authorization error response",
            "value": {
                "success": False,
                "message": "Insufficient permissions",
                "error_code": "AUTHORIZATION_ERROR",
                "details": [
                    {
                        "message": "User does not have required role",
                        "code": "INSUFFICIENT_PERMISSIONS"
                    }
                ],
                "correlation_id": "abc123-def456-ghi789",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        },
        "NotFoundError": {
            "summary": "Not Found Error Example",
            "description": "Example of a resource not found error response",
            "value": {
                "success": False,
                "message": "Resource not found",
                "error_code": "NOT_FOUND",
                "details": [
                    {
                        "message": "User with ID 'user_123' not found",
                        "code": "RESOURCE_NOT_FOUND"
                    }
                ],
                "correlation_id": "abc123-def456-ghi789",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        },
        "RateLimitError": {
            "summary": "Rate Limit Error Example",
            "description": "Example of a rate limit exceeded error response",
            "value": {
                "success": False,
                "message": "Rate limit exceeded",
                "error_code": "RATE_LIMIT_EXCEEDED",
                "details": [
                    {
                        "message": "Too many requests. Try again in 60 seconds.",
                        "code": "TOO_MANY_REQUESTS"
                    }
                ],
                "correlation_id": "abc123-def456-ghi789",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        },
        "SuccessResponse": {
            "summary": "Success Response Example",
            "description": "Example of a successful operation response",
            "value": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {
                    "id": "resource_123",
                    "status": "created"
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    })


def _add_response_schemas(openapi_schema: Dict[str, Any]) -> None:
    """
    Add comprehensive response schemas to the OpenAPI schema.

    Args:
        openapi_schema: OpenAPI schema dictionary to modify
    """
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}

    # Add standard response schemas
    openapi_schema["components"]["schemas"].update({
        "ErrorResponse": {
            "type": "object",
            "required": ["success", "message", "timestamp"],
            "properties": {
                "success": {
                    "type": "boolean",
                    "example": False,
                    "description": "Indicates if the request was successful"
                },
                "message": {
                    "type": "string",
                    "example": "Validation failed",
                    "description": "Human-readable error message"
                },
                "error_code": {
                    "type": "string",
                    "example": "VALIDATION_ERROR",
                    "description": "Error code for programmatic handling"
                },
                "details": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/ErrorDetail"},
                    "description": "Detailed error information"
                },
                "correlation_id": {
                    "type": "string",
                    "example": "abc123-def456-ghi789",
                    "description": "Request correlation ID for tracking"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-15T10:30:00Z",
                    "description": "Timestamp of the error"
                }
            }
        },
        "ErrorDetail": {
            "type": "object",
            "required": ["message"],
            "properties": {
                "field": {
                    "type": "string",
                    "example": "email",
                    "description": "Field name that caused the error (for validation errors)"
                },
                "message": {
                    "type": "string",
                    "example": "This field is required",
                    "description": "Error message"
                },
                "code": {
                    "type": "string",
                    "example": "FIELD_REQUIRED",
                    "description": "Error code for programmatic handling"
                }
            }
        },
        "SuccessResponse": {
            "type": "object",
            "required": ["success", "message", "timestamp"],
            "properties": {
                "success": {
                    "type": "boolean",
                    "example": True,
                    "description": "Indicates if the request was successful"
                },
                "message": {
                    "type": "string",
                    "example": "Operation completed successfully",
                    "description": "Human-readable success message"
                },
                "data": {
                    "type": "object",
                    "description": "Response data (optional)"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-15T10:30:00Z",
                    "description": "Timestamp of the response"
                }
            }
        },
        "PaginationMeta": {
            "type": "object",
            "required": ["total", "skip", "limit", "page", "pages", "has_next", "has_prev"],
            "properties": {
                "total": {
                    "type": "integer",
                    "minimum": 0,
                    "example": 100,
                    "description": "Total number of items available"
                },
                "skip": {
                    "type": "integer",
                    "minimum": 0,
                    "example": 0,
                    "description": "Number of items skipped"
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "example": 10,
                    "description": "Maximum number of items per page"
                },
                "page": {
                    "type": "integer",
                    "minimum": 1,
                    "example": 1,
                    "description": "Current page number"
                },
                "pages": {
                    "type": "integer",
                    "minimum": 1,
                    "example": 10,
                    "description": "Total number of pages"
                },
                "has_next": {
                    "type": "boolean",
                    "example": True,
                    "description": "Whether there are more items available"
                },
                "has_prev": {
                    "type": "boolean",
                    "example": False,
                    "description": "Whether there are previous items available"
                }
            }
        }
    })


def _add_rate_limiting_info(openapi_schema: Dict[str, Any]) -> None:
    """
    Add comprehensive rate limiting information to the OpenAPI schema.

    Args:
        openapi_schema: OpenAPI schema dictionary to modify
    """
    # Add rate limiting extension
    openapi_schema["x-rate-limiting"] = {
        "description": "API rate limiting is enforced to ensure fair usage and system stability",
        "default": {
            "requests": getattr(settings, "rate_limit_requests", 100),
            "window": getattr(settings, "rate_limit_window", 60),
            "unit": "minute",
            "description": "Default rate limit for unauthenticated requests"
        },
        "authenticated": {
            "requests": getattr(settings, "rate_limit_requests_authenticated", 1000),
            "window": getattr(settings, "rate_limit_window", 60),
            "unit": "minute",
            "description": "Higher rate limit for authenticated requests"
        },
        "headers": {
            "limit": "X-RateLimit-Limit",
            "remaining": "X-RateLimit-Remaining",
            "reset": "X-RateLimit-Reset",
            "retry_after": "Retry-After"
        },
        "error_response": {
            "status_code": 429,
            "error_code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later."
        }
    }


def _add_authentication_examples(openapi_schema: Dict[str, Any]) -> None:
    """
    Add authentication examples to the OpenAPI schema.

    Args:
        openapi_schema: OpenAPI schema dictionary to modify
    """
    if "examples" not in openapi_schema["components"]:
        openapi_schema["components"]["examples"] = {}

    openapi_schema["components"]["examples"].update({
        "BearerTokenExample": {
            "summary": "Bearer Token Authentication",
            "description": "Example of using JWT Bearer token for authentication",
            "value": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        },
        "ApiKeyExample": {
            "summary": "API Key Authentication",
            "description": "Example of using API key for service-to-service authentication",
            "value": {
                "X-API-Key": "api_key_1234567890abcdef1234567890abcdef"
            }
        },
        "LoginRequest": {
            "summary": "Login Request Example",
            "description": "Example login request to obtain JWT token",
            "value": {
                "email": "user@example.com",
                "password": "secure_password123"
            }
        },
        "LoginResponse": {
            "summary": "Login Response Example",
            "description": "Example successful login response with JWT tokens",
            "value": {
                "success": True,
                "message": "Login successful",
                "data": {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "user": {
                        "id": "user_123",
                        "email": "user@example.com",
                        "roles": ["user"]
                    }
                },
                "timestamp": "2024-01-15T10:30:00Z"
            }
        }
    })


def _add_error_handling_docs(openapi_schema: Dict[str, Any]) -> None:
    """
    Add comprehensive error handling documentation to the OpenAPI schema.

    Args:
        openapi_schema: OpenAPI schema dictionary to modify
    """
    openapi_schema["x-error-handling"] = {
        "description": "Comprehensive error handling with consistent response format",
        "error_codes": {
            "VALIDATION_ERROR": {
                "status_code": 400,
                "description": "Request validation failed",
                "example": {
                    "success": False,
                    "message": "Validation failed",
                    "error_code": "VALIDATION_ERROR",
                    "details": [
                        {
                            "field": "email",
                            "message": "Invalid email format",
                            "code": "INVALID_EMAIL"
                        }
                    ]
                }
            },
            "AUTHENTICATION_ERROR": {
                "status_code": 401,
                "description": "Authentication failed or missing",
                "example": {
                    "success": False,
                    "message": "Authentication failed",
                    "error_code": "AUTHENTICATION_ERROR",
                    "details": [
                        {
                            "message": "Invalid or expired token",
                            "code": "INVALID_TOKEN"
                        }
                    ]
                }
            },
            "AUTHORIZATION_ERROR": {
                "status_code": 403,
                "description": "Insufficient permissions",
                "example": {
                    "success": False,
                    "message": "Insufficient permissions",
                    "error_code": "AUTHORIZATION_ERROR",
                    "details": [
                        {
                            "message": "User does not have required role",
                            "code": "INSUFFICIENT_PERMISSIONS"
                        }
                    ]
                }
            },
            "NOT_FOUND": {
                "status_code": 404,
                "description": "Resource not found",
                "example": {
                    "success": False,
                    "message": "Resource not found",
                    "error_code": "NOT_FOUND",
                    "details": [
                        {
                            "message": "User with ID 'user_123' not found",
                            "code": "RESOURCE_NOT_FOUND"
                        }
                    ]
                }
            },
            "RATE_LIMIT_EXCEEDED": {
                "status_code": 429,
                "description": "Rate limit exceeded",
                "example": {
                    "success": False,
                    "message": "Rate limit exceeded",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "details": [
                        {
                            "message": "Too many requests. Try again in 60 seconds.",
                            "code": "TOO_MANY_REQUESTS"
                        }
                    ]
                }
            },
            "INTERNAL_SERVER_ERROR": {
                "status_code": 500,
                "description": "Internal server error",
                "example": {
                    "success": False,
                    "message": "Internal server error",
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "details": [
                        {
                            "message": "An unexpected error occurred",
                            "code": "UNEXPECTED_ERROR"
                        }
                    ]
                }
            }
        },
        "correlation_id": {
            "description": "Every response includes a correlation ID for request tracking",
            "header": "X-Correlation-ID",
            "format": "uuid4"
        }
    }


def _add_api_usage_guidelines(openapi_schema: Dict[str, Any]) -> None:
    """
    Add API usage guidelines to the OpenAPI schema.

    Args:
        openapi_schema: OpenAPI schema dictionary to modify
    """
    openapi_schema["x-api-guidelines"] = {
        "versioning": {
            "strategy": "URL path versioning",
            "current_version": "v1",
            "format": "/api/{version}/",
            "deprecation_policy": "Versions are supported for 12 months after deprecation announcement"
        },
        "pagination": {
            "default_limit": 10,
            "max_limit": 100,
            "parameters": {
                "skip": "Number of items to skip (offset)",
                "limit": "Maximum number of items to return (1-100)"
            },
            "response_format": "Items are returned in 'items' array with 'pagination' metadata"
        },
        "filtering": {
            "query_parameters": "Use query parameters for filtering (e.g., ?status=active)",
            "date_format": "ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)",
            "search": "Use 'q' parameter for text search"
        },
        "sorting": {
            "parameter": "sort_by",
            "order_parameter": "sort_order",
            "values": ["asc", "desc"],
            "example": "?sort_by=created_at&sort_order=desc"
        },
        "best_practices": [
            "Always include proper error handling in your client code",
            "Use appropriate HTTP methods (GET for reading, POST for creating, etc.)",
            "Include correlation IDs in logs for request tracking",
            "Implement exponential backoff for rate limit handling",
            "Cache responses when appropriate to reduce API calls",
            "Use HTTPS in production environments",
            "Validate input data before sending requests"
        ]
    }


def get_swagger_ui_oauth2_redirect_url() -> Optional[str]:
    """
    Get OAuth2 redirect URL for Swagger UI.

    Returns:
        OAuth2 redirect URL or None if not configured
    """
    if is_production():
        return getattr(settings, "swagger_oauth2_redirect_url", None)
    return "/docs/oauth2-redirect"


def get_swagger_ui_init_oauth() -> Optional[Dict[str, Any]]:
    """
    Get OAuth2 initialization parameters for Swagger UI.

    Returns:
        OAuth2 initialization parameters or None if not configured
    """
    if not getattr(settings, "swagger_oauth2_enabled", False):
        return None

    return {
        "clientId": getattr(settings, "swagger_oauth2_client_id", "swagger-ui"),
        "clientSecret": getattr(settings, "swagger_oauth2_client_secret", ""),
        "realm": getattr(settings, "swagger_oauth2_realm", "swagger-ui-realm"),
        "appName": getattr(settings, "app_name", "Production API Framework"),
        "scopeSeparator": " ",
        "scopes": "read write admin",
        "additionalQueryStringParams": {},
        "useBasicAuthenticationWithAccessCodeGrant": False,
        "usePkceWithAuthorizationCodeGrant": True
    }


def customize_openapi_responses() -> Dict[str, Any]:
    """
    Get custom OpenAPI response definitions.

    Returns:
        Dictionary of custom response definitions
    """
    return {
        "400": {
            "description": "Validation Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "examples": {
                        "validation_error": {"$ref": "#/components/examples/ValidationError"}
                    }
                }
            }
        },
        "401": {
            "description": "Authentication Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "examples": {
                        "auth_error": {"$ref": "#/components/examples/AuthenticationError"}
                    }
                }
            }
        },
        "403": {
            "description": "Authorization Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "examples": {
                        "authz_error": {"$ref": "#/components/examples/AuthorizationError"}
                    }
                }
            }
        },
        "404": {
            "description": "Not Found Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "examples": {
                        "not_found": {"$ref": "#/components/examples/NotFoundError"}
                    }
                }
            }
        },
        "429": {
            "description": "Rate Limit Exceeded",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"},
                    "examples": {
                        "rate_limit": {"$ref": "#/components/examples/RateLimitError"}
                    }
                }
            }
        },
        "500": {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            }
        }
    }
