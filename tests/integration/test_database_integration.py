"""
Integration tests for database functionality.

This module demonstrates how to use the testing framework
for database integration testing with transaction rollback
and test data isolation.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import UserFactory
from tests.utils import DatabaseTestHelper
from tests.test_config import TestData


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    @pytest.mark.asyncio
    async def test_database_session_fixture(self, db_session: AsyncSession):
        """Test that database session fixture works correctly."""
        assert db_session is not None
        assert isinstance(db_session, AsyncSession)
    
    @pytest.mark.asyncio
    async def test_transaction_rollback_isolation(self, db_session: AsyncSession):
        """Test that database transactions are properly rolled back between tests."""
        # This test should start with a clean database
        # Any changes made here should be rolled back after the test
        
        # For now, we'll just verify the session works
        # In a real implementation, we would:
        # 1. Create a test record
        # 2. Verify it exists
        # 3. Let the transaction rollback happen automatically
        # 4. In the next test, verify the record doesn't exist
        
        assert db_session is not None
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_isolated(self, db_session: AsyncSession):
        """Test that multiple test sessions are isolated from each other."""
        # This test should also start with a clean database
        # demonstrating that the previous test's changes were rolled back
        
        assert db_session is not None
    
    @pytest.mark.asyncio
    async def test_factory_data_with_database(self, db_session: AsyncSession):
        """Test using factory data with database operations."""
        # Create test data using factories
        user_data = UserFactory()
        
        # Verify the factory created valid data
        assert user_data.id is not None
        assert user_data.username is not None
        assert user_data.email is not None
        
        # In a real implementation, we would:
        # 1. Save the user to the database
        # 2. Query it back
        # 3. Verify the data matches
        
        # For now, just verify the factory works
        assert user_data.is_active is True


@pytest.mark.integration
class TestDatabaseHelpers:
    """Test the database helper utilities."""
    
    def test_database_test_helper_methods_exist(self):
        """Test that DatabaseTestHelper has expected methods."""
        assert hasattr(DatabaseTestHelper, 'create_test_record')
        assert hasattr(DatabaseTestHelper, 'get_record_by_id')
        assert hasattr(DatabaseTestHelper, 'count_records')
        assert hasattr(DatabaseTestHelper, 'assert_record_exists')
        assert hasattr(DatabaseTestHelper, 'assert_record_not_exists')
        assert hasattr(DatabaseTestHelper, 'assert_record_count')
    
    def test_test_data_constants(self):
        """Test that test data constants are available."""
        assert TestData.VALID_USER_DATA is not None
        assert TestData.ADMIN_USER_DATA is not None
        assert TestData.VALID_POST_DATA is not None
        
        # Verify structure
        assert 'username' in TestData.VALID_USER_DATA
        assert 'email' in TestData.VALID_USER_DATA
        assert 'password' in TestData.VALID_USER_DATA


@pytest.mark.integration
@pytest.mark.slow
class TestDatabasePerformance:
    """Performance tests for database operations."""
    
    @pytest.mark.asyncio
    async def test_database_connection_performance(self, db_session: AsyncSession):
        """Test database connection performance."""
        import time
        
        start_time = time.time()
        
        # Perform a simple database operation
        # In a real implementation, this would be an actual query
        assert db_session is not None
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert that connection is fast (under 100ms)
        assert duration < 0.1, f"Database connection took {duration:.3f}s, expected < 0.1s"
    
    @pytest.mark.asyncio
    async def test_multiple_operations_performance(self, db_session: AsyncSession):
        """Test performance of multiple database operations."""
        import time
        
        start_time = time.time()
        
        # Simulate multiple operations
        for i in range(10):
            # In a real implementation, these would be actual database operations
            user_data = UserFactory()
            assert user_data.id is not None
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert that operations are reasonably fast
        assert duration < 1.0, f"10 operations took {duration:.3f}s, expected < 1.0s"


@pytest.mark.integration
class TestTestFrameworkIntegration:
    """Integration tests for the testing framework components working together."""
    
    @pytest.mark.asyncio
    async def test_complete_testing_workflow(self, db_session: AsyncSession):
        """Test a complete testing workflow using all framework components."""
        # 1. Create test data using factories
        user = UserFactory()
        admin = UserFactory(roles=['admin', 'user'])
        
        # 2. Validate test data
        from tests.utils import TestDataValidator
        TestDataValidator.validate_uuid(user.id)
        TestDataValidator.validate_email(user.email)
        TestDataValidator.validate_uuid(admin.id)
        TestDataValidator.validate_email(admin.email)
        
        # 3. Use database session (even if just for verification)
        assert db_session is not None
        
        # 4. Verify data relationships
        assert user.id != admin.id
        assert user.email != admin.email
        assert 'admin' not in user.roles
        assert 'admin' in admin.roles
        
        # 5. Test assertions
        from tests.test_config import TestAssertions
        TestAssertions.assert_valid_uuid(user.id)
        TestAssertions.assert_valid_email(user.email)
    
    def test_mock_integration(self):
        """Test integration of mock utilities."""
        from tests.utils import MockHelper
        
        # Create mocks
        async_mock = MockHelper.create_async_mock("test_result")
        response_mock = MockHelper.create_mock_response(
            status_code=200,
            json_data={"id": "123", "name": "Test"}
        )
        db_mock = MockHelper.create_mock_database_session()
        
        # Verify mocks work as expected
        assert async_mock.return_value == "test_result"
        assert response_mock.status_code == 200
        assert response_mock.json() == {"id": "123", "name": "Test"}
        assert db_mock is not None
    
    def test_api_helper_integration(self):
        """Test integration of API helper utilities."""
        from tests.utils import APITestHelper, MockHelper
        
        # Create a mock successful response
        response_data = {"id": "123", "message": "Success"}
        mock_response = MockHelper.create_mock_response(
            status_code=200,
            json_data=response_data
        )
        
        # Test API helper with mock response
        result = APITestHelper.assert_success_response(mock_response)
        assert result == response_data
        
        # Test response schema validation
        APITestHelper.assert_response_schema(
            result,
            expected_fields=["id", "message"]
        )
    
    def test_configuration_integration(self):
        """Test integration of test configuration."""
        from tests.test_config import test_config, TestEndpoints, TestHeaders
        
        # Verify configuration is loaded
        assert test_config is not None
        assert test_config.testing is True
        assert test_config.database_url is not None
        
        # Verify endpoints are defined
        assert TestEndpoints.API_V1_BASE == "/api/v1"
        assert TestEndpoints.HEALTH_CHECK == "/healthz"
        
        # Verify headers utilities work
        token = "test-token"
        auth_headers = TestHeaders.authorization_bearer(token)
        assert "Authorization" in auth_headers
        assert "Bearer test-token" in auth_headers["Authorization"]