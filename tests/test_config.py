"""
Test configuration and settings.

This module provides configuration settings and utilities
specifically for testing the application.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class TestConfig:
    """
    Configuration class for test settings.
    
    This class centralizes test configuration and provides
    easy access to test-specific settings.
    """
    
    # Database settings
    database_url: str = "sqlite+aiosqlite:///:memory:"
    database_echo: bool = False
    
    # Application settings
    debug: bool = False
    testing: bool = True
    log_level: str = "WARNING"
    
    # Security settings
    secret_key: str = "test-secret-key-not-for-production"
    jwt_secret_key: str = "test-jwt-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    
    # External service settings
    redis_url: str = "redis://localhost:6379/1"
    sentry_dsn: str = ""  # Disabled for tests
    
    # Test-specific settings
    test_timeout: float = 30.0
    test_db_isolation: bool = True
    test_parallel: bool = False
    
    # Coverage settings
    coverage_target: float = 80.0
    coverage_fail_under: float = 75.0
    
    @classmethod
    def from_env(cls) -> "TestConfig":
        """
        Create test configuration from environment variables.
        
        Returns:
            TestConfig instance with values from environment
        """
        return cls(
            database_url=os.getenv("TEST_DATABASE_URL", cls.database_url),
            database_echo=os.getenv("TEST_DATABASE_ECHO", "false").lower() == "true",
            debug=os.getenv("TEST_DEBUG", "false").lower() == "true",
            log_level=os.getenv("TEST_LOG_LEVEL", cls.log_level),
            secret_key=os.getenv("TEST_SECRET_KEY", cls.secret_key),
            jwt_secret_key=os.getenv("TEST_JWT_SECRET_KEY", cls.jwt_secret_key),
            jwt_algorithm=os.getenv("TEST_JWT_ALGORITHM", cls.jwt_algorithm),
            jwt_expire_minutes=int(os.getenv("TEST_JWT_EXPIRE_MINUTES", str(cls.jwt_expire_minutes))),
            redis_url=os.getenv("TEST_REDIS_URL", cls.redis_url),
            sentry_dsn=os.getenv("TEST_SENTRY_DSN", cls.sentry_dsn),
            test_timeout=float(os.getenv("TEST_TIMEOUT", str(cls.test_timeout))),
            test_db_isolation=os.getenv("TEST_DB_ISOLATION", "true").lower() == "true",
            test_parallel=os.getenv("TEST_PARALLEL", "false").lower() == "true",
            coverage_target=float(os.getenv("COVERAGE_TARGET", str(cls.coverage_target))),
            coverage_fail_under=float(os.getenv("COVERAGE_FAIL_UNDER", str(cls.coverage_fail_under))),
        )
    
    def to_env_dict(self) -> Dict[str, str]:
        """
        Convert configuration to environment variables dictionary.
        
        Returns:
            Dictionary of environment variables
        """
        return {
            "ENV": "testing",
            "DEBUG": str(self.debug).lower(),
            "LOG_LEVEL": self.log_level,
            "DATABASE_URL": self.database_url,
            "DATABASE_ECHO": str(self.database_echo).lower(),
            "SECRET_KEY": self.secret_key,
            "JWT_SECRET_KEY": self.jwt_secret_key,
            "JWT_ALGORITHM": self.jwt_algorithm,
            "JWT_EXPIRE_MINUTES": str(self.jwt_expire_minutes),
            "REDIS_URL": self.redis_url,
            "SENTRY_DSN": self.sentry_dsn,
        }


# Global test configuration instance
test_config = TestConfig.from_env()


class TestCategories:
    """
    Test category constants for organizing tests.
    
    These constants can be used with pytest markers to
    categorize and filter tests.
    """
    
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    SLOW = "slow"
    FAST = "fast"
    AUTH = "auth"
    DATABASE = "database"
    API = "api"
    SECURITY = "security"
    PERFORMANCE = "performance"


class TestData:
    """
    Common test data constants and utilities.
    
    This class provides commonly used test data that can be
    shared across multiple test files.
    """
    
    # User test data
    VALID_USER_DATA = {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePassword123!",
    }
    
    ADMIN_USER_DATA = {
        "username": "adminuser",
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "password": "AdminPassword123!",
        "roles": ["admin", "user"],
        "permissions": ["read", "write", "admin", "delete"],
    }
    
    INACTIVE_USER_DATA = {
        "username": "inactiveuser",
        "email": "inactive@example.com",
        "first_name": "Inactive",
        "last_name": "User",
        "password": "InactivePassword123!",
        "is_active": False,
        "is_verified": False,
    }
    
    # Post test data
    VALID_POST_DATA = {
        "title": "Test Post Title",
        "content": "This is test post content with enough text to be meaningful.",
        "is_published": False,
    }
    
    PUBLISHED_POST_DATA = {
        "title": "Published Test Post",
        "content": "This is a published test post content.",
        "is_published": True,
    }
    
    # Comment test data
    VALID_COMMENT_DATA = {
        "content": "This is a test comment with meaningful content.",
        "is_approved": True,
    }
    
    UNAPPROVED_COMMENT_DATA = {
        "content": "This is an unapproved test comment.",
        "is_approved": False,
    }
    
    # Invalid data for validation testing
    INVALID_EMAIL_DATA = {
        "username": "testuser",
        "email": "invalid-email",
        "first_name": "Test",
        "last_name": "User",
        "password": "SecurePassword123!",
    }
    
    INVALID_PASSWORD_DATA = {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "weak",  # Too weak
    }
    
    MISSING_REQUIRED_FIELDS = {
        "email": "test@example.com",
        # Missing username, first_name, last_name, password
    }
    
    # JWT token test data
    VALID_JWT_PAYLOAD = {
        "user_id": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": ["read"],
        "exp": 9999999999,  # Far future expiration
        "iat": 1000000000,  # Past issued time
    }
    
    EXPIRED_JWT_PAYLOAD = {
        "user_id": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": ["read"],
        "exp": 1000000000,  # Past expiration
        "iat": 999999999,   # Past issued time
    }
    
    # API response test data
    SUCCESS_RESPONSE_SCHEMA = {
        "required_fields": ["data", "message", "timestamp"],
        "optional_fields": ["meta", "links"],
    }
    
    ERROR_RESPONSE_SCHEMA = {
        "required_fields": ["error"],
        "optional_fields": [],
    }
    
    ERROR_DETAIL_SCHEMA = {
        "required_fields": ["code", "message"],
        "optional_fields": ["details", "trace_id"],
    }


class TestEndpoints:
    """
    API endpoint constants for testing.
    
    This class provides constants for API endpoints to ensure
    consistency across tests and easy maintenance.
    """
    
    # Base URLs
    API_V1_BASE = "/api/v1"
    
    # Health check endpoints
    HEALTH_CHECK = "/healthz"
    READINESS_CHECK = "/readyz"
    
    # Authentication endpoints
    AUTH_LOGIN = f"{API_V1_BASE}/auth/login"
    AUTH_LOGOUT = f"{API_V1_BASE}/auth/logout"
    AUTH_REFRESH = f"{API_V1_BASE}/auth/refresh"
    AUTH_REGISTER = f"{API_V1_BASE}/auth/register"
    
    # User endpoints
    USERS_BASE = f"{API_V1_BASE}/users"
    USER_DETAIL = f"{USERS_BASE}/{{user_id}}"
    USER_PROFILE = f"{API_V1_BASE}/profile"
    
    # Post endpoints
    POSTS_BASE = f"{API_V1_BASE}/posts"
    POST_DETAIL = f"{POSTS_BASE}/{{post_id}}"
    POST_COMMENTS = f"{POST_DETAIL}/comments"
    
    # Comment endpoints
    COMMENTS_BASE = f"{API_V1_BASE}/comments"
    COMMENT_DETAIL = f"{COMMENTS_BASE}/{{comment_id}}"
    
    # Admin endpoints
    ADMIN_BASE = f"{API_V1_BASE}/admin"
    ADMIN_USERS = f"{ADMIN_BASE}/users"
    ADMIN_POSTS = f"{ADMIN_BASE}/posts"
    ADMIN_COMMENTS = f"{ADMIN_BASE}/comments"
    
    # Metrics and monitoring
    METRICS = "/metrics"
    
    @classmethod
    def user_detail(cls, user_id: str) -> str:
        """Get user detail endpoint with ID."""
        return cls.USER_DETAIL.format(user_id=user_id)
    
    @classmethod
    def post_detail(cls, post_id: str) -> str:
        """Get post detail endpoint with ID."""
        return cls.POST_DETAIL.format(post_id=post_id)
    
    @classmethod
    def post_comments(cls, post_id: str) -> str:
        """Get post comments endpoint with ID."""
        return cls.POST_COMMENTS.format(post_id=post_id)
    
    @classmethod
    def comment_detail(cls, comment_id: str) -> str:
        """Get comment detail endpoint with ID."""
        return cls.COMMENT_DETAIL.format(comment_id=comment_id)


class TestHeaders:
    """
    HTTP header constants for testing.
    
    This class provides constants for HTTP headers used in tests.
    """
    
    CONTENT_TYPE_JSON = {"Content-Type": "application/json"}
    ACCEPT_JSON = {"Accept": "application/json"}
    
    # Authentication headers
    AUTHORIZATION_BEARER = "Bearer {token}"
    
    # Request tracking headers
    REQUEST_ID = "X-Request-ID"
    CORRELATION_ID = "X-Correlation-ID"
    
    # Security headers
    CSRF_TOKEN = "X-CSRF-Token"
    
    @classmethod
    def authorization_bearer(cls, token: str) -> Dict[str, str]:
        """Create authorization header with bearer token."""
        return {"Authorization": cls.AUTHORIZATION_BEARER.format(token=token)}
    
    @classmethod
    def with_request_id(cls, request_id: str) -> Dict[str, str]:
        """Create headers with request ID."""
        return {cls.REQUEST_ID: request_id}
    
    @classmethod
    def with_correlation_id(cls, correlation_id: str) -> Dict[str, str]:
        """Create headers with correlation ID."""
        return {cls.CORRELATION_ID: correlation_id}
    
    @classmethod
    def json_with_auth(cls, token: str) -> Dict[str, str]:
        """Create JSON headers with authentication."""
        headers = cls.CONTENT_TYPE_JSON.copy()
        headers.update(cls.authorization_bearer(token))
        return headers


class TestAssertions:
    """
    Common assertion helpers for tests.
    
    This class provides reusable assertion methods that can be
    used across different test files.
    """
    
    @staticmethod
    def assert_valid_uuid(value: str, field_name: str = "id") -> None:
        """Assert that a value is a valid UUID."""
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        assert uuid_pattern.match(value), f"Invalid UUID format for {field_name}: {value}"
    
    @staticmethod
    def assert_valid_timestamp(value: str, field_name: str = "timestamp") -> None:
        """Assert that a value is a valid ISO timestamp."""
        from datetime import datetime
        try:
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            assert False, f"Invalid timestamp format for {field_name}: {value}"
    
    @staticmethod
    def assert_valid_email(value: str, field_name: str = "email") -> None:
        """Assert that a value is a valid email address."""
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        assert email_pattern.match(value), f"Invalid email format for {field_name}: {value}"
    
    @staticmethod
    def assert_response_time(response_time: float, max_time: float = 1.0) -> None:
        """Assert that response time is within acceptable limits."""
        assert response_time <= max_time, (
            f"Response time {response_time}s exceeds maximum {max_time}s"
        )
    
    @staticmethod
    def assert_pagination_response(
        data: Dict[str, Any],
        expected_fields: Optional[list] = None
    ) -> None:
        """Assert that response contains valid pagination structure."""
        expected_fields = expected_fields or ["items", "total", "page", "size", "pages"]
        
        for field in expected_fields:
            assert field in data, f"Pagination response missing field: {field}"
        
        assert isinstance(data["items"], list), "Pagination items must be a list"
        assert isinstance(data["total"], int), "Pagination total must be an integer"
        assert isinstance(data["page"], int), "Pagination page must be an integer"
        assert isinstance(data["size"], int), "Pagination size must be an integer"
        assert isinstance(data["pages"], int), "Pagination pages must be an integer"
        
        assert data["total"] >= 0, "Pagination total must be non-negative"
        assert data["page"] >= 1, "Pagination page must be at least 1"
        assert data["size"] >= 1, "Pagination size must be at least 1"
        assert data["pages"] >= 0, "Pagination pages must be non-negative"


# Export commonly used items
__all__ = [
    "test_config",
    "TestConfig",
    "TestCategories",
    "TestData",
    "TestEndpoints",
    "TestHeaders",
    "TestAssertions",
]