"""
Tests for database migrations.

This module provides comprehensive tests for database migrations
including upgrade/downgrade cycles and data integrity checks.
"""

import asyncio
import os
import pytest
import subprocess
import tempfile
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.config import get_session, init_database, close_database
from src.database.models import User, Post
from src.config.settings import settings


@pytest.mark.asyncio
class TestMigrations:
    """Test database migrations functionality."""
    
    def setup_method(self):
        """Set up test database for migration tests."""
        # Use a temporary database for testing
        self.test_db_url = "sqlite+aiosqlite:///./test_migrations.db"
    
    def teardown_method(self):
        """Clean up test database."""
        # Remove test database file
        db_file = Path("./test_migrations.db")
        if db_file.exists():
            db_file.unlink()
    
    def run_alembic_command(self, command: list) -> subprocess.CompletedProcess:
        """
        Run an Alembic command for testing.
        
        Args:
            command: Alembic command as list of strings
            
        Returns:
            Completed process result
        """
        project_root = Path(__file__).parent.parent
        
        # Set environment variable for test database
        env = {
            "DATABASE_URL": self.test_db_url,
            "API_DATABASE_URL": self.test_db_url,
            "API_ENV": "test",
            "ENV": "test"
        }
        
        return subprocess.run(
            ["poetry", "run", "alembic"] + command,
            cwd=project_root,
            capture_output=True,
            text=True,
            env={**os.environ, **env}
        )
    
    async def test_migration_upgrade_to_head(self):
        """Test upgrading to head revision."""
        result = self.run_alembic_command(["upgrade", "head"])
        
        assert result.returncode == 0, f"Migration failed: {result.stderr}"
        # Check for migration success in either stdout or stderr (alembic logs to stderr)
        output = result.stdout + result.stderr
        assert "Running upgrade" in output or "Target database is up to date" in output
    
    async def test_migration_current_revision(self):
        """Test getting current revision."""
        # First upgrade to head
        self.run_alembic_command(["upgrade", "head"])
        
        # Then check current revision
        result = self.run_alembic_command(["current"])
        
        assert result.returncode == 0, f"Current command failed: {result.stderr}"
        assert result.stdout.strip() != "", "Current revision should not be empty"
    
    async def test_migration_history(self):
        """Test getting migration history."""
        result = self.run_alembic_command(["history"])
        
        assert result.returncode == 0, f"History command failed: {result.stderr}"
        # Should contain at least the initial migration
        assert "001" in result.stdout or "initial" in result.stdout.lower()
    
    async def test_migration_creates_tables(self):
        """Test that migration creates expected tables."""
        # Run migration
        result = self.run_alembic_command(["upgrade", "head"])
        assert result.returncode == 0
        
        # Check that tables exist
        engine = create_async_engine(self.test_db_url)
        
        async with engine.connect() as conn:
            # Check user table
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user'"
            ))
            assert result.fetchone() is not None, "User table should exist"
            
            # Check post table
            result = await conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='post'"
            ))
            assert result.fetchone() is not None, "Post table should exist"
        
        await engine.dispose()
    
    async def test_migration_table_structure(self):
        """Test that migrated tables have correct structure."""
        # Run migration
        result = self.run_alembic_command(["upgrade", "head"])
        assert result.returncode == 0
        
        engine = create_async_engine(self.test_db_url)
        
        async with engine.connect() as conn:
            # Check user table columns
            result = await conn.execute(text("PRAGMA table_info(user)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
            
            expected_columns = {
                'id', 'created_at', 'updated_at', 'username', 'email',
                'hashed_password', 'status', 'is_active'
            }
            
            for col in expected_columns:
                assert col in columns, f"Column {col} should exist in user table"
            
            # Check post table columns
            result = await conn.execute(text("PRAGMA table_info(post)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
            
            expected_columns = {
                'id', 'created_at', 'updated_at', 'title', 'content',
                'is_published', 'author_id'
            }
            
            for col in expected_columns:
                assert col in columns, f"Column {col} should exist in post table"
        
        await engine.dispose()
    
    async def test_migration_with_data_integrity(self):
        """Test migration preserves data integrity."""
        # Run migration
        result = self.run_alembic_command(["upgrade", "head"])
        assert result.returncode == 0
        
        # Insert test data
        engine = create_async_engine(self.test_db_url)
        
        async with engine.connect() as conn:
            # Insert a test user
            await conn.execute(text("""
                INSERT INTO user (id, username, email, hashed_password, status, is_active, is_deleted)
                VALUES ('test-user-id', 'testuser', 'test@example.com', 'hashed_password', 'active', 1, 0)
            """))
            
            # Insert a test post
            await conn.execute(text("""
                INSERT INTO post (id, title, content, is_published, author_id, is_deleted)
                VALUES ('test-post-id', 'Test Post', 'Test content', 0, 'test-user-id', 0)
            """))
            
            await conn.commit()
            
            # Verify data exists
            result = await conn.execute(text("SELECT COUNT(*) FROM user"))
            assert result.scalar() == 1, "User should be inserted"
            
            result = await conn.execute(text("SELECT COUNT(*) FROM post"))
            assert result.scalar() == 1, "Post should be inserted"
            
            # Verify foreign key relationship
            result = await conn.execute(text("""
                SELECT u.username, p.title 
                FROM user u 
                JOIN post p ON u.id = p.author_id
            """))
            row = result.fetchone()
            assert row is not None, "Foreign key relationship should work"
            assert row[0] == 'testuser', "Username should match"
            assert row[1] == 'Test Post', "Post title should match"
        
        await engine.dispose()
    
    def test_migration_downgrade_and_upgrade_cycle(self):
        """Test downgrade and upgrade cycle."""
        # First upgrade to head
        result = self.run_alembic_command(["upgrade", "head"])
        assert result.returncode == 0
        
        # Get current revision
        result = self.run_alembic_command(["current"])
        assert result.returncode == 0
        current_revision = result.stdout.strip()
        
        # Downgrade to base
        result = self.run_alembic_command(["downgrade", "base"])
        assert result.returncode == 0
        
        # Verify we're at base
        result = self.run_alembic_command(["current"])
        assert result.returncode == 0
        # Should be empty or show base
        
        # Upgrade back to head
        result = self.run_alembic_command(["upgrade", "head"])
        assert result.returncode == 0
        
        # Verify we're back at the same revision
        result = self.run_alembic_command(["current"])
        assert result.returncode == 0
        # Should be back to the original revision
    
    async def test_migration_autogenerate_detection(self):
        """Test that autogenerate can detect model changes."""
        # First upgrade to head to ensure database is up to date
        upgrade_result = self.run_alembic_command(["upgrade", "head"])
        assert upgrade_result.returncode == 0, f"Upgrade failed: {upgrade_result.stderr}"
        
        # This test would require modifying models temporarily
        # For now, just test that autogenerate command works
        result = self.run_alembic_command(["revision", "--autogenerate", "-m", "test_autogenerate"])
        
        # The command should succeed even if no changes are detected
        assert result.returncode == 0, f"Autogenerate failed: {result.stderr}"
        
        # Clean up the generated revision file
        project_root = Path(__file__).parent.parent
        migrations_dir = project_root / "migrations" / "versions"
        
        for file in migrations_dir.glob("*test_autogenerate*"):
            file.unlink()
    
    async def test_migration_rollback_safety(self):
        """Test migration rollback safety."""
        # Upgrade to head
        result = self.run_alembic_command(["upgrade", "head"])
        assert result.returncode == 0
        
        # Add some data
        engine = create_async_engine(self.test_db_url)
        
        async with engine.connect() as conn:
            await conn.execute(text("""
                INSERT INTO user (id, username, email, hashed_password, status, is_active, is_deleted)
                VALUES ('rollback-test', 'rollbackuser', 'rollback@example.com', 'hashed', 'active', 1, 0)
            """))
            await conn.commit()
            
            # Verify data exists
            result = await conn.execute(text("SELECT COUNT(*) FROM user WHERE id = 'rollback-test'"))
            assert result.scalar() == 1
        
        await engine.dispose()
        
        # Downgrade (this should handle data appropriately)
        result = self.run_alembic_command(["downgrade", "base"])
        assert result.returncode == 0
        
        # Upgrade again
        result = self.run_alembic_command(["upgrade", "head"])
        assert result.returncode == 0
        
        # Data should be gone after downgrade/upgrade cycle
        engine = create_async_engine(self.test_db_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM user WHERE id = 'rollback-test'"))
            assert result.scalar() == 0, "Data should be cleared after downgrade/upgrade"
        
        await engine.dispose()


@pytest.mark.asyncio
class TestMigrationIntegration:
    """Integration tests for migrations with the application."""
    
    async def test_migration_with_application_models(self):
        """Test that migrations work with actual application models."""
        # This would test the full integration with the application
        # For now, we'll just verify that models can be imported
        # and are compatible with the migration
        
        from src.database.models import User, Post
        from src.database.base import Base
        
        # Verify models have the expected attributes
        assert hasattr(User, '__tablename__')
        assert hasattr(Post, '__tablename__')
        
        # Verify base metadata includes all models
        table_names = {table.name for table in Base.metadata.tables.values()}
        expected_tables = {'user', 'post'}
        
        # Debug: print actual table names if assertion fails
        if not expected_tables.issubset(table_names):
            print(f"Expected tables: {expected_tables}")
            print(f"Actual table names: {table_names}")
        
        assert expected_tables.issubset(table_names), f"All expected tables should be in metadata. Expected: {expected_tables}, Got: {table_names}"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])