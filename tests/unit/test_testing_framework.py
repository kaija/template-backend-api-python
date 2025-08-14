"""
Unit tests for the testing framework itself.

This module tests the testing framework components to ensure
they work correctly and provide a good example of how to use
the testing utilities.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import AsyncTestCase
from tests.factories import (
    UserFactory, AdminUserFactory, PostFactory, 
    UserCreateRequestFactory
)
from tests.utils import (
    APITestHelper, DatabaseTestHelper, AsyncTestHelper,
    MockHelper, TestDataValidator
)
from tests.test_config import TestData, TestEndpoints, TestHeaders, TestAssertions


class TestFactories:
    """Test the factory classes for creating test data."""
    
    def test_user_factory_creates_valid_user(self):
        """Test that UserFactory creates a valid user object."""
        user = UserFactory()
        
        assert user.id is not None
        assert user.username is not None
        assert user.email is not None
        assert user.first_name is not None
        assert user.last_name is not None
        assert user.is_active is True
        assert user.is_verified is True
        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.roles, list)
        assert isinstance(user.permissions, list)
    
    def test_admin_user_factory_creates_admin_user(self):
        """Test that AdminUserFactory creates a user with admin privileges."""
        admin = AdminUserFactory()
        
        assert 'admin' in admin.roles
        assert 'user' in admin.roles
        assert 'admin' in admin.permissions
        assert 'delete' in admin.permissions
    
    def test_post_factory_creates_valid_post(self):
        """Test that PostFactory creates a valid post object."""
        post = PostFactory()
        
        assert post.id is not None
        assert post.title is not None
        assert post.content is not None
        assert post.author_id is not None
        assert post.is_published is False  # Default value
        assert post.created_at is not None
        assert post.updated_at is not None
    
    def test_user_create_request_factory(self):
        """Test that UserCreateRequestFactory creates valid request data."""
        request_data = UserCreateRequestFactory()
        
        assert 'username' in request_data
        assert 'email' in request_data
        assert 'first_name' in request_data
        assert 'last_name' in request_data
        assert 'password' in request_data
        assert 'request_id' in request_data
        assert 'timestamp' in request_data
    
    def test_factory_sequence_generates_unique_values(self):
        """Test that factory sequences generate unique values."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        assert user1.username != user2.username
        assert user1.email != user2.email
        assert user1.id != user2.id
    
    def test_factory_with_custom_attributes(self):
        """Test that factories accept custom attributes."""
        custom_username = "custom_user"
        user = UserFactory(username=custom_username)
        
        assert user.username == custom_username
        assert custom_username in user.email  # Email is derived from username


