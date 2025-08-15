"""
Pytest configuration and shared fixtures.

This module provides generic pytest configuration and shared fixtures for testing
FastAPI applications. It demonstrates common testing patterns and can be adapted
for different application domains.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Import application components
from src.app import get_application
from src.database.base import Base
from src.database.config import get_session_dependency
from src.dependencies import get_current_user, get_request_context


# Test database URL - use in-memory SQLite for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Global test engine and session factory
test_engine = None
test_session_factory = None


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the test session.
    
    This fixture ensures that async tests run in the same event loop
    throughout the test session.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    """
    Create test database engine for the session.
    
    This fixture creates a test database engine that's shared across
    all tests in the session for better performance.
    """
    global test_engine
    
    # Create async engine with in-memory SQLite
    test_engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
        },
    )
    
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield test_engine
    
    # Cleanup
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_session_factory(test_db_engine):
    """
    Create test session factory for the session.
    
    Args:
        test_db_engine: Test database engine fixture
        
    Returns:
        Async session factory for tests
    """
    global test_session_factory
    
    test_session_factory = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    
    return test_session_factory


@pytest_asyncio.fixture
async def db_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test with transaction rollback.
    
    This fixture creates a new database session for each test and
    automatically rolls back the transaction at the end, ensuring
    test isolation.
    
    Args:
        test_session_factory: Test session factory fixture
        
    Yields:
        Database session for the test
    """
    async with test_session_factory() as session:
        # Start a transaction
        transaction = await session.begin()
        
        try:
            yield session
        finally:
            # Always rollback the transaction to ensure test isolation
            await transaction.rollback()
            await session.close()


@pytest.fixture
def override_dependencies():
    """
    Dictionary to store dependency overrides for tests.
    
    Returns:
        Dictionary for storing FastAPI dependency overrides
    """
    return {}


@pytest.fixture
def app(db_session: AsyncSession, override_dependencies: Dict) -> FastAPI:
    """
    Create FastAPI application with test dependencies.
    
    Args:
        db_session: Test database session
        override_dependencies: Dictionary of dependency overrides
        
    Returns:
        Configured FastAPI application for testing
    """
    # Create application
    app = get_application()
    
    # Override database dependency
    app.dependency_overrides[get_session_dependency] = lambda: db_session
    
    # Apply additional dependency overrides
    for original_dep, override_dep in override_dependencies.items():
        app.dependency_overrides[original_dep] = override_dep
    
    yield app
    
    # Cleanup dependency overrides
    app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """
    Create synchronous test client.
    
    Args:
        app: FastAPI application fixture
        
    Returns:
        Synchronous test client for testing
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Create asynchronous test client.
    
    Args:
        app: FastAPI application fixture
        
    Returns:
        Asynchronous test client for testing
    """
    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def mock_user() -> Dict[str, Any]:
    """
    Create mock user data for authentication tests.
    
    Returns:
        Dictionary with mock user information
    """
    return {
        "user_id": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "roles": ["user"],
        "permissions": ["read", "write"],
        "is_active": True,
        "is_verified": True,
    }


@pytest.fixture
def mock_admin_user() -> Dict[str, Any]:
    """
    Create mock admin user data for authorization tests.
    
    Returns:
        Dictionary with mock admin user information
    """
    return {
        "user_id": "admin_user_123",
        "username": "adminuser",
        "email": "admin@example.com",
        "roles": ["admin", "user"],
        "permissions": ["read", "write", "admin", "delete"],
        "is_active": True,
        "is_verified": True,
    }


@pytest.fixture
def authenticated_app(app: FastAPI, mock_user: Dict[str, Any]) -> FastAPI:
    """
    Create FastAPI application with authenticated user.
    
    Args:
        app: FastAPI application fixture
        mock_user: Mock user data
        
    Returns:
        FastAPI application with authenticated user override
    """
    # Override authentication dependency
    app.dependency_overrides[get_current_user] = lambda: mock_user
    
    return app


@pytest.fixture
def admin_authenticated_app(app: FastAPI, mock_admin_user: Dict[str, Any]) -> FastAPI:
    """
    Create FastAPI application with authenticated admin user.
    
    Args:
        app: FastAPI application fixture
        mock_admin_user: Mock admin user data
        
    Returns:
        FastAPI application with authenticated admin user override
    """
    # Override authentication dependency
    app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    
    return app


