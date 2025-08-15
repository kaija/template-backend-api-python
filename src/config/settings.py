"""
Configuration management using Dynaconf.

This module provides centralized configuration management with support for:
- Environment-specific settings
- Hierarchical configuration loading
- Secure secrets management
- Configuration validation
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dynaconf import Dynaconf, Validator

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Configuration file paths
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_FILES = [
    CONFIG_DIR / "settings.toml",
    CONFIG_DIR / "environments" / "{env}.toml",
]

# Import environment detection
from .environment import EnvironmentDetector

# Environment detection
def get_environment() -> str:
    """
    Detect the current environment using the EnvironmentDetector.

    Returns:
        Current environment name
    """
    return EnvironmentDetector.detect_environment().value

# Dynaconf settings instance
settings = Dynaconf(
    # Environment settings
    envvar_prefix="API",
    environments=True,
    env=get_environment(),

    # Configuration files
    settings_files=SETTINGS_FILES,

    # Secrets file (optional, for sensitive data)
    secrets=CONFIG_DIR / ".secrets.toml",

    # Environment variables
    load_dotenv=True,
    dotenv_path=PROJECT_ROOT / ".env",

    # Validation
    validators=[
        # Application settings
        Validator("app_name", must_exist=True, is_type_of=str),
        Validator("version", must_exist=True, is_type_of=str),
        Validator("debug", must_exist=True, is_type_of=bool),

        # Server settings
        Validator("host", must_exist=True, is_type_of=str),
        Validator("port", must_exist=True, is_type_of=int, gte=1, lte=65535),

        # API settings
        Validator("api_prefix", must_exist=True, is_type_of=str),
        Validator("version_prefix", must_exist=True, is_type_of=str),

        # Database settings
        # Note: database_url validation is handled separately for test environment
        Validator("db_pool_size", must_exist=True, is_type_of=int, gte=1),
        Validator("db_max_overflow", must_exist=True, is_type_of=int, gte=0),
        Validator("db_pool_timeout", must_exist=True, is_type_of=int, gte=1),
        Validator("db_pool_recycle", must_exist=True, is_type_of=int, gte=1),

        # Redis settings
        Validator("redis_url", must_exist=True, is_type_of=str),
        Validator("redis_max_connections", must_exist=True, is_type_of=int, gte=1),
        Validator("redis_retry_on_timeout", must_exist=True, is_type_of=bool),

        # Security settings
        Validator("secret_key", must_exist=True, is_type_of=str, len_min=32),
        Validator("access_token_expire_minutes", must_exist=True, is_type_of=int, gte=1),
        Validator("refresh_token_expire_days", must_exist=True, is_type_of=int, gte=1),
        Validator("algorithm", must_exist=True, is_type_of=str),

        # CORS settings
        Validator("cors_origins", must_exist=True, is_type_of=list),
        Validator("cors_allow_credentials", must_exist=True, is_type_of=bool),
        Validator("cors_allow_methods", must_exist=True, is_type_of=list),
        Validator("cors_allow_headers", must_exist=True, is_type_of=list),

        # Logging settings
        Validator("log_level", must_exist=True, is_type_of=str, is_in=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
        Validator("log_format", must_exist=True, is_type_of=str, is_in=["json", "console"]),

        # Monitoring settings
        Validator("metrics_enabled", must_exist=True, is_type_of=bool),
        Validator("metrics_path", must_exist=True, is_type_of=str),

        # Rate limiting
        Validator("rate_limit_enabled", must_exist=True, is_type_of=bool),
        Validator("rate_limit_requests", must_exist=True, is_type_of=int, gte=1),
        Validator("rate_limit_window", must_exist=True, is_type_of=int, gte=1),

        # Health checks
        Validator("health_check_path", must_exist=True, is_type_of=str),
        Validator("readiness_check_path", must_exist=True, is_type_of=str),
        Validator("health_check_timeout", must_exist=True, is_type_of=int, gte=1),

        # Performance settings
        Validator("request_timeout", must_exist=True, is_type_of=int, gte=1),
        Validator("max_request_size", must_exist=True, is_type_of=int, gte=1),
        Validator("workers", must_exist=True, is_type_of=int, gte=1),
        Validator("worker_connections", must_exist=True, is_type_of=int, gte=1),

        # Shutdown settings
        Validator("shutdown_timeout", must_exist=True, is_type_of=int, gte=5, lte=300),
        Validator("shutdown_wait_for_connections", must_exist=True, is_type_of=bool),
        Validator("shutdown_force_after_timeout", must_exist=True, is_type_of=bool),
    ]
)


class ConfigurationError(Exception):
    """Raised when configuration validation fails."""
    pass


def validate_configuration() -> None:
    """
    Validate the current configuration.

    Raises:
        ConfigurationError: If configuration validation fails.
    """
    try:
        # Trigger validation by accessing a required setting
        _ = settings.app_name

        # Additional custom validations

        # Get current environment
        current_env = get_environment()

        # Database URL validation (not required for test environment)
        if current_env != "test":
            try:
                database_url = getattr(settings, "database_url", None)
                if not database_url:
                    raise ConfigurationError("Database URL is required for non-test environments")
                if not isinstance(database_url, str):
                    raise ConfigurationError("Database URL must be a string")
            except AttributeError:
                raise ConfigurationError("Database URL is required for non-test environments")

        if current_env == "production":
            # Production-specific validations
            debug_mode = getattr(settings, "debug", False)
            if debug_mode:
                raise ConfigurationError("Debug mode should be disabled in production")

            secret_key = getattr(settings, "secret_key", "")
            if secret_key == "your-super-secret-key-change-this-in-production":
                raise ConfigurationError("Default secret key detected in production")

            sentry_dsn = getattr(settings, "sentry_dsn", None)
            if not sentry_dsn:
                raise ConfigurationError("Sentry DSN is required in production")

        # Validate CORS origins format
        for origin in settings.cors_origins:
            if not isinstance(origin, str):
                raise ConfigurationError(f"Invalid CORS origin format: {origin}")

    except Exception as e:
        raise ConfigurationError(f"Configuration validation failed: {str(e)}")


def get_database_url(for_testing: bool = False) -> str:
    """
    Get the database URL for the current environment.

    Args:
        for_testing: If True, return the test database URL

    Returns:
        Database connection URL
    """
    if for_testing:
        return settings.get("test_database_url", settings.database_url.replace("/api_", "/api_test_"))

    return settings.database_url


def get_redis_url() -> str:
    """
    Get the Redis URL for the current environment.

    Returns:
        Redis connection URL
    """
    return settings.redis_url


def is_development() -> bool:
    """Check if running in development environment."""
    return get_environment() == "development"


def is_production() -> bool:
    """Check if running in production environment."""
    return get_environment() == "production"


def is_testing() -> bool:
    """Check if running in test environment."""
    return get_environment() == "test"


def get_cors_config() -> Dict[str, Any]:
    """
    Get CORS configuration as a dictionary.

    Returns:
        CORS configuration dictionary
    """
    return {
        "allow_origins": settings.cors_origins,
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
    }


def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration as a dictionary.

    Returns:
        Logging configuration dictionary
    """
    return {
        "level": settings.log_level,
        "format": settings.log_format,
        "file": settings.get("log_file"),
    }