class TestAPITestHelper:
    """Test the API testing helper utilities."""
    
    def test_assert_response_status_success(self):
        """Test successful status assertion."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        # Should not raise
        APITestHelper.assert_response_status(mock_response, 200)
    
    def test_assert_response_status_failure(self):
        """Test failed status assertion."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        with pytest.raises(AssertionError) as exc_info:
            APITestHelper.assert_response_status(mock_response, 200)
        
        assert "Expected status 200, got 404" in str(exc_info.value)
    
    def test_assert_response_json_valid(self):
        """Test JSON response assertion with valid JSON."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        
        result = APITestHelper.assert_response_json(mock_response)
        assert result == {"key": "value"}
    
    def test_assert_response_json_invalid(self):
        """Test JSON response assertion with invalid JSON."""
        import json
        
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.text = "Invalid JSON"
        
        with pytest.raises(pytest.fail.Exception):
            APITestHelper.assert_response_json(mock_response)
    
    def test_assert_success_response(self):
        """Test successful response assertion."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "123"}
        
        result = APITestHelper.assert_success_response(mock_response)
        assert result == {"id": "123"}
    
    def test_assert_error_response(self):
        """Test error response assertion."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input"
            }
        }
        
        result = APITestHelper.assert_error_response(
            mock_response, 400, "VALIDATION_ERROR"
        )
        assert result["error"]["code"] == "VALIDATION_ERROR"
    
    def test_assert_response_headers(self):
        """Test response headers assertion."""
        mock_response = MagicMock()
        mock_response.headers = {
            "Content-Type": "application/json",
            "X-Request-ID": "123"
        }
        
        expected_headers = {
            "Content-Type": "application/json",
            "X-Request-ID": "123"
        }
        
        # Should not raise
        APITestHelper.assert_response_headers(mock_response, expected_headers)
    
    def test_assert_response_schema(self):
        """Test response schema assertion."""
        response_data = {
            "id": "123",
            "name": "Test",
            "email": "test@example.com",
            "optional_field": "value"
        }
        
        required_fields = ["id", "name", "email"]
        optional_fields = ["optional_field"]
        
        # Should not raise
        APITestHelper.assert_response_schema(
            response_data, required_fields, optional_fields
        )


class TestAsyncTestHelper:
    """Test the async testing helper utilities."""
    
    @pytest.mark.asyncio
    async def test_run_with_timeout_success(self):
        """Test running async function with timeout - success case."""
        async def quick_function():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await AsyncTestHelper.run_with_timeout(quick_function, timeout=1.0)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_run_with_timeout_failure(self):
        """Test running async function with timeout - timeout case."""
        async def slow_function():
            await asyncio.sleep(2.0)
            return "success"
        
        with pytest.raises(asyncio.TimeoutError):
            await AsyncTestHelper.run_with_timeout(slow_function, timeout=0.5)
    
    @pytest.mark.asyncio
    async def test_assert_async_raises(self):
        """Test async exception assertion."""
        async def failing_function():
            raise ValueError("Test error")
        
        # Should not raise AssertionError
        await AsyncTestHelper.assert_async_raises(ValueError, failing_function)
    
    @pytest.mark.asyncio
    async def test_collect_async_results(self):
        """Test collecting results from async generators."""
        async def async_generator():
            for i in range(5):
                yield i
        
        results = await AsyncTestHelper.collect_async_results([async_generator()])
        assert results == [0, 1, 2, 3, 4]


class TestMockHelper:
    """Test the mock helper utilities."""
    
    def test_create_async_mock(self):
        """Test creating async mock."""
        mock = MockHelper.create_async_mock("test_return")
        
        assert isinstance(mock, AsyncMock)
        assert mock.return_value == "test_return"
    
    def test_create_mock_response(self):
        """Test creating mock HTTP response."""
        json_data = {"key": "value"}
        headers = {"Content-Type": "application/json"}
        
        mock_response = MockHelper.create_mock_response(
            status_code=200,
            json_data=json_data,
            headers=headers
        )
        
        assert mock_response.status_code == 200
        assert mock_response.json() == json_data
        assert mock_response.headers == headers
    
    def test_create_mock_database_session(self):
        """Test creating mock database session."""
        mock_session = MockHelper.create_mock_database_session()
        
        assert isinstance(mock_session, AsyncMock)
        assert hasattr(mock_session, 'add')
        assert hasattr(mock_session, 'commit')
        assert hasattr(mock_session, 'rollback')
        assert hasattr(mock_session, 'close')


class TestDataValidator:
    """Test the data validation utilities."""
    
    def test_validate_timestamp_iso_format(self):
        """Test timestamp validation with ISO format."""
        timestamp_str = "2024-01-01T12:00:00Z"
        result = TestDataValidator.validate_timestamp(timestamp_str)
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1
    
    def test_validate_timestamp_invalid_format(self):
        """Test timestamp validation with invalid format."""
        with pytest.raises(ValueError):
            TestDataValidator.validate_timestamp("invalid-timestamp")
    
    def test_validate_uuid_valid(self):
        """Test UUID validation with valid UUID."""
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        assert TestDataValidator.validate_uuid(valid_uuid) is True
    
    def test_validate_uuid_invalid(self):
        """Test UUID validation with invalid UUID."""
        invalid_uuid = "not-a-uuid"
        assert TestDataValidator.validate_uuid(invalid_uuid) is False
    
    def test_validate_email_valid(self):
        """Test email validation with valid email."""
        valid_email = "test@example.com"
        assert TestDataValidator.validate_email(valid_email) is True
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid email."""
        invalid_email = "not-an-email"
        assert TestDataValidator.validate_email(invalid_email) is False
    
    def test_validate_response_structure_valid(self):
        """Test response structure validation with valid data."""
        data = {
            "id": "123",
            "name": "Test",
            "email": "test@example.com"
        }
        required_fields = ["id", "name", "email"]
        field_types = {"id": str, "name": str, "email": str}
        
        # Should not raise
        TestDataValidator.validate_response_structure(
            data, required_fields, field_types
        )
    
    def test_validate_response_structure_missing_field(self):
        """Test response structure validation with missing field."""
        data = {"id": "123", "name": "Test"}
        required_fields = ["id", "name", "email"]
        
        with pytest.raises(AssertionError) as exc_info:
            TestDataValidator.validate_response_structure(data, required_fields)
        
        assert "Required field 'email' missing" in str(exc_info.value)


