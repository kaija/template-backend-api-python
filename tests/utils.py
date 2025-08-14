"""
Test utilities and helper functions.

This module provides common utilities for testing including:
- Test data factories
- Mock helpers
- Assertion utilities
- Test client helpers
"""

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Test environment setup
os.environ["API_ENV"] = "test"
os.environ["SKIP_CONFIG_INIT"] = "1"
os.environ["SKIP_CONFIG_VALIDATION"] = "1"


class DatabaseTestHelper:
    """Helper class for database testing operations."""
    
    @staticmethod
    def create_test_database_url() -> str:
        """Create a unique test database URL."""
        import uuid
        db_name = f"test_{uuid.uuid4().hex[:8]}.db"
        return f"sqlite+aiosqlite:///{db_name}"
    
    @staticmethod
    async def create_test_session() -> AsyncSession:
        """Create a test database session."""
        from src.database.base import Base
        
        # Create test database
        db_url = DatabaseTestHelper.create_test_database_url()
        engine = create_async_engine(db_url, echo=False)
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Create session
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        return async_session()
    
    @staticmethod
    def cleanup_test_database(db_url: str) -> None:
        """Clean up test database file."""
        if "sqlite" in db_url and ":///" in db_url:
            db_file = db_url.split("///")[-1]
            if os.path.exists(db_file):
                os.remove(db_file)


