"""
Environment detection and configuration utilities.

This module provides utilities for detecting the current environment
and managing environment-specific configurations.
"""

import os
import sys
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional


class Environment(str, Enum):
    """Supported application environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class EnvironmentDetector:
    """Utility class for environment detection and validation."""

    @staticmethod
    def detect_environment() -> Environment:
        """
        Detect the current environment from various sources.

        Detection priority:
        1. API_ENV environment variable
        2. ENV environment variable
        3. ENVIRONMENT environment variable
        4. Check if running in pytest (test environment)
        5. Default to development

        Returns:
            Detected environment
        """
        # Check environment variables
        env_vars = ["API_ENV", "ENV", "ENVIRONMENT"]
        for var in env_vars:
            env_value = os.getenv(var)
            if env_value:
                env_value = env_value.lower().strip()
                try:
                    return Environment(env_value)
                except ValueError:
                    print(f"Warning: Invalid environment value '{env_value}' in {var}")

        # Check if running in pytest
        if "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
            return Environment.TEST

        # Default to development
        return Environment.DEVELOPMENT

    @staticmethod
    def is_development() -> bool:
        """Check if running in development environment."""
        return EnvironmentDetector.detect_environment() == Environment.DEVELOPMENT

    @staticmethod
    def is_staging() -> bool:
        """Check if running in staging environment."""
        return EnvironmentDetector.detect_environment() == Environment.STAGING

    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment."""
        return EnvironmentDetector.detect_environment() == Environment.PRODUCTION

    @staticmethod
    def is_testing() -> bool:
        """Check if running in test environment."""
        return EnvironmentDetector.detect_environment() == Environment.TEST

    @staticmethod
    def validate_environment_setup() -> Dict[str, Any]:
        """
        Validate the current environment setup.

        Returns:
            Dictionary with validation results
        """
        env = EnvironmentDetector.detect_environment()
        results = {
            "environment": env.value,
            "valid": True,
            "warnings": [],
            "errors": [],
        }

        # Check for required environment variables based on environment
        required_vars = {
            Environment.DEVELOPMENT: [],
            Environment.STAGING: [],
            Environment.PRODUCTION: [],
            Environment.TEST: [],
        }

        for var in required_vars.get(env, []):
            if not os.getenv(var):
                results["errors"].append(f"Missing required environment variable: {var}")
                results["valid"] = False

        # Environment-specific validations
        if env == Environment.PRODUCTION:
            # Production-specific checks
            debug_mode = os.getenv("API_DEBUG", "false").lower()
            if debug_mode in ("true", "1", "yes"):
                results["errors"].append("Debug mode should be disabled in production")
                results["valid"] = False

            secret_key = os.getenv("API_SECRET_KEY", "")
            if secret_key == "your-super-secret-key-change-this-in-production":
                results["errors"].append("Default secret key detected in production")
                results["valid"] = False

            if len(secret_key) < 32:
                results["errors"].append("Secret key should be at least 32 characters in production")
                results["valid"] = False

        elif env == Environment.DEVELOPMENT:
            # Development-specific warnings
            if not os.path.exists(".env"):
                results["warnings"].append("No .env file found - using default configuration")

            if not os.path.exists("config/.secrets.toml"):
                results["warnings"].append("No .secrets.toml file found - using environment variables only")

        return results


class ConfigurationPaths:
    """Utility class for managing configuration file paths."""

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize configuration paths.

        Args:
            project_root: Project root directory (auto-detected if not provided)
        """
        if project_root is None:
            # Auto-detect project root (assuming this file is in src/config/)
            self.project_root = Path(__file__).parent.parent.parent
        else:
            self.project_root = project_root

        self.config_dir = self.project_root / "config"
        self.src_dir = self.project_root / "src"

    @property
    def settings_file(self) -> Path:
        """Path to the main settings file."""
        return self.config_dir / "settings.toml"

    @property
    def secrets_file(self) -> Path:
        """Path to the secrets file."""
        return self.config_dir / ".secrets.toml"

    @property
    def secrets_example_file(self) -> Path:
        """Path to the secrets example file."""
        return self.config_dir / ".secrets.toml.example"

    @property
    def env_file(self) -> Path:
        """Path to the .env file."""
        return self.project_root / ".env"

    @property
    def env_example_file(self) -> Path:
        """Path to the .env.example file."""
        return self.project_root / ".env.example"

    def environment_file(self, environment: Environment) -> Path:
        """
        Get the path to an environment-specific configuration file.

        Args:
            environment: Target environment

        Returns:
            Path to the environment configuration file
        """
        return self.config_dir / "environments" / f"{environment.value}.toml"

    def validate_paths(self) -> Dict[str, Any]:
        """
        Validate that required configuration files exist.

        Returns:
            Dictionary with validation results
        """
        results = {
            "valid": True,
            "missing_files": [],
            "warnings": [],
        }

        # Check required files
        required_files = [
            ("settings.toml", self.settings_file),
            (".env.example", self.env_example_file),
        ]

        for name, path in required_files:
            if not path.exists():
                results["missing_files"].append(name)
                results["valid"] = False

        # Check optional but recommended files
        optional_files = [
            (".env", self.env_file),
            (".secrets.toml", self.secrets_file),
        ]

        for name, path in optional_files:
            if not path.exists():
                results["warnings"].append(f"Optional file missing: {name}")

        # Check environment-specific files
        current_env = EnvironmentDetector.detect_environment()
        env_file = self.environment_file(current_env)
        if not env_file.exists():
            results["warnings"].append(f"Environment file missing: {env_file.name}")

        return results


def print_environment_info() -> None:
    """Print detailed environment information for debugging."""
    detector = EnvironmentDetector()
    paths = ConfigurationPaths()

    print("=== Environment Information ===")
    print(f"Detected environment: {detector.detect_environment().value}")
    print(f"Project root: {paths.project_root}")
    print(f"Config directory: {paths.config_dir}")

    print("\n=== Environment Variables ===")
    env_vars = ["API_ENV", "ENV", "ENVIRONMENT", "API_DEBUG"]
    for var in env_vars:
        value = os.getenv(var, "Not set")
        # Mask sensitive values
        if "secret" in var.lower() or "password" in var.lower() or "key" in var.lower():
            value = "***MASKED***" if value != "Not set" else value
        print(f"{var}: {value}")

    print("\n=== Environment Validation ===")
    validation = detector.validate_environment_setup()
    print(f"Valid: {validation['valid']}")

    if validation["warnings"]:
        print("Warnings:")
        for warning in validation["warnings"]:
            print(f"  - {warning}")

    if validation["errors"]:
        print("Errors:")
        for error in validation["errors"]:
            print(f"  - {error}")

    print("\n=== Configuration Files ===")
    path_validation = paths.validate_paths()
    print(f"All required files present: {path_validation['valid']}")

    if path_validation["missing_files"]:
        print("Missing required files:")
        for file in path_validation["missing_files"]:
            print(f"  - {file}")

    if path_validation["warnings"]:
        print("File warnings:")
        for warning in path_validation["warnings"]:
            print(f"  - {warning}")


if __name__ == "__main__":
    # Allow running this module directly for environment debugging
    print_environment_info()
