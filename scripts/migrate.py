#!/usr/bin/env python3
"""
Database migration management script.

This script provides convenient commands for managing database migrations
with proper error handling and validation.
"""

import argparse
import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config.settings import settings, is_production
    from src.database.config import init_database, close_database, get_session
except ImportError as e:
    print(f"Error importing application modules: {e}")
    print("Make sure you're running this script from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations with safety checks and validation."""
    
    def __init__(self):
        self.project_root = project_root
        self.alembic_cfg = self.project_root / "alembic.ini"
        
    def _run_alembic_command(self, command: list, check_production: bool = True) -> int:
        """
        Run an Alembic command with safety checks.
        
        Args:
            command: Alembic command as list of strings
            check_production: Whether to check for production environment
            
        Returns:
            Exit code from the command
        """
        if check_production and is_production():
            logger.warning("Running migration command in PRODUCTION environment!")
            response = input("Are you sure you want to continue? (yes/no): ")
            if response.lower() != "yes":
                logger.info("Migration cancelled by user")
                return 1
        
        logger.info(f"Running command: alembic {' '.join(command)}")
        
        try:
            result = subprocess.run(
                ["alembic"] + command,
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
                
            return result.returncode
            
        except FileNotFoundError:
            logger.error("Alembic not found. Make sure it's installed: pip install alembic")
            return 1
        except Exception as e:
            logger.error(f"Error running Alembic command: {e}")
            return 1
    
    async def check_database_connection(self) -> bool:
        """
        Check if database connection is working.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            await init_database(create_tables=False)
            async with get_session() as session:
                await session.execute("SELECT 1")
            await close_database()
            logger.info("Database connection successful")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def upgrade(self, revision: str = "head") -> int:
        """
        Upgrade database to a specific revision.
        
        Args:
            revision: Target revision (default: head)
            
        Returns:
            Exit code
        """
        logger.info(f"Upgrading database to revision: {revision}")
        return self._run_alembic_command(["upgrade", revision])
    
    def downgrade(self, revision: str) -> int:
        """
        Downgrade database to a specific revision.
        
        Args:
            revision: Target revision
            
        Returns:
            Exit code
        """
        logger.warning(f"Downgrading database to revision: {revision}")
        return self._run_alembic_command(["downgrade", revision])
    
    def current(self) -> int:
        """
        Show current database revision.
        
        Returns:
            Exit code
        """
        return self._run_alembic_command(["current"], check_production=False)
    
    def history(self, verbose: bool = False) -> int:
        """
        Show migration history.
        
        Args:
            verbose: Show verbose output
            
        Returns:
            Exit code
        """
        command = ["history"]
        if verbose:
            command.append("--verbose")
        return self._run_alembic_command(command, check_production=False)
    
    def show(self, revision: str) -> int:
        """
        Show details of a specific revision.
        
        Args:
            revision: Revision to show
            
        Returns:
            Exit code
        """
        return self._run_alembic_command(["show", revision], check_production=False)
    
    def revision(self, message: str, autogenerate: bool = True) -> int:
        """
        Create a new migration revision.
        
        Args:
            message: Migration message
            autogenerate: Whether to use autogenerate
            
        Returns:
            Exit code
        """
        command = ["revision", "-m", message]
        if autogenerate:
            command.append("--autogenerate")
        
        logger.info(f"Creating new revision: {message}")
        return self._run_alembic_command(command, check_production=False)
    
    def stamp(self, revision: str) -> int:
        """
        Stamp database with a specific revision without running migrations.
        
        Args:
            revision: Revision to stamp
            
        Returns:
            Exit code
        """
        logger.warning(f"Stamping database with revision: {revision}")
        return self._run_alembic_command(["stamp", revision])
    
    def check(self) -> int:
        """
        Check if there are any pending migrations.
        
        Returns:
            Exit code (0 if up to date, 1 if migrations pending)
        """
        logger.info("Checking for pending migrations")
        
        # Get current revision
        result = subprocess.run(
            ["alembic", "current"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("Failed to get current revision")
            return 1
        
        current_output = result.stdout.strip()
        
        # Get head revision
        result = subprocess.run(
            ["alembic", "heads"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error("Failed to get head revision")
            return 1
        
        head_output = result.stdout.strip()
        
        if "head" in current_output.lower() or current_output == head_output:
            logger.info("Database is up to date")
            return 0
        else:
            logger.warning("Database has pending migrations")
            logger.info(f"Current: {current_output}")
            logger.info(f"Head: {head_output}")
            return 1
    
    async def test_migration(self, revision: str = "head") -> bool:
        """
        Test migration by upgrading and then downgrading.
        
        Args:
            revision: Target revision for testing
            
        Returns:
            True if test successful, False otherwise
        """
        logger.info("Starting migration test")
        
        try:
            # Check database connection
            if not await self.check_database_connection():
                return False
            
            # Get current revision
            result = subprocess.run(
                ["alembic", "current"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error("Failed to get current revision")
                return False
            
            original_revision = result.stdout.strip()
            logger.info(f"Original revision: {original_revision}")
            
            # Upgrade to target revision
            if self.upgrade(revision) != 0:
                logger.error("Upgrade failed during test")
                return False
            
            # Downgrade back to original revision
            if original_revision and "head" not in original_revision.lower():
                if self.downgrade(original_revision.split()[0]) != 0:
                    logger.error("Downgrade failed during test")
                    return False
            
            logger.info("Migration test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration test failed: {e}")
            return False


async def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(description="Database migration management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument("revision", nargs="?", default="head", help="Target revision")
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("revision", help="Target revision")
    
    # Current command
    subparsers.add_parser("current", help="Show current revision")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show revision details")
    show_parser.add_argument("revision", help="Revision to show")
    
    # Revision command
    revision_parser = subparsers.add_parser("revision", help="Create new revision")
    revision_parser.add_argument("-m", "--message", required=True, help="Migration message")
    revision_parser.add_argument("--no-autogenerate", action="store_true", help="Disable autogenerate")
    
    # Stamp command
    stamp_parser = subparsers.add_parser("stamp", help="Stamp database with revision")
    stamp_parser.add_argument("revision", help="Revision to stamp")
    
    # Check command
    subparsers.add_parser("check", help="Check for pending migrations")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test migration up and down")
    test_parser.add_argument("revision", nargs="?", default="head", help="Target revision")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    manager = MigrationManager()
    
    try:
        if args.command == "upgrade":
            return manager.upgrade(args.revision)
        elif args.command == "downgrade":
            return manager.downgrade(args.revision)
        elif args.command == "current":
            return manager.current()
        elif args.command == "history":
            return manager.history(args.verbose)
        elif args.command == "show":
            return manager.show(args.revision)
        elif args.command == "revision":
            return manager.revision(args.message, not args.no_autogenerate)
        elif args.command == "stamp":
            return manager.stamp(args.revision)
        elif args.command == "check":
            return manager.check()
        elif args.command == "test":
            success = await manager.test_migration(args.revision)
            return 0 if success else 1
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))