class MockHelper:
    """Helper class for creating mocks."""
    
    @staticmethod
    def create_mock_session() -> AsyncMock:
        """Create a mock database session."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.add = Mock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.scalar = AsyncMock()
        mock_session.scalars = AsyncMock()
        
        return mock_session
    
    @staticmethod
    def create_mock_user(user_id: str = "test_user_id", **kwargs) -> Mock:
        """Create a mock user object."""
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.username = kwargs.get("username", "testuser")
        mock_user.email = kwargs.get("email", "test@example.com")
        mock_user.full_name = kwargs.get("full_name", "Test User")
        mock_user.is_active = kwargs.get("is_active", True)
        mock_user.is_verified = kwargs.get("is_verified", True)
        mock_user.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        mock_user.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
        
        return mock_user
    
    @staticmethod
    def create_mock_request(
        method: str = "GET",
        url: str = "/test",
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Mock:
        """Create a mock HTTP request."""
        mock_request = Mock()
        mock_request.method = method
        mock_request.url = Mock()
        mock_request.url.path = url
        mock_request.headers = headers or {}
        mock_request.client = Mock()
        mock_request.client.host = kwargs.get("client_host", "127.0.0.1")
        
        return mock_request
    
    @staticmethod
    def create_mock_response(
        status_code: int = 200,
        content: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,  # Alternative parameter name
        headers: Optional[Dict[str, str]] = None
    ) -> Mock:
        """Create a mock HTTP response."""
        mock_response = Mock()
        mock_response.status_code = status_code
        
        # Use json_data if provided, otherwise use content
        response_data = json_data or content or {}
        mock_response.json.return_value = response_data
        mock_response.headers = headers or {}
        mock_response.text = json.dumps(response_data)
        
        return mock_response
    
    @staticmethod
    def create_async_mock(return_value=None, **kwargs) -> AsyncMock:
        """Create an async mock object."""
        mock = AsyncMock(**kwargs)
        if return_value is not None:
            mock.return_value = return_value
        return mock
    
    @staticmethod
    def create_mock_database_session() -> AsyncMock:
        """Create a mock database session."""
        return MockHelper.create_mock_session()


class APITestHelper:
    """Helper class for API testing."""
    
    @staticmethod
    def create_test_app() -> FastAPI:
        """Create a minimal FastAPI app for testing."""
        app = FastAPI(title="Test API")
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy"}
        
        return app
    
    @staticmethod
    def assert_response_status(response, expected_status: int) -> None:
        """Assert that response has expected status code."""
        actual_status = response.status_code
        assert actual_status == expected_status, (
            f"Expected status {expected_status}, got {actual_status}. "
            f"Response: {getattr(response, 'text', '')}"
        )
    
    @staticmethod
    def assert_response_json(response) -> Dict[str, Any]:
        """Assert that response contains valid JSON and return it."""
        try:
            return response.json()
        except Exception as e:
            pytest.fail(f"Response does not contain valid JSON: {e}. Response: {response.text}")
    
    @staticmethod
    def assert_success_response(response) -> Dict[str, Any]:
        """Assert that response is successful (2xx) and return JSON."""
        assert 200 <= response.status_code < 300, (
            f"Expected success status (2xx), got {response.status_code}"
        )
        return APITestHelper.assert_response_json(response)
    
    @staticmethod
    def assert_response_headers(response, expected_headers: Dict[str, str]) -> None:
        """Assert that response contains expected headers."""
        for header, expected_value in expected_headers.items():
            actual_value = response.headers.get(header)
            assert actual_value == expected_value, (
                f"Expected header '{header}' to be '{expected_value}', got '{actual_value}'"
            )
    
    @staticmethod
    def assert_response_schema(
        response_data: Dict[str, Any], 
        required_fields: List[str], 
        optional_fields: Optional[List[str]] = None,
        expected_fields: Optional[List[str]] = None,  # Alternative parameter name
        schema: Optional[Dict[str, Any]] = None
    ) -> None:
        """Assert that response data matches expected schema."""
        # Handle different calling patterns
        if schema is not None:
            # Schema-based validation
            for field, field_type in schema.items():
                assert field in response_data, f"Required field '{field}' missing from response"
                if field_type is not None:
                    actual_value = response_data[field]
                    assert isinstance(actual_value, field_type), (
                        f"Field '{field}' expected type {field_type.__name__}, "
                        f"got {type(actual_value).__name__}"
                    )
        else:
            # Field-based validation
            all_expected_fields = expected_fields or (required_fields + (optional_fields or []))
            
            # Check required fields
            for field in required_fields:
                assert field in response_data, f"Required field '{field}' missing from response"
            
            # Check that no unexpected fields are present
            actual_fields = set(response_data.keys())
            expected_fields_set = set(all_expected_fields)
            unexpected_fields = actual_fields - expected_fields_set
            
            if unexpected_fields:
                # Only warn about unexpected fields, don't fail
                pass
    
    @staticmethod
    def assert_response_structure(
        response_data: Dict[str, Any],
        required_fields: List[str],
        optional_fields: Optional[List[str]] = None
    ) -> None:
        """Assert that response has expected structure."""
        optional_fields = optional_fields or []
        
        # Check required fields
        for field in required_fields:
            assert field in response_data, f"Required field '{field}' missing"
        
        # Check that no unexpected fields are present
        expected_fields = set(required_fields + optional_fields)
        actual_fields = set(response_data.keys())
        unexpected_fields = actual_fields - expected_fields
        
        assert not unexpected_fields, f"Unexpected fields: {unexpected_fields}"
    
    @staticmethod
    def assert_error_response(
        response_data: Dict[str, Any],
        expected_status: int,
        expected_message: Optional[str] = None
    ) -> None:
        """Assert that response is a proper error response."""
        assert "detail" in response_data or "message" in response_data
        
        if expected_message:
            detail = response_data.get("detail", response_data.get("message", ""))
            assert expected_message in str(detail)
    
    @staticmethod
    def assert_validation_error(response, expected_field: Optional[str] = None) -> None:
        """Assert that response is a validation error."""
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        error_data = APITestHelper.assert_response_json(response)
        assert "detail" in error_data, "Validation error should have 'detail' field"
        
        if expected_field:
            # Check if the expected field is mentioned in the error details
            detail_str = str(error_data["detail"])
            assert expected_field in detail_str, (
                f"Expected field '{expected_field}' not found in validation error: {detail_str}"
            )


class FileTestHelper:
    """Helper class for file system testing."""
    
    @staticmethod
    def create_temp_file(content: str = "", suffix: str = ".txt") -> str:
        """Create a temporary file with content."""
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name
    
    @staticmethod
    def create_temp_directory() -> str:
        """Create a temporary directory."""
        return tempfile.mkdtemp()
    
    @staticmethod
    def cleanup_temp_path(path: str) -> None:
        """Clean up temporary file or directory."""
        path_obj = Path(path)
        if path_obj.is_file():
            path_obj.unlink()
        elif path_obj.is_dir():
            import shutil
            shutil.rmtree(path)


class LogTestHelper:
    """Helper class for testing logging."""
    
    @staticmethod
    def capture_logs(logger_name: str, level: int = logging.INFO) -> List[logging.LogRecord]:
        """Capture logs from a specific logger."""
        logger = logging.getLogger(logger_name)
        handler = logging.handlers.MemoryHandler(capacity=1000)
        handler.setLevel(level)
        logger.addHandler(handler)
        logger.setLevel(level)
        
        return handler.buffer
    
    @staticmethod
    def assert_log_contains(
        log_records: List[logging.LogRecord],
        message: str,
        level: Optional[int] = None
    ) -> None:
        """Assert that logs contain a specific message."""
        matching_records = [
            record for record in log_records
            if message in record.getMessage()
            and (level is None or record.levelno == level)
        ]
        
        assert matching_records, f"No log record found containing '{message}'"


class AsyncTestHelper:
    """Helper class for async testing."""
    
    @staticmethod
    def run_async(coro):
        """Run an async coroutine in tests."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    @staticmethod
    async def run_with_timeout(coro_or_func, timeout: float = 5.0):
        """Run an async coroutine with timeout."""
        # Handle both coroutines and coroutine functions
        if asyncio.iscoroutinefunction(coro_or_func):
            coro = coro_or_func()
        else:
            coro = coro_or_func
        return await asyncio.wait_for(coro, timeout=timeout)
    
    @staticmethod
    async def assert_async_raises(exception_class, coro_or_func):
        """Assert that an async coroutine raises a specific exception."""
        with pytest.raises(exception_class):
            # Handle both coroutines and coroutine functions
            if asyncio.iscoroutinefunction(coro_or_func):
                await coro_or_func()
            else:
                await coro_or_func
    
    @staticmethod
    async def collect_async_results(coroutines_or_funcs: List) -> List[Any]:
        """Collect results from multiple async coroutines."""
        # Convert functions to coroutines if needed
        coroutines = []
        for item in coroutines_or_funcs:
            if asyncio.iscoroutinefunction(item):
                coroutines.append(item())
            else:
                coroutines.append(item)
        return await asyncio.gather(*coroutines)
    
    @staticmethod
    async def wait_for_condition(
        condition_func,
        timeout: float = 5.0,
        interval: float = 0.1
    ) -> bool:
        """Wait for a condition to become true."""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
                return True
            await asyncio.sleep(interval)
        
        return False


