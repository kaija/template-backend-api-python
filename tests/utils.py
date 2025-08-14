"""
Test utilities and helper functions.

This module provides utility functions and helpers for testing
the FastAPI application, including assertion helpers, data validation,
and common test operations.
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession


class APITestHelper:
    """
    Helper class for API testing with common assertion methods.
    
    This class provides utility methods for testing API endpoints
    with consistent assertions and error handling.
    """
    
    @staticmethod
    def assert_response_status(response: Response, expected_status: int) -> None:
        """
        Assert that response has expected status code.
        
        Args:
            response: HTTP response object
            expected_status: Expected status code
        """
        assert response.status_code == expected_status, (
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.text}"
        )
    
    @staticmethod
    def assert_response_json(response: Response) -> Dict[str, Any]:
        """
        Assert that response contains valid JSON and return it.
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON response data
        """
        try:
            return response.json()
        except json.JSONDecodeError as e:
            pytest.fail(f"Response is not valid JSON: {e}. Response: {response.text}")
    
    @staticmethod
    def assert_success_response(response: Response) -> Dict[str, Any]:
        """
        Assert that response is successful (2xx) and return JSON data.
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON response data
        """
        assert 200 <= response.status_code < 300, (
            f"Expected success status (2xx), got {response.status_code}. "
            f"Response: {response.text}"
        )
        return APITestHelper.assert_response_json(response)
    
    @staticmethod
    def assert_error_response(
        response: Response, 
        expected_status: int,
        expected_error_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assert that response is an error with expected format.
        
        Args:
            response: HTTP response object
            expected_status: Expected error status code
            expected_error_code: Expected error code in response
            
        Returns:
            Parsed JSON error response data
        """
        APITestHelper.assert_response_status(response, expected_status)
        data = APITestHelper.assert_response_json(response)
        
        # Assert error response structure
        assert "error" in data, f"Error response missing 'error' field: {data}"
        error = data["error"]
        
        assert "code" in error, f"Error missing 'code' field: {error}"
        assert "message" in error, f"Error missing 'message' field: {error}"
        
        if expected_error_code:
            assert error["code"] == expected_error_code, (
                f"Expected error code '{expected_error_code}', got '{error['code']}'"
            )
        
        return data
    
    @staticmethod
    def assert_validation_error(response: Response) -> Dict[str, Any]:
        """
        Assert that response is a validation error (400).
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON error response data
        """
        return APITestHelper.assert_error_response(
            response, 
            status.HTTP_400_BAD_REQUEST,
            "VALIDATION_ERROR"
        )
    
    @staticmethod
    def assert_authentication_error(response: Response) -> Dict[str, Any]:
        """
        Assert that response is an authentication error (401).
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON error response data
        """
        return APITestHelper.assert_error_response(
            response,
            status.HTTP_401_UNAUTHORIZED,
            "AUTHENTICATION_ERROR"
        )
    
    @staticmethod
    def assert_authorization_error(response: Response) -> Dict[str, Any]:
        """
        Assert that response is an authorization error (403).
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON error response data
        """
        return APITestHelper.assert_error_response(
            response,
            status.HTTP_403_FORBIDDEN,
            "AUTHORIZATION_ERROR"
        )
    
    @staticmethod
    def assert_not_found_error(response: Response) -> Dict[str, Any]:
        """
        Assert that response is a not found error (404).
        
        Args:
            response: HTTP response object
            
        Returns:
            Parsed JSON error response data
        """
        return APITestHelper.assert_error_response(
            response,
            status.HTTP_404_NOT_FOUND,
            "NOT_FOUND_ERROR"
        )
    
    @staticmethod
    def assert_response_headers(
        response: Response, 
        expected_headers: Dict[str, str]
    ) -> None:
        """
        Assert that response contains expected headers.
        
        Args:
            response: HTTP response object
            expected_headers: Dictionary of expected headers
        """
        for header_name, expected_value in expected_headers.items():
            assert header_name in response.headers, (
                f"Expected header '{header_name}' not found in response headers"
            )
            actual_value = response.headers[header_name]
            assert actual_value == expected_value, (
                f"Expected header '{header_name}' to be '{expected_value}', "
                f"got '{actual_value}'"
            )
    
    @staticmethod
    def assert_response_schema(
        response_data: Dict[str, Any],
        expected_fields: List[str],
        optional_fields: Optional[List[str]] = None
    ) -> None:
        """
        Assert that response data contains expected fields.
        
        Args:
            response_data: Response data dictionary
            expected_fields: List of required field names
            optional_fields: List of optional field names
        """
        optional_fields = optional_fields or []
        
        # Check required fields
        for field in expected_fields:
            assert field in response_data, (
                f"Required field '{field}' missing from response: {response_data}"
            )
        
        # Check for unexpected fields
        all_expected_fields = set(expected_fields + optional_fields)
        actual_fields = set(response_data.keys())
        unexpected_fields = actual_fields - all_expected_fields
        
        if unexpected_fields:
            pytest.fail(
                f"Unexpected fields in response: {unexpected_fields}. "
                f"Response: {response_data}"
            )