def get_jwt_config() -> Dict[str, Any]:
    """
    Get JWT configuration as a dictionary.

    Returns:
        JWT configuration dictionary
    """
    return {
        "secret_key": settings.secret_key,
        "algorithm": settings.algorithm,
        "access_token_expire_minutes": settings.access_token_expire_minutes,
        "refresh_token_expire_days": settings.refresh_token_expire_days,
    }


def get_feature_flags() -> Dict[str, bool]:
    """
    Get all feature flags as a dictionary.

    Returns:
        Feature flags dictionary
    """
    return {
        "registration_enabled": settings.get("feature_registration_enabled", True),
        "email_verification": settings.get("feature_email_verification", False),
        "social_login": settings.get("feature_social_login", False),
    }


def print_configuration_summary() -> None:
    """Print a summary of the current configuration (for debugging)."""
    print(f"Environment: {get_environment()}")
    print(f"Debug mode: {getattr(settings, 'debug', False)}")
    print(f"App name: {getattr(settings, 'app_name', 'Unknown')}")
    print(f"Version: {getattr(settings, 'version', 'Unknown')}")
    print(f"Host: {getattr(settings, 'host', 'localhost')}:{getattr(settings, 'port', 8000)}")
    database_url = getattr(settings, 'database_url', 'Not configured')
    print(f"Database: {database_url.split('@')[-1] if '@' in database_url else 'Not configured'}")
    print(f"Redis: {getattr(settings, 'redis_url', 'Not configured')}")
    print(f"Log level: {settings.log_level}")
    print(f"Metrics enabled: {settings.metrics_enabled}")


# Validate configuration on import (can be disabled for testing)
if not os.getenv("SKIP_CONFIG_VALIDATION"):
    try:
        validate_configuration()
    except ConfigurationError as e:
        print(f"Configuration Error: {e}")
        if not is_development():
            raise


def apply_deployment_overrides_to_settings():
    """Apply deployment-specific overrides to settings after initialization."""
    try:
        from .deployment import apply_deployment_overrides
        deployment_overrides = apply_deployment_overrides()

        # Apply overrides to settings
        for key, value in deployment_overrides.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        # Validate deployment configuration (skip for test environment)
        if get_environment() != "test":
            from .deployment import validate_deployment
            deployment_validation = validate_deployment()
            if not deployment_validation["valid"]:
                error_msg = f"Deployment validation failed: {', '.join(deployment_validation['errors'])}"
                print(f"Deployment Configuration Error: {error_msg}")
                if not is_development():
                    raise ConfigurationError(error_msg)

    except ImportError:
        # Deployment module not available, skip overrides
        pass


# Apply deployment overrides after settings initialization
apply_deployment_overrides_to_settings()
