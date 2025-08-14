"""
Configuration management module.

This module provides centralized configuration management for the application
using Dynaconf with support for environment-specific settings, secrets management,
and configuration validation.

Usage:
    from src.config import settings

    # Access configuration values
    app_name = settings.app_name
    database_url = settings.database_url

    # Use helper functions
    from src.config import get_database_url, is_production

    db_url = get_database_url()
    if is_production():
        # Production-specific logic
        pass
"""

from .settings import (
    settings,
    ConfigurationError,
    validate_configuration,
    get_database_url,
    get_redis_url,
    is_development,
    is_production,
    is_testing,
    get_cors_config,
    get_logging_config,
    get_jwt_config,
    get_feature_flags,
    print_configuration_summary,
)

from .environment import (
    Environment,
    EnvironmentDetector,
    ConfigurationPaths,
    print_environment_info,
)

# Create convenience function for get_environment
def get_environment() -> Environment:
    """Get the current environment."""
    return EnvironmentDetector.detect_environment()

# Export commonly used items
__all__ = [
    # Main settings object
    "settings",

    # Exception classes
    "ConfigurationError",

    # Validation functions
    "validate_configuration",

    # Helper functions
    "get_database_url",
    "get_redis_url",
    "is_development",
    "is_production",
    "is_testing",
    "get_cors_config",
    "get_logging_config",
    "get_jwt_config",
    "get_feature_flags",
    "get_environment",

    # Debug functions
    "print_configuration_summary",
    "print_environment_info",

    # Environment classes
    "Environment",
    "EnvironmentDetector",
    "ConfigurationPaths",
]


def initialize_configuration() -> None:
    """
    Initialize and validate the configuration system.

    This function should be called early in the application startup
    to ensure configuration is properly loaded and validated.

    Raises:
        ConfigurationError: If configuration validation fails
    """
    try:
        # Validate configuration
        validate_configuration()

        # Print configuration summary in development
        if is_development():
            print("Configuration loaded successfully")
            print_configuration_summary()

    except ConfigurationError as e:
        print(f"Configuration initialization failed: {e}")
        if is_production():
            # In production, fail fast on configuration errors
            raise
        else:
            # In development, warn but continue
            print("Warning: Continuing with potentially invalid configuration")


# Auto-initialize configuration when module is imported
# This can be disabled by setting SKIP_CONFIG_INIT environment variable
import os
if not os.getenv("SKIP_CONFIG_INIT"):
    try:
        initialize_configuration()
    except Exception as e:
        print(f"Warning: Configuration initialization failed: {e}")
        if not is_development():
            raise
