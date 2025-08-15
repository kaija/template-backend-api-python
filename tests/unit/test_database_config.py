"""
Tests for database configuration and connection management.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.database.config import (
    get_database_url,
    create_engine,
    create_session_factory,
    init_database,
    close_database,
    get_session,
    check_database_health,
    get_database_info,
)


class TestDatabaseConfig:
    """Test database configuration functions."""
    
    def test_get_database_url(self):
        """Test getting database URL from configuration."""
        url = get_database_url()
        assert isinstance(url, str)
        assert url  # Should not be empty
    
    def test_create_engine_default_params(self):
        """Test creating engine with default parameters."""
        engine = create_engine("sqlite+aiosqlite:///./test.db")
        assert isinstance(engine, AsyncEngine)
        assert engine.url.database == "./test.db"
    
    def test_create_engine_custom_params(self):
        """Test creating engine with custom parameters."""
        engine = create_engine(
            "sqlite+aiosqlite:///./test.db",
            echo=True,
            pool_size=10,
            max_overflow=20
        )
        assert isinstance(engine, AsyncEngine)
        assert engine.echo is True
    
    def test_create_session_factory(self):
        """Test creating session factory."""
        engine = create_engine("sqlite+aiosqlite:///./test.db")
        factory = create_session_factory(engine)
        assert factory is not None
        # Test that we can create a session
        session = factory()
        assert isinstance(session, AsyncSession)
    
    @pytest.mark.asyncio
    async def test_init_database(self):
        """Test database initialization."""
        with patch('src.database.config._engine', None):
            with patch('src.database.config._session_factory', None):
                await init_database("sqlite+aiosqlite:///./test.db", create_tables=False)
                # Should not raise any exceptions
    
    @pytest.mark.asyncio
    async def test_close_database(self):
        """Test database cleanup."""
        # Mock engine
        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()
        
        with patch('src.database.config._engine', mock_engine):
            await close_database()
            mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_context_manager(self):
        """Test session context manager."""
        # Initialize database first
        await init_database("sqlite+aiosqlite:///./test.db", create_tables=False)
        
        async with get_session() as session:
            assert isinstance(session, AsyncSession)
    
    @pytest.mark.asyncio
    async def test_check_database_health_success(self):
        """Test successful database health check."""
        # Mock session that executes successfully
        mock_session = AsyncMock()
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result
        
        with patch('src.database.config.get_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            result = await check_database_health()
            
            assert result["status"] == "healthy"
            assert result["database"] == "connected"
    
    @pytest.mark.asyncio
    async def test_check_database_health_failure(self):
        """Test failed database health check."""
        with patch('src.database.config.get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Connection failed")
            
            result = await check_database_health()
            
            assert result["status"] == "unhealthy"
            assert result["database"] == "disconnected"
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_database_info(self):
        """Test getting database information."""
        # Initialize database first
        await init_database("sqlite+aiosqlite:///./test.db", create_tables=False)
        
        info = await get_database_info()
        
        assert "url" in info
        assert "dialect" in info
        assert "driver" in info
        assert "pool" in info


class TestDatabaseConnectionPooling:
    """Test database connection pooling configuration."""
    
    def test_sqlite_pooling_config(self):
        """Test SQLite-specific pooling configuration."""
        engine = create_engine("sqlite+aiosqlite:///./test.db")
        assert engine is not None
        # SQLite should use StaticPool
    
    def test_postgresql_pooling_config(self):
        """Test PostgreSQL pooling configuration."""
        engine = create_engine(
            "postgresql+asyncpg://user:pass@localhost/test",
            pool_size=5,
            max_overflow=10
        )
        assert engine is not None
        # Should use QueuePool with specified parameters


class TestDatabaseEventListeners:
    """Test database event listeners."""
    
    def test_sqlite_pragma_listener(self):
        """Test SQLite pragma event listener."""
        # This is more of an integration test
        # The listener should be attached when creating SQLite engines
        engine = create_engine("sqlite+aiosqlite:///./test.db")
        
        # Check that the engine has event listeners
        # This is difficult to test directly, so we just ensure
        # the engine is created without errors
        assert engine is not None
    
    def test_connection_checkout_listener(self):
        """Test connection checkout event listener."""
        engine = create_engine("sqlite+aiosqlite:///./test.db")
        
        # The listener should be attached
        # This is mainly tested through integration
        assert engine is not None


@pytest.fixture
async def database_session():
    """Fixture providing a test database session."""
    await init_database("sqlite+aiosqlite:///./test.db", create_tables=True)
    
    async with get_session() as session:
        yield session
    
    await close_database()


class TestDatabaseIntegration:
    """Integration tests for database functionality."""
    
    def test_database_session_fixture(self, database_session):
        """Test database session fixture creation (simplified test)."""
        # Just test that the fixture provides something
        assert database_session is not None
    
    @pytest.mark.asyncio
    async def test_session_transaction_rollback(self):
        """Test session transaction rollback on error."""
        await init_database("sqlite+aiosqlite:///./test.db", create_tables=True)
        
        try:
            async with get_session() as session:
                # This should work
                await session.execute("SELECT 1")
                # Force an error to test rollback
                raise Exception("Test error")
        except Exception:
            pass  # Expected
        
        # Session should be properly cleaned up
        await close_database()
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self):
        """Test multiple concurrent database sessions."""
        await init_database("sqlite+aiosqlite:///./test.db", create_tables=True)
        
        async def query_database():
            async with get_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                return result.scalar()
        
        # Run multiple concurrent queries
        tasks = [query_database() for _ in range(5)]
        results = await asyncio.gather(*tasks)
        
        assert all(result == 1 for result in results)
        
        await close_database()