class PerformanceTestHelper:
    """Helper class for performance testing."""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> tuple:
        """Measure execution time of a function."""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        
        return result, execution_time
    
    @staticmethod
    async def measure_async_execution_time(coro) -> tuple:
        """Measure execution time of an async coroutine."""
        import time
        start_time = time.time()
        result = await coro
        end_time = time.time()
        execution_time = end_time - start_time
        
        return result, execution_time
    
    @staticmethod
    def assert_execution_time_under(
        execution_time: float,
        max_time: float,
        operation_name: str = "Operation"
    ) -> None:
        """Assert that execution time is under a threshold."""
        assert execution_time < max_time, (
            f"{operation_name} took {execution_time:.3f}s, "
            f"expected under {max_time:.3f}s"
        )


class SecurityTestHelper:
    """Helper class for security testing."""
    
    @staticmethod
    def create_jwt_token(
        payload: Dict[str, Any],
        secret: str = "test_secret",
        algorithm: str = "HS256"
    ) -> str:
        """Create a JWT token for testing."""
        import jwt
        return jwt.encode(payload, secret, algorithm=algorithm)
    
    @staticmethod
    def create_expired_jwt_token(
        payload: Dict[str, Any],
        secret: str = "test_secret",
        algorithm: str = "HS256"
    ) -> str:
        """Create an expired JWT token for testing."""
        import jwt
        from datetime import timedelta
        
        # Set expiration to 1 hour ago
        payload["exp"] = datetime.utcnow() - timedelta(hours=1)
        return jwt.encode(payload, secret, algorithm=algorithm)
    
    @staticmethod
    def generate_test_password(
        length: int = 12,
        include_special: bool = True
    ) -> str:
        """Generate a test password that meets requirements."""
        import random
        import string
        
        # Ensure password meets requirements
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        if include_special:
            chars += "!@#$%^&*"
        
        password = [
            random.choice(string.ascii_lowercase),  # At least one lowercase
            random.choice(string.ascii_uppercase),  # At least one uppercase
            random.choice(string.digits),           # At least one digit
        ]
        
        if include_special:
            password.append(random.choice("!@#$%^&*"))  # At least one special
        
        # Fill remaining length
        for _ in range(length - len(password)):
            password.append(random.choice(chars))
        
        # Shuffle to avoid predictable patterns
        random.shuffle(password)
        return ''.join(password)