@pytest.fixture
def mock_request_context() -> Dict[str, Any]:
    """
    Create mock request context for testing.
    
    Returns:
        Dictionary with mock request context
    """
    return {
        "request_id": "test_req_123",
        "correlation_id": "test_corr_123",
        "method": "GET",
        "url": "http://test/api/v1/test",
        "path": "/api/v1/test",
        "query_params": {},
        "user_agent": "test-client/1.0",
        "client_ip": "127.0.0.1",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def app_with_mock_context(app: FastAPI, mock_request_context: Dict[str, Any]) -> FastAPI:
    """
    Create FastAPI application with mock request context.
    
    Args:
        app: FastAPI application fixture
        mock_request_context: Mock request context
        
    Returns:
        FastAPI application with mock request context override
    """
    # Override request context dependency
    app.dependency_overrides[get_request_context] = lambda: mock_request_context
    
    return app


@pytest.fixture
def mock_redis():
    """
    Create mock Redis client for testing.
    
    Returns:
        Mock Redis client
    """
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True
    
    return mock_redis


@pytest.fixture
def mock_external_service():
    """
    Create mock external service for testing.
    
    Returns:
        Mock external service client
    """
    mock_service = AsyncMock()
    mock_service.get.return_value = {"status": "success", "data": {}}
    mock_service.post.return_value = {"status": "success", "id": "123"}
    mock_service.put.return_value = {"status": "success"}
    mock_service.delete.return_value = {"status": "success"}
    
    return mock_service


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_environment():
    """
    Set up test environment variables.
    
    This fixture automatically sets up the test environment
    for all tests.
    """
    # Set test environment
    os.environ["ENV"] = "testing"
    os.environ["DEBUG"] = "false"
    os.environ["LOG_LEVEL"] = "WARNING"
    
    # Database settings
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["DATABASE_ECHO"] = "false"
    
    # Security settings
    os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
    os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key"
    os.environ["JWT_ALGORITHM"] = "HS256"
    os.environ["JWT_EXPIRE_MINUTES"] = "30"
    
    # External service settings
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["SENTRY_DSN"] = ""  # Disable Sentry in tests
    
    yield
    
    # Cleanup environment variables
    test_env_vars = [
        "ENV", "DEBUG", "LOG_LEVEL", "DATABASE_URL", "DATABASE_ECHO",
        "SECRET_KEY", "JWT_SECRET_KEY", "JWT_ALGORITHM", "JWT_EXPIRE_MINUTES",
        "REDIS_URL", "SENTRY_DSN"
    ]
    
    for var in test_env_vars:
        os.environ.pop(var, None)


# Pytest configuration
def pytest_configure(config):
    """
    Configure pytest with custom markers and settings.
    
    Args:
        config: Pytest configuration object
    """
    # Add custom markers
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "auth: mark test as requiring authentication"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers based on test location.
    
    Args:
        config: Pytest configuration object
        items: List of collected test items
    """
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add database marker for tests using db_session fixture
        if "db_session" in item.fixturenames:
            item.add_marker(pytest.mark.database)
        
        # Add auth marker for tests using authentication fixtures
        auth_fixtures = ["authenticated_app", "admin_authenticated_app", "mock_user"]
        if any(fixture in item.fixturenames for fixture in auth_fixtures):
            item.add_marker(pytest.mark.auth)


# Async test utilities
class AsyncTestCase:
    """
    Base class for async test cases.
    
    Provides utility methods for async testing.
    """
    
    @staticmethod
    async def assert_async_raises(exception_class, async_func, *args, **kwargs):
        """
        Assert that an async function raises a specific exception.
        
        Args:
            exception_class: Expected exception class
            async_func: Async function to test
            *args: Arguments for the async function
            **kwargs: Keyword arguments for the async function
        """
        with pytest.raises(exception_class):
            await async_func(*args, **kwargs)
    
    @staticmethod
    async def assert_async_no_raises(async_func, *args, **kwargs):
        """
        Assert that an async function does not raise an exception.
        
        Args:
            async_func: Async function to test
            *args: Arguments for the async function
            **kwargs: Keyword arguments for the async function
        """
        try:
            result = await async_func(*args, **kwargs)
            return result
        except Exception as e:
            pytest.fail(f"Unexpected exception raised: {e}")


# Test data utilities
def create_test_data(model_class, **kwargs):
    """
    Create test data for a model class.
    
    Args:
        model_class: SQLAlchemy model class
        **kwargs: Field values for the model
        
    Returns:
        Model instance with test data
    """
    # Set default values for common fields
    defaults = {
        "id": f"test_{model_class.__name__.lower()}_{id(kwargs)}",
    }
    
    # Merge defaults with provided kwargs
    data = {**defaults, **kwargs}
    
    return model_class(**data)


# Coverage configuration
pytest_plugins = ["pytest_cov"]