class TestTestConfig:
    """Test the test configuration utilities."""
    
    def test_test_data_constants(self):
        """Test that test data constants are properly defined."""
        assert TestData.VALID_USER_DATA["username"] == "testuser"
        assert TestData.ADMIN_USER_DATA["roles"] == ["admin", "user"]
        assert TestData.VALID_POST_DATA["is_published"] is False
    
    def test_test_endpoints_constants(self):
        """Test that endpoint constants are properly defined."""
        assert TestEndpoints.API_V1_BASE == "/api/v1"
        assert TestEndpoints.HEALTH_CHECK == "/healthz"
        assert TestEndpoints.USERS_BASE == "/api/v1/users"
    
    def test_test_endpoints_formatting(self):
        """Test endpoint formatting methods."""
        user_id = "123"
        endpoint = TestEndpoints.user_detail(user_id)
        assert endpoint == "/api/v1/users/123"
    
    def test_test_headers_utilities(self):
        """Test header utility methods."""
        token = "test-token"
        headers = TestHeaders.authorization_bearer(token)
        assert headers["Authorization"] == "Bearer test-token"
        
        request_id = "req-123"
        headers = TestHeaders.with_request_id(request_id)
        assert headers["X-Request-ID"] == "req-123"


class TestTestAssertions:
    """Test the test assertion utilities."""
    
    def test_assert_valid_uuid_success(self):
        """Test UUID assertion with valid UUID."""
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        # Should not raise
        TestAssertions.assert_valid_uuid(valid_uuid)
    
    def test_assert_valid_uuid_failure(self):
        """Test UUID assertion with invalid UUID."""
        invalid_uuid = "not-a-uuid"
        with pytest.raises(AssertionError):
            TestAssertions.assert_valid_uuid(invalid_uuid)
    
    def test_assert_valid_timestamp_success(self):
        """Test timestamp assertion with valid timestamp."""
        valid_timestamp = "2024-01-01T12:00:00Z"
        # Should not raise
        TestAssertions.assert_valid_timestamp(valid_timestamp)
    
    def test_assert_valid_timestamp_failure(self):
        """Test timestamp assertion with invalid timestamp."""
        invalid_timestamp = "not-a-timestamp"
        with pytest.raises(AssertionError):
            TestAssertions.assert_valid_timestamp(invalid_timestamp)
    
    def test_assert_valid_email_success(self):
        """Test email assertion with valid email."""
        valid_email = "test@example.com"
        # Should not raise
        TestAssertions.assert_valid_email(valid_email)
    
    def test_assert_valid_email_failure(self):
        """Test email assertion with invalid email."""
        invalid_email = "not-an-email"
        with pytest.raises(AssertionError):
            TestAssertions.assert_valid_email(invalid_email)
    
    def test_assert_response_time_success(self):
        """Test response time assertion within limits."""
        response_time = 0.5
        max_time = 1.0
        # Should not raise
        TestAssertions.assert_response_time(response_time, max_time)
    
    def test_assert_response_time_failure(self):
        """Test response time assertion exceeding limits."""
        response_time = 2.0
        max_time = 1.0
        with pytest.raises(AssertionError):
            TestAssertions.assert_response_time(response_time, max_time)
    
    def test_assert_pagination_response_success(self):
        """Test pagination response assertion with valid data."""
        data = {
            "items": [{"id": "1"}, {"id": "2"}],
            "total": 10,
            "page": 1,
            "size": 2,
            "pages": 5
        }
        # Should not raise
        TestAssertions.assert_pagination_response(data)
    
    def test_assert_pagination_response_failure(self):
        """Test pagination response assertion with invalid data."""
        data = {
            "items": [{"id": "1"}],
            "total": "invalid",  # Should be int
            "page": 1,
            "size": 2,
            "pages": 5
        }
        with pytest.raises(AssertionError):
            TestAssertions.assert_pagination_response(data)


