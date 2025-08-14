"""
Database configuration and connection management.

This module provides database configuration, connection pooling,
and session management for SQLAlchemy.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine as sa_create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import QueuePool, StaticPool
from sqlalchemy.engine import Engine

# Import configuration functions with fallback for testing
try:
    from src.config.settings import settings, is_development, is_testing
except Exception:
    # Fallback for testing when configuration is not available
    class MockSettings:
        database_url = "sqlite+aiosqlite:///./test.db"
        database_pool_size = 5
        database_max_overflow = 10
        database_pool_timeout = 30
        database_pool_recycle = 3600
        database_echo = False
    
    settings = MockSettings()
    
    def is_development():
        return True
    
    def is_testing():
        return False

logger = logging.getLogger(__name__)

# Global database engine and session factory
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """
    Get database URL from configuration.
    
    Returns:
        Database URL string
    """
    return settings.database_url


def create_engine(
    database_url: Optional[str] = None,
    echo: Optional[bool] = None,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    pool_timeout: Optional[int] = None,
    pool_recycle: Optional[int] = None,
) -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.
    
    Args:
        database_url: Database URL (uses settings if not provided)
        echo: Enable SQL query logging
        pool_size: Connection pool size
        max_overflow: Maximum pool overflow
        pool_timeout: Pool timeout in seconds
        pool_recycle: Pool recycle time in seconds
        
    Returns:
        Configured async SQLAlchemy engine
    """
    if database_url is None:
        database_url = get_database_url()
    
    if echo is None:
        echo = getattr(settings, 'database_echo', is_development())
    
    if pool_size is None:
        pool_size = getattr(settings, 'database_pool_size', 5)
    
    if max_overflow is None:
        max_overflow = getattr(settings, 'database_max_overflow', 10)
    
    if pool_timeout is None:
        pool_timeout = getattr(settings, 'database_pool_timeout', 30)
    
    if pool_recycle is None:
        pool_recycle = getattr(settings, 'database_pool_recycle', 3600)
    
    # Configure connection pooling based on database type
    if "sqlite" in database_url:
        # SQLite configuration
        poolclass = StaticPool
        connect_args = {
            "check_same_thread": False,
            "timeout": 20,
        }
        pool_kwargs = {
            "poolclass": poolclass,
            "connect_args": connect_args,
        }
    else:
        # PostgreSQL/MySQL configuration
        # For async engines, let SQLAlchemy choose the appropriate pool class
        pool_kwargs = {
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": True,  # Validate connections before use
        }
    
    # Create async engine
    engine = create_async_engine(
        database_url,
        echo=echo,
        future=True,
        **pool_kwargs
    )
    
    # Add connection event listeners
    _add_connection_listeners(engine)
    
    logger.info(
        f"Created database engine: {database_url.split('@')[-1] if '@' in database_url else database_url}",
        extra={
            "event_type": "database_engine_created",
            "database_type": database_url.split("://")[0],
            "pool_size": pool_size,
            "max_overflow": max_overflow,
        }
    )
    
    return engine


def _add_connection_listeners(engine: AsyncEngine) -> None:
    """
    Add connection event listeners for monitoring and optimization.
    
    Args:
        engine: SQLAlchemy async engine
    """
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance and reliability."""
        if "sqlite" in str(engine.url):
            cursor = dbapi_connection.cursor()
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            # Set WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            # Set synchronous mode for better performance
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Set cache size (negative value = KB)
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB
            # Set temp store to memory
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Create async session factory.
    
    Args:
        engine: SQLAlchemy async engine
        
    Returns:
        Async session factory
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )


async def init_database(
    database_url: Optional[str] = None,
    create_tables: bool = True
) -> None:
    """
    Initialize database connection and create tables.
    
    Args:
        database_url: Database URL (uses settings if not provided)
        create_tables: Whether to create tables
    """
    global _engine, _session_factory
    
    try:
        # Create engine
        _engine = create_engine(database_url)
        
        # Create session factory
        _session_factory = create_session_factory(_engine)
        
        # Create tables if requested
        if create_tables:
            from .base import Base
            async with _engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info(
                    "Database tables created successfully",
                    extra={"event_type": "database_tables_created"}
                )
        
        logger.info(
            "Database initialized successfully",
            extra={"event_type": "database_initialized"}
        )
        
    except Exception as e:
        logger.error(
            f"Failed to initialize database: {e}",
            extra={"event_type": "database_init_failed"},
            exc_info=True
        )
        raise


async def close_database() -> None:
    """
    Close database connections and cleanup resources.
    """
    global _engine, _session_factory
    
    try:
        if _engine:
            await _engine.dispose()
            _engine = None
            logger.info(
                "Database connections closed",
                extra={"event_type": "database_closed"}
            )
        
        _session_factory = None
        
    except Exception as e:
        logger.error(
            f"Error closing database: {e}",
            extra={"event_type": "database_close_failed"},
            exc_info=True
        )
        raise


def get_engine() -> AsyncEngine:
    """
    Get the global database engine.
    
    Returns:
        SQLAlchemy async engine
        
    Raises:
        RuntimeError: If database is not initialized
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the global session factory.
    
    Returns:
        Async session factory
        
    Raises:
        RuntimeError: If database is not initialized
    """
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session context manager.
    
    Yields:
        SQLAlchemy async session
        
    Example:
        async with get_session() as session:
            user = await session.get(User, user_id)
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        SQLAlchemy async session
        
    Example:
        @app.get("/users/{user_id}")
        async def get_user(
            user_id: int,
            session: AsyncSession = Depends(get_session_dependency)
        ):
            return await session.get(User, user_id)
    """
    async with get_session() as session:
        yield session


# Health check functions
async def check_database_health() -> dict:
    """
    Check database health and connectivity.
    
    Returns:
        Health check result dictionary
    """
    try:
        async with get_session() as session:
            # Simple query to test connectivity
            result = await session.execute("SELECT 1")
            result.scalar()
            
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
            }
            
    except Exception as e:
        logger.error(
            f"Database health check failed: {e}",
            extra={"event_type": "database_health_check_failed"},
            exc_info=True
        )
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
        }


async def get_database_info() -> dict:
    """
    Get database information and statistics.
    
    Returns:
        Database information dictionary
    """
    try:
        engine = get_engine()
        
        # Get pool information
        pool = engine.pool
        pool_info = {
            "size": getattr(pool, 'size', lambda: 0)(),
            "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
            "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
            "overflow": getattr(pool, 'overflow', lambda: 0)(),
        }
        
        return {
            "url": str(engine.url).split('@')[-1] if '@' in str(engine.url) else str(engine.url),
            "dialect": engine.dialect.name,
            "driver": engine.dialect.driver,
            "pool": pool_info,
            "echo": engine.echo,
        }
        
    except Exception as e:
        logger.error(
            f"Failed to get database info: {e}",
            extra={"event_type": "database_info_failed"},
            exc_info=True
        )
        return {
            "error": str(e)
        }