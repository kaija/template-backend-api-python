"""
Alembic environment configuration for database migrations.

This module configures Alembic to work with our SQLAlchemy models
and provides both online and offline migration capabilities with
comprehensive error handling and configuration management.
"""

import asyncio
import logging
import os
import sys
from logging.config import fileConfig
from pathlib import Path
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import your models here so Alembic can detect them
try:
    from src.database.base import Base
    from src.database.models import User, APIKey, UserSession
except ImportError as e:
    print(f"Warning: Could not import models: {e}")
    print("Make sure you're running migrations from the project root directory")
    sys.exit(1)

# Import configuration with comprehensive fallback
def get_database_url():
    """Get database URL with multiple fallback options."""
    try:
        # Try to import settings from the application
        from src.config.settings import settings
        return settings.database_url
    except Exception as e:
        print(f"Warning: Could not load application settings: {e}")
        
        # Fallback to environment variables
        database_url = os.getenv("API_DATABASE_URL") or os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        
        # Final fallback to SQLite
        print("Warning: Using SQLite fallback database")
        return "sqlite+aiosqlite:///./app.db"

database_url = get_database_url()

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger(__name__)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_url():
    """Get database URL from configuration."""
    # Override the URL in alembic.ini with our configuration
    return database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    logger.info(f"Running offline migrations with URL: {url.split('@')[-1] if '@' in url else url}")
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # For SQLite compatibility
        # Include object names in autogenerate
        include_object=include_object,
        # Custom naming convention for constraints
        render_item=render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Filter objects to include in autogenerate.
    
    This function allows us to exclude certain objects from being
    automatically detected by Alembic's autogenerate feature.
    """
    # Skip temporary tables
    if type_ == "table" and name.startswith("temp_"):
        return False
    
    # Skip certain indexes that are automatically created
    if type_ == "index" and name.startswith("sqlite_"):
        return False
    
    return True


def render_item(type_, obj, autogen_context):
    """
    Custom rendering for migration items.
    
    This allows us to customize how certain items are rendered
    in the migration files.
    """
    # Use default rendering for most items
    return False


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with database connection."""
    logger.info("Configuring migration context")
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=True,  # For SQLite compatibility
        # Include schemas in autogenerate
        include_schemas=True,
        # Custom object filtering
        include_object=include_object,
        # Custom item rendering
        render_item=render_item,
        # Transaction per migration
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        logger.info("Running migrations")
        context.run_migrations()
        logger.info("Migrations completed successfully")


async def run_async_migrations() -> None:
    """Run migrations in async mode with proper error handling."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    logger.info(f"Creating async engine for migrations")
    
    try:
        connectable = async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        async with connectable.connect() as connection:
            logger.info("Connected to database, running migrations")
            await connection.run_sync(do_run_migrations)

        await connectable.dispose()
        logger.info("Migration engine disposed successfully")
        
    except Exception as e:
        logger.error(f"Error during async migrations: {e}")
        raise


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    logger.info("Starting online migrations")
    try:
        asyncio.run(run_async_migrations())
        logger.info("Online migrations completed successfully")
    except Exception as e:
        logger.error(f"Online migrations failed: {e}")
        raise


# Main execution logic
if context.is_offline_mode():
    logger.info("Running migrations in offline mode")
    run_migrations_offline()
else:
    logger.info("Running migrations in online mode")
    run_migrations_online()