#!/usr/bin/env python3
"""
Configuration management CLI utility.

This script provides command-line utilities for managing application configuration,
including validation, environment setup, and secrets management.

Usage:
    python scripts/config_manager.py validate
    python scripts/config_manager.py info
    python scripts/config_manager.py init-secrets
    python scripts/config_manager.py check-env [environment]
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Skip auto-initialization and validation for the config manager
os.environ["SKIP_CONFIG_INIT"] = "1"
os.environ["SKIP_CONFIG_VALIDATION"] = "1"

from config import (
    settings,
    validate_configuration,
    print_configuration_summary,
    print_environment_info,
    ConfigurationError,
    Environment,
    EnvironmentDetector,
    ConfigurationPaths,
)


def validate_config() -> int:
    """
    Validate the current configuration.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        print("Validating configuration...")
        validate_configuration()
        print("✅ Configuration is valid")
        return 0
    except ConfigurationError as e:
        print(f"❌ Configuration validation failed: {e}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}")
        return 1


def show_info() -> int:
    """
    Show detailed configuration information.
    
    Returns:
        Exit code (always 0)
    """
    print("=== Configuration Information ===\n")
    
    # Environment information
    print_environment_info()
    
    print("\n" + "="*50 + "\n")
    
    # Configuration summary (create settings without validation)
    try:
        from dynaconf import Dynaconf
        from config.settings import CONFIG_DIR, SETTINGS_FILES, get_environment
        
        # Create settings without validators for info display
        info_settings = Dynaconf(
            envvar_prefix="API",
            environments=True,
            env=get_environment(),
            settings_files=SETTINGS_FILES,
            secrets=CONFIG_DIR / ".secrets.toml",
            load_dotenv=True,
            validators=[],  # No validators for info display
        )
        
        print("=== Configuration Summary ===")
        print(f"Environment: {info_settings.get('env', 'unknown')}")
        print(f"Debug mode: {info_settings.get('debug', 'unknown')}")
        print(f"App name: {info_settings.get('app_name', 'unknown')}")
        print(f"Version: {info_settings.get('version', 'unknown')}")
        print(f"Host: {info_settings.get('host', 'unknown')}:{info_settings.get('port', 'unknown')}")
        
        db_url = info_settings.get('database_url', 'Not configured')
        if '@' in str(db_url):
            db_display = db_url.split('@')[-1]
        else:
            db_display = 'Not configured'
        print(f"Database: {db_display}")
        
        print(f"Redis: {info_settings.get('redis_url', 'Not configured')}")
        print(f"Log level: {info_settings.get('log_level', 'unknown')}")
        print(f"Metrics enabled: {info_settings.get('metrics_enabled', 'unknown')}")
        
    except Exception as e:
        print(f"Error displaying configuration summary: {e}")
    
    return 0


def init_secrets() -> int:
    """
    Initialize secrets file from template.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    paths = ConfigurationPaths()
    
    if paths.secrets_file.exists():
        response = input(f"Secrets file already exists at {paths.secrets_file}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0
    
    if not paths.secrets_example_file.exists():
        print(f"❌ Secrets template not found at {paths.secrets_example_file}")
        return 1
    
    try:
        # Copy template to secrets file
        shutil.copy2(paths.secrets_example_file, paths.secrets_file)
        print(f"✅ Created secrets file at {paths.secrets_file}")
        print("⚠️  Remember to update the secrets with your actual values!")
        print("⚠️  Never commit .secrets.toml to version control!")
        
        # Set restrictive permissions on Unix systems
        if os.name != 'nt':  # Not Windows
            os.chmod(paths.secrets_file, 0o600)
            print("✅ Set restrictive permissions (600) on secrets file")
        
        return 0
    except Exception as e:
        print(f"❌ Failed to create secrets file: {e}")
        return 1


def check_environment(env_name: str = None) -> int:
    """
    Check environment-specific configuration.
    
    Args:
        env_name: Environment to check (current environment if not specified)
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if env_name:
        try:
            target_env = Environment(env_name.lower())
        except ValueError:
            print(f"❌ Invalid environment: {env_name}")
            print(f"Valid environments: {', '.join([e.value for e in Environment])}")
            return 1
    else:
        target_env = EnvironmentDetector.detect_environment()
    
    print(f"Checking configuration for environment: {target_env.value}")
    
    # Set environment variable temporarily
    original_env = os.getenv("API_ENV")
    os.environ["API_ENV"] = target_env.value
    
    try:
        # Skip auto-initialization to avoid conflicts
        os.environ["SKIP_CONFIG_INIT"] = "1"
        os.environ["SKIP_CONFIG_VALIDATION"] = "1"
        
        # Re-import to get fresh configuration
        from importlib import reload
        import config.settings
        reload(config.settings)
        
        # Validate configuration for target environment
        config.settings.validate_configuration()
        print(f"✅ Configuration is valid for {target_env.value}")
        
        # Show environment-specific summary
        print(f"\n=== {target_env.value.title()} Configuration Summary ===")
        config.settings.print_configuration_summary()
        
        return 0
        
    except ConfigurationError as e:
        print(f"❌ Configuration invalid for {target_env.value}: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error checking {target_env.value} configuration: {e}")
        return 1
    finally:
        # Restore original environment
        if original_env:
            os.environ["API_ENV"] = original_env
        else:
            os.environ.pop("API_ENV", None)
        
        # Clean up temporary environment variables
        os.environ.pop("SKIP_CONFIG_INIT", None)
        os.environ.pop("SKIP_CONFIG_VALIDATION", None)


def create_env_file() -> int:
    """
    Create .env file from .env.example template.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    paths = ConfigurationPaths()
    
    if paths.env_file.exists():
        response = input(f".env file already exists at {paths.env_file}. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return 0
    
    if not paths.env_example_file.exists():
        print(f"❌ .env.example template not found at {paths.env_example_file}")
        return 1
    
    try:
        # Copy template to .env file
        shutil.copy2(paths.env_example_file, paths.env_file)
        print(f"✅ Created .env file at {paths.env_file}")
        print("⚠️  Remember to update the values in .env for your environment!")
        return 0
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Configuration management utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/config_manager.py validate
  python scripts/config_manager.py info
  python scripts/config_manager.py init-secrets
  python scripts/config_manager.py init-env
  python scripts/config_manager.py check-env production
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validate command
    subparsers.add_parser("validate", help="Validate current configuration")
    
    # Info command
    subparsers.add_parser("info", help="Show configuration information")
    
    # Init secrets command
    subparsers.add_parser("init-secrets", help="Initialize secrets file from template")
    
    # Init env command
    subparsers.add_parser("init-env", help="Initialize .env file from template")
    
    # Check environment command
    check_parser = subparsers.add_parser("check-env", help="Check environment-specific configuration")
    check_parser.add_argument("environment", nargs="?", help="Environment to check (current if not specified)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    if args.command == "validate":
        return validate_config()
    elif args.command == "info":
        return show_info()
    elif args.command == "init-secrets":
        return init_secrets()
    elif args.command == "init-env":
        return create_env_file()
    elif args.command == "check-env":
        return check_environment(args.environment)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())