class DatabaseTestHelper:
    """
    Helper class for database testing operations.
    
    This class provides utility methods for database testing,
    including data creation, validation, and cleanup.
    """
    
    @staticmethod
    async def create_test_record(
        session: AsyncSession,
        model_class: Any,
        **kwargs
    ) -> Any:
        """
        Create a test record in the database.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            **kwargs: Field values for the record
            
        Returns:
            Created model instance
        """
        record = model_class(**kwargs)
        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record
    
    @staticmethod
    async def get_record_by_id(
        session: AsyncSession,
        model_class: Any,
        record_id: str
    ) -> Optional[Any]:
        """
        Get a record by ID from the database.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            record_id: Record ID to fetch
            
        Returns:
            Model instance or None if not found
        """
        return await session.get(model_class, record_id)
    
    @staticmethod
    async def count_records(
        session: AsyncSession,
        model_class: Any,
        **filters
    ) -> int:
        """
        Count records in the database with optional filters.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            **filters: Filter conditions
            
        Returns:
            Number of matching records
        """
        from sqlalchemy import select, func
        
        query = select(func.count(model_class.id))
        
        for field, value in filters.items():
            if hasattr(model_class, field):
                query = query.where(getattr(model_class, field) == value)
        
        result = await session.execute(query)
        return result.scalar()
    
    @staticmethod
    async def assert_record_exists(
        session: AsyncSession,
        model_class: Any,
        record_id: str
    ) -> Any:
        """
        Assert that a record exists in the database.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            record_id: Record ID to check
            
        Returns:
            Model instance if found
        """
        record = await DatabaseTestHelper.get_record_by_id(
            session, model_class, record_id
        )
        assert record is not None, (
            f"Expected {model_class.__name__} with ID {record_id} to exist"
        )
        return record
    
    @staticmethod
    async def assert_record_not_exists(
        session: AsyncSession,
        model_class: Any,
        record_id: str
    ) -> None:
        """
        Assert that a record does not exist in the database.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            record_id: Record ID to check
        """
        record = await DatabaseTestHelper.get_record_by_id(
            session, model_class, record_id
        )
        assert record is None, (
            f"Expected {model_class.__name__} with ID {record_id} to not exist"
        )
    
    @staticmethod
    async def assert_record_count(
        session: AsyncSession,
        model_class: Any,
        expected_count: int,
        **filters
    ) -> None:
        """
        Assert that the number of records matches expected count.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            expected_count: Expected number of records
            **filters: Filter conditions
        """
        actual_count = await DatabaseTestHelper.count_records(
            session, model_class, **filters
        )
        assert actual_count == expected_count, (
            f"Expected {expected_count} {model_class.__name__} records, "
            f"got {actual_count}"
        )


class AsyncTestHelper:
    """
    Helper class for async testing operations.
    
    This class provides utility methods for testing async functions
    and handling async test scenarios.
    """
    
    @staticmethod
    async def run_with_timeout(
        coro: Callable,
        timeout: float = 5.0,
        *args,
        **kwargs
    ) -> Any:
        """
        Run an async function with a timeout.
        
        Args:
            coro: Async function to run
            timeout: Timeout in seconds
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            asyncio.TimeoutError: If function times out
        """
        return await asyncio.wait_for(coro(*args, **kwargs), timeout=timeout)
    
    @staticmethod
    async def assert_async_raises(
        exception_class: type,
        coro: Callable,
        *args,
        **kwargs
    ) -> None:
        """
        Assert that an async function raises a specific exception.
        
        Args:
            exception_class: Expected exception class
            coro: Async function to test
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
        """
        with pytest.raises(exception_class):
            await coro(*args, **kwargs)
    
    @staticmethod
    async def collect_async_results(
        async_generators: List[Any],
        max_items: int = 100
    ) -> List[Any]:
        """
        Collect results from async generators.
        
        Args:
            async_generators: List of async generators
            max_items: Maximum items to collect per generator
            
        Returns:
            List of collected results
        """
        results = []
        
        for generator in async_generators:
            count = 0
            async for item in generator:
                results.append(item)
                count += 1
                if count >= max_items:
                    break
        
        return results


class MockHelper:
    """
    Helper class for creating and managing mocks in tests.
    
    This class provides utility methods for creating consistent
    mocks and managing mock behavior across tests.
    """
    
    @staticmethod
    def create_async_mock(return_value: Any = None) -> AsyncMock:
        """
        Create an async mock with optional return value.
        
        Args:
            return_value: Value to return from mock calls
            
        Returns:
            Configured AsyncMock instance
        """
        mock = AsyncMock()
        if return_value is not None:
            mock.return_value = return_value
        return mock
    
    @staticmethod
    def create_mock_response(
        status_code: int = 200,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> MagicMock:
        """
        Create a mock HTTP response.
        
        Args:
            status_code: HTTP status code
            json_data: JSON response data
            headers: Response headers
            
        Returns:
            Mock response object
        """
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data or {}
        mock_response.headers = headers or {}
        mock_response.text = json.dumps(json_data) if json_data else ""
        
        return mock_response
    
    @staticmethod
    def create_mock_database_session() -> AsyncMock:
        """
        Create a mock database session.
        
        Returns:
            Mock database session
        """
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.execute = AsyncMock()
        
        return mock_session


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


def assert_list_contains_items(
    actual_list: List[Any],
    expected_items: List[Any],
    key_func: Optional[Callable] = None
) -> None:
    """
    Assert that a list contains expected items.
    
    Args:
        actual_list: Actual list to check
        expected_items: Expected items that should be in the list
        key_func: Optional function to extract comparison key from items
    """
    if key_func:
        actual_keys = [key_func(item) for item in actual_list]
        expected_keys = [key_func(item) for item in expected_items]
        
        for expected_key in expected_keys:
            assert expected_key in actual_keys, (
                f"Expected item with key '{expected_key}' not found in list"
            )
    else:
        for expected_item in expected_items:
            assert expected_item in actual_list, (
                f"Expected item '{expected_item}' not found in list"
            )