class TestAsyncTestCase(AsyncTestCase):
    """Test the async test case base class."""
    
    @pytest.mark.asyncio
    async def test_assert_async_raises_success(self):
        """Test async exception assertion - success case."""
        async def failing_function():
            raise ValueError("Test error")
        
        # Should not raise AssertionError
        await self.assert_async_raises(ValueError, failing_function)
    
    @pytest.mark.asyncio
    async def test_assert_async_no_raises_success(self):
        """Test async no exception assertion - success case."""
        async def working_function():
            return "success"
        
        result = await self.assert_async_no_raises(working_function)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_assert_async_no_raises_failure(self):
        """Test async no exception assertion - failure case."""
        async def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(pytest.fail.Exception):
            await self.assert_async_no_raises(failing_function)


@pytest.mark.integration
class TestFrameworkIntegration:
    """Integration tests for the testing framework components."""
    
    def test_factory_with_test_data(self):
        """Test using factories with test data constants."""
        user_data = TestData.VALID_USER_DATA.copy()
        user = UserFactory(**user_data)
        
        assert user.username == user_data["username"]
        assert user.email == user_data["email"]
    
    def test_api_helper_with_mock_response(self):
        """Test API helper with mock response."""
        json_data = {"id": "123", "name": "Test"}
        mock_response = MockHelper.create_mock_response(
            status_code=200,
            json_data=json_data
        )
        
        result = APITestHelper.assert_success_response(mock_response)
        assert result == json_data
    
    def test_validator_with_factory_data(self):
        """Test validator with factory-generated data."""
        user = UserFactory()
        
        # These should not raise
        TestDataValidator.validate_uuid(user.id)
        TestDataValidator.validate_email(user.email)
    
    def test_complete_test_scenario(self):
        """Test a complete testing scenario using all components."""
        # Create test data
        user = UserFactory()
        post = PostFactory(author_id=user.id)
        
        # Validate data
        TestDataValidator.validate_uuid(user.id)
        TestDataValidator.validate_uuid(post.id)
        TestDataValidator.validate_email(user.email)
        
        # Create mock API response
        response_data = {
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            },
            "post": {
                "id": post.id,
                "title": post.title,
                "author_id": post.author_id
            }
        }
        
        mock_response = MockHelper.create_mock_response(
            status_code=200,
            json_data=response_data
        )
        
        # Test API response
        result = APITestHelper.assert_success_response(mock_response)
        assert result["user"]["id"] == user.id
        assert result["post"]["author_id"] == user.id
        
        # Test response schema
        APITestHelper.assert_response_schema(
            result,
            required_fields=["user", "post"]
        )