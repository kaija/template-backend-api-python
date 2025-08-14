#!/usr/bin/env python3
"""
Database rollback utility with safety checks and backup functionality.

This script provides safe rollback procedures with data backup and validation.
"""

import argparse
import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.config.settings import settings, is_production
    from src.database.config import init_database, close_database, get_session
    from sqlalchemy import text
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


class RollbackManager:
    """Manages safe database rollbacks with backup and validation."""
    
    def __init__(self):
        self.project_root = project_root
        self.backup_dir = self.project_root / "backups" / "migrations"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_alembic_command(self, command: list) -> subprocess.CompletedProcess:
        """
        Run an Alembic command.
        
        Args:
            command: Alembic command as list of strings
            
        Returns:
            Completed process result
        """
        logger.info(f"Running command: alembic {' '.join(command)}")
        
        return subprocess.run(
            ["alembic"] + command,
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
    
    async def create_data_backup(self, backup_name: Optional[str] = None) -> Path:
        """
        Create a backup of critical data before rollback.
        
        Args:
            backup_name: Optional custom backup name
            
        Returns:
            Path to the backup file
        """
        if backup_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"rollback_backup_{timestamp}"
        
        backup_file = self.backup_dir / f"{backup_name}.json"
        
        logger.info(f"Creating data backup: {backup_file}")
        
        try:
            await init_database(create_tables=False)
            
            backup_data = {
                "timestamp": datetime.now().isoformat(),
                "database_url": settings.database_url.split('@')[-1] if '@' in settings.database_url else "hidden",
                "tables": {}
            }
            
            async with get_session() as session:
                # Backup users
                result = await session.execute(text("""
                    SELECT id, username, email, full_name, status, role, 
                           is_active, is_verified, created_at, updated_at
                    FROM user 
                    WHERE is_deleted = 0
                """))
                
                users = []
                for row in result.fetchall():
                    users.append({
                        "id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "full_name": row[3],
                        "status": row[4],
                        "role": row[5],
                        "is_active": bool(row[6]),
                        "is_verified": bool(row[7]),
                        "created_at": row[8].isoformat() if row[8] else None,
                        "updated_at": row[9].isoformat() if row[9] else None,
                    })
                
                backup_data["tables"]["users"] = users
                logger.info(f"Backed up {len(users)} users")
                
                # Backup API keys
                result = await session.execute(text("""
                    SELECT id, name, key_prefix, status, user_id, 
                           usage_count, created_at, updated_at
                    FROM api_key 
                    WHERE is_deleted = 0
                """))
                
                api_keys = []
                for row in result.fetchall():
                    api_keys.append({
                        "id": row[0],
                        "name": row[1],
                        "key_prefix": row[2],
                        "status": row[3],
                        "user_id": row[4],
                        "usage_count": row[5],
                        "created_at": row[6].isoformat() if row[6] else None,
                        "updated_at": row[7].isoformat() if row[7] else None,
                    })
                
                backup_data["tables"]["api_keys"] = api_keys
                logger.info(f"Backed up {len(api_keys)} API keys")
                
                # Backup active sessions
                result = await session.execute(text("""
                    SELECT id, user_id, ip_address, expires_at, 
                           last_activity_at, is_active, created_at
                    FROM user_session 
                    WHERE is_active = 1 AND expires_at > datetime('now')
                """))
                
                sessions = []
                for row in result.fetchall():
                    sessions.append({
                        "id": row[0],
                        "user_id": row[1],
                        "ip_address": row[2],
                        "expires_at": row[3].isoformat() if row[3] else None,
                        "last_activity_at": row[4].isoformat() if row[4] else None,
                        "is_active": bool(row[5]),
                        "created_at": row[6].isoformat() if row[6] else None,
                    })
                
                backup_data["tables"]["sessions"] = sessions
                logger.info(f"Backed up {len(sessions)} active sessions")
            
            await close_database()
            
            # Write backup to file
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            logger.info(f"Backup created successfully: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    async def validate_rollback_safety(self, target_revision: str) -> Dict[str, any]:
        """
        Validate that rollback to target revision is safe.
        
        Args:
            target_revision: Target revision to rollback to
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating rollback safety to revision: {target_revision}")
        
        validation_result = {
            "safe": True,
            "warnings": [],
            "errors": [],
            "data_loss_risk": False,
            "current_revision": None,
            "target_revision": target_revision,
        }
        
        try:
            # Get current revision
            result = self._run_alembic_command(["current"])
            if result.returncode != 0:
                validation_result["errors"].append("Failed to get current revision")
                validation_result["safe"] = False
                return validation_result
            
            current_revision = result.stdout.strip()
            validation_result["current_revision"] = current_revision
            
            # Check if target revision exists
            result = self._run_alembic_command(["show", target_revision])
            if result.returncode != 0:
                validation_result["errors"].append(f"Target revision {target_revision} does not exist")
                validation_result["safe"] = False
                return validation_result
            
            # Get migration history between current and target
            result = self._run_alembic_command(["history", "-r", f"{target_revision}:{current_revision}"])
            if result.returncode == 0:
                history = result.stdout
                
                # Check for potentially destructive operations
                destructive_keywords = [
                    "drop_table", "drop_column", "alter_column", 
                    "drop_index", "drop_constraint"
                ]
                
                for keyword in destructive_keywords:
                    if keyword in history.lower():
                        validation_result["warnings"].append(
                            f"Potentially destructive operation detected: {keyword}"
                        )
                        validation_result["data_loss_risk"] = True
            
            # Check for data in tables that might be affected
            await init_database(create_tables=False)
            
            async with get_session() as session:
                # Check user count
                result = await session.execute(text("SELECT COUNT(*) FROM user WHERE is_deleted = 0"))
                user_count = result.scalar()
                
                if user_count > 0:
                    validation_result["warnings"].append(
                        f"Database contains {user_count} active users"
                    )
                
                # Check API key count
                result = await session.execute(text("SELECT COUNT(*) FROM api_key WHERE is_deleted = 0"))
                key_count = result.scalar()
                
                if key_count > 0:
                    validation_result["warnings"].append(
                        f"Database contains {key_count} active API keys"
                    )
                
                # Check active sessions
                result = await session.execute(text("""
                    SELECT COUNT(*) FROM user_session 
                    WHERE is_active = 1 AND expires_at > datetime('now')
                """))
                session_count = result.scalar()
                
                if session_count > 0:
                    validation_result["warnings"].append(
                        f"Database contains {session_count} active sessions"
                    )
            
            await close_database()
            
            # Production environment check
            if is_production():
                validation_result["warnings"].append("Running in PRODUCTION environment")
                if validation_result["data_loss_risk"]:
                    validation_result["errors"].append(
                        "Data loss risk detected in production environment"
                    )
                    validation_result["safe"] = False
            
            logger.info(f"Validation completed. Safe: {validation_result['safe']}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            validation_result["errors"].append(f"Validation error: {str(e)}")
            validation_result["safe"] = False
            return validation_result
    
    async def perform_rollback(
        self, 
        target_revision: str, 
        create_backup: bool = True,
        force: bool = False
    ) -> bool:
        """
        Perform database rollback with safety checks.
        
        Args:
            target_revision: Target revision to rollback to
            create_backup: Whether to create a backup before rollback
            force: Skip safety checks (dangerous!)
            
        Returns:
            True if rollback successful, False otherwise
        """
        logger.info(f"Starting rollback to revision: {target_revision}")
        
        try:
            # Validate rollback safety unless forced
            if not force:
                validation = await self.validate_rollback_safety(target_revision)
                
                if not validation["safe"]:
                    logger.error("Rollback validation failed:")
                    for error in validation["errors"]:
                        logger.error(f"  - {error}")
                    return False
                
                if validation["warnings"]:
                    logger.warning("Rollback warnings:")
                    for warning in validation["warnings"]:
                        logger.warning(f"  - {warning}")
                    
                    if is_production() or validation["data_loss_risk"]:
                        response = input("Continue with rollback despite warnings? (yes/no): ")
                        if response.lower() != "yes":
                            logger.info("Rollback cancelled by user")
                            return False
            
            # Create backup if requested
            backup_file = None
            if create_backup:
                backup_file = await self.create_data_backup()
                logger.info(f"Backup created: {backup_file}")
            
            # Perform the rollback
            logger.info("Executing rollback...")
            result = self._run_alembic_command(["downgrade", target_revision])
            
            if result.returncode != 0:
                logger.error(f"Rollback failed: {result.stderr}")
                if backup_file:
                    logger.info(f"Data backup available at: {backup_file}")
                return False
            
            logger.info("Rollback completed successfully")
            
            # Verify the rollback
            result = self._run_alembic_command(["current"])
            if result.returncode == 0:
                current_revision = result.stdout.strip()
                logger.info(f"Current revision after rollback: {current_revision}")
            
            if backup_file:
                logger.info(f"Backup file: {backup_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed with exception: {e}")
            return False
    
    def list_backups(self) -> List[Path]:
        """
        List available backup files.
        
        Returns:
            List of backup file paths
        """
        backups = list(self.backup_dir.glob("*.json"))
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return backups
    
    def show_backup_info(self, backup_file: Path) -> Dict:
        """
        Show information about a backup file.
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            Backup information dictionary
        """
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            info = {
                "file": str(backup_file),
                "timestamp": backup_data.get("timestamp"),
                "database": backup_data.get("database_url"),
                "tables": {}
            }
            
            for table_name, table_data in backup_data.get("tables", {}).items():
                info["tables"][table_name] = len(table_data) if isinstance(table_data, list) else "unknown"
            
            return info
            
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point for the rollback script."""
    parser = argparse.ArgumentParser(description="Database rollback management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Perform database rollback")
    rollback_parser.add_argument("revision", help="Target revision")
    rollback_parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    rollback_parser.add_argument("--force", action="store_true", help="Skip safety checks")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate rollback safety")
    validate_parser.add_argument("revision", help="Target revision")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create data backup")
    backup_parser.add_argument("--name", help="Custom backup name")
    
    # List backups command
    subparsers.add_parser("list-backups", help="List available backups")
    
    # Show backup command
    show_parser = subparsers.add_parser("show-backup", help="Show backup information")
    show_parser.add_argument("backup_file", help="Path to backup file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    manager = RollbackManager()
    
    try:
        if args.command == "rollback":
            success = await manager.perform_rollback(
                args.revision,
                create_backup=not args.no_backup,
                force=args.force
            )
            return 0 if success else 1
            
        elif args.command == "validate":
            validation = await manager.validate_rollback_safety(args.revision)
            
            print(f"Rollback validation for revision: {args.revision}")
            print(f"Safe: {validation['safe']}")
            print(f"Current revision: {validation['current_revision']}")
            print(f"Data loss risk: {validation['data_loss_risk']}")
            
            if validation["warnings"]:
                print("\nWarnings:")
                for warning in validation["warnings"]:
                    print(f"  - {warning}")
            
            if validation["errors"]:
                print("\nErrors:")
                for error in validation["errors"]:
                    print(f"  - {error}")
            
            return 0 if validation["safe"] else 1
            
        elif args.command == "backup":
            backup_file = await manager.create_data_backup(args.name)
            print(f"Backup created: {backup_file}")
            return 0
            
        elif args.command == "list-backups":
            backups = manager.list_backups()
            
            if not backups:
                print("No backups found")
                return 0
            
            print("Available backups:")
            for backup in backups:
                info = manager.show_backup_info(backup)
                timestamp = info.get("timestamp", "unknown")
                print(f"  {backup.name} - {timestamp}")
            
            return 0
            
        elif args.command == "show-backup":
            backup_file = Path(args.backup_file)
            info = manager.show_backup_info(backup_file)
            
            if "error" in info:
                print(f"Error reading backup: {info['error']}")
                return 1
            
            print(f"Backup: {info['file']}")
            print(f"Timestamp: {info['timestamp']}")
            print(f"Database: {info['database']}")
            print("Tables:")
            for table, count in info["tables"].items():
                print(f"  {table}: {count} records")
            
            return 0
            
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