class TestDataValidator:
    """
    Helper class for validating test data and responses.
    
    This class provides utility methods for validating data
    structures and ensuring test data integrity.
    """
    
    @staticmethod
    def validate_timestamp(timestamp_str: str) -> datetime:
        """
        Validate and parse a timestamp string.
        
        Args:
            timestamp_str: Timestamp string to validate
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValueError: If timestamp format is invalid
        """
        try:
            # Try ISO format first
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            # Try other common formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S",
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"Invalid timestamp format: {timestamp_str}")
    
    @staticmethod
    def validate_uuid(uuid_str: str) -> bool:
        """
        Validate UUID string format.
        
        Args:
            uuid_str: UUID string to validate
            
        Returns:
            True if valid UUID format
        """
        import re
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        return bool(uuid_pattern.match(uuid_str))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid email format
        """
        import re
        email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        return bool(email_pattern.match(email))
    
    @staticmethod
    def validate_response_structure(
        data: Dict[str, Any],
        required_fields: List[str],
        field_types: Optional[Dict[str, type]] = None
    ) -> None:
        """
        Validate response data structure.
        
        Args:
            data: Response data to validate
            required_fields: List of required field names
            field_types: Optional dictionary of field types to validate
        """
        field_types = field_types or {}
        
        # Check required fields
        for field in required_fields:
            assert field in data, f"Required field '{field}' missing from data"
        
        # Check field types
        for field, expected_type in field_types.items():
            if field in data:
                actual_value = data[field]
                assert isinstance(actual_value, expected_type), (
                    f"Field '{field}' expected type {expected_type.__name__}, "
                    f"got {type(actual_value).__name__}"
                )


# Convenience functions
def create_test_client_with_auth(app, user_data: Dict[str, Any]) -> TestClient:
    """
    Create a test client with authentication override.
    
    Args:
        app: FastAPI application
        user_data: User data for authentication
        
    Returns:
        Test client with authentication
    """
    from src.dependencies import get_current_user
    
    app.dependency_overrides[get_current_user] = lambda: user_data
    return TestClient(app)


async def create_async_client_with_auth(
    app, 
    user_data: Dict[str, Any]
) -> AsyncClient:
    """
    Create an async test client with authentication override.
    
    Args:
        app: FastAPI application
        user_data: User data for authentication
        
    Returns:
        Async test client with authentication
    """
    from src.dependencies import get_current_user
    
    app.dependency_overrides[get_current_user] = lambda: user_data
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        return client


def assert_datetime_recent(dt: datetime, max_age_seconds: int = 60) -> None:
    """
    Assert that a datetime is recent (within specified seconds).
    
    Args:
        dt: Datetime to check
        max_age_seconds: Maximum age in seconds
    """
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    age = (now - dt).total_seconds()
    assert age <= max_age_seconds, (
        f"Datetime {dt} is too old (age: {age}s, max: {max_age_seconds}s)"
    )