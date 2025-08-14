"""
Deployment configuration management.

This module provides utilities for managing deployment-specific configurations,
validation, and environment variable overrides for different deployment scenarios.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

from .environment import Environment, EnvironmentDetector


class DeploymentType(str, Enum):
    """Supported deployment types."""
    LOCAL = "local"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    SERVERLESS = "serverless"
    CLOUD_RUN = "cloud_run"
    ECS = "ecs"
    HEROKU = "heroku"


@dataclass
class DeploymentConfig:
    """Configuration for a specific deployment scenario."""
    
    # Basic deployment info
    deployment_type: DeploymentType
    environment: Environment
    
    # Required environment variables
    required_env_vars: List[str] = field(default_factory=list)
    
    # Optional environment variables with defaults
    optional_env_vars: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration overrides
    config_overrides: Dict[str, Any] = field(default_factory=dict)
    
    # Validation rules
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    
    # Health check configuration
    health_check_enabled: bool = True
    readiness_check_enabled: bool = True
    
    # Resource limits and requirements
    resource_requirements: Dict[str, Any] = field(default_factory=dict)


class DeploymentConfigManager:
    """Manages deployment-specific configurations and validation."""
    
    def __init__(self):
        """Initialize the deployment configuration manager."""
        self.current_environment = EnvironmentDetector.detect_environment()
        self.deployment_type = self._detect_deployment_type()
        self.deployment_configs = self._load_deployment_configs()
    
    def _detect_deployment_type(self) -> DeploymentType:
        """
        Detect the current deployment type based on environment indicators.
        
        Returns:
            Detected deployment type
        """
        # Check for Kubernetes
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            return DeploymentType.KUBERNETES
        
        # Check for Docker
        if os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER"):
            return DeploymentType.DOCKER
        
        # Check for Cloud Run
        if os.getenv("K_SERVICE") or os.getenv("GOOGLE_CLOUD_PROJECT"):
            return DeploymentType.CLOUD_RUN
        
        # Check for ECS
        if os.getenv("AWS_EXECUTION_ENV") == "AWS_ECS_FARGATE" or os.getenv("ECS_CONTAINER_METADATA_URI"):
            return DeploymentType.ECS
        
        # Check for Heroku
        if os.getenv("DYNO") or os.getenv("HEROKU_APP_NAME"):
            return DeploymentType.HEROKU
        
        # Check for serverless (AWS Lambda, etc.)
        if os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("LAMBDA_RUNTIME_DIR"):
            return DeploymentType.SERVERLESS
        
        # Default to local
        return DeploymentType.LOCAL
    
    def _load_deployment_configs(self) -> Dict[str, DeploymentConfig]:
        """
        Load deployment configurations for different scenarios.
        
        Returns:
            Dictionary of deployment configurations
        """
        configs = {}
        
        # Local development configuration
        configs["local_development"] = DeploymentConfig(
            deployment_type=DeploymentType.LOCAL,
            environment=Environment.DEVELOPMENT,
            required_env_vars=[
                "API_DATABASE_URL",
                "API_SECRET_KEY",
            ],
            optional_env_vars={
                "API_REDIS_URL": "redis://localhost:6379/0",
                "API_DEBUG": True,
                "API_LOG_LEVEL": "DEBUG",
            },
            config_overrides={
                "debug": True,
                "reload": True,
                "workers": 1,
            },
            validation_rules={
                "min_secret_key_length": 32,
                "allow_debug": True,
            }
        )
        
        # Docker development configuration
        configs["docker_development"] = DeploymentConfig(
            deployment_type=DeploymentType.DOCKER,
            environment=Environment.DEVELOPMENT,
            required_env_vars=[
                "API_DATABASE_URL",
                "API_SECRET_KEY",
                "API_REDIS_URL",
            ],
            optional_env_vars={
                "API_DEBUG": True,
                "API_LOG_LEVEL": "INFO",
                "API_HOST": "0.0.0.0",
                "API_PORT": 8000,
            },
            config_overrides={
                "host": "0.0.0.0",
                "workers": 1,
            },
            health_check_enabled=True,
            readiness_check_enabled=True,
        )
        
        # Docker staging configuration
        configs["docker_staging"] = DeploymentConfig(
            deployment_type=DeploymentType.DOCKER,
            environment=Environment.STAGING,
            required_env_vars=[
                "API_DATABASE_URL",
                "API_SECRET_KEY",
                "API_REDIS_URL",
                "API_SENTRY_DSN",
            ],
            optional_env_vars={
                "API_DEBUG": False,
                "API_LOG_LEVEL": "INFO",
                "API_HOST": "0.0.0.0",
                "API_PORT": 8000,
                "API_WORKERS": 2,
            },
            config_overrides={
                "debug": False,
                "host": "0.0.0.0",
                "workers": 2,
                "log_format": "json",
            },
            validation_rules={
                "min_secret_key_length": 32,
                "allow_debug": False,
                "require_sentry": True,
            },
            resource_requirements={
                "memory_limit": "512Mi",
                "cpu_limit": "500m",
                "memory_request": "256Mi",
                "cpu_request": "250m",
            }
        )
        
        # Docker production configuration
        configs["docker_production"] = DeploymentConfig(
            deployment_type=DeploymentType.DOCKER,
            environment=Environment.PRODUCTION,
            required_env_vars=[
                "API_DATABASE_URL",
                "API_SECRET_KEY",
                "API_REDIS_URL",
                "API_SENTRY_DSN",
            ],
            optional_env_vars={
                "API_DEBUG": False,
                "API_LOG_LEVEL": "WARNING",
                "API_HOST": "0.0.0.0",
                "API_PORT": 8000,
                "API_WORKERS": 4,
            },
            config_overrides={
                "debug": False,
                "host": "0.0.0.0",
                "workers": 4,
                "log_format": "json",
                "log_level": "WARNING",
            },
            validation_rules={
                "min_secret_key_length": 64,
                "allow_debug": False,
                "require_sentry": True,
                "require_https": True,
            },
            resource_requirements={
                "memory_limit": "1Gi",
                "cpu_limit": "1000m",
                "memory_request": "512Mi",
                "cpu_request": "500m",
            }
        )
        
        # Kubernetes production configuration
        configs["kubernetes_production"] = DeploymentConfig(
            deployment_type=DeploymentType.KUBERNETES,
            environment=Environment.PRODUCTION,
            required_env_vars=[
                "API_DATABASE_URL",
                "API_SECRET_KEY",
                "API_REDIS_URL",
                "API_SENTRY_DSN",
            ],
            optional_env_vars={
                "API_DEBUG": False,
                "API_LOG_LEVEL": "WARNING",
                "API_HOST": "0.0.0.0",
                "API_PORT": 8000,
                "API_WORKERS": 4,
                "API_SHUTDOWN_TIMEOUT": 30,
            },
            config_overrides={
                "debug": False,
                "host": "0.0.0.0",
                "workers": 4,
                "log_format": "json",
                "log_level": "WARNING",
                "shutdown_timeout": 30,
            },
            validation_rules={
                "min_secret_key_length": 64,
                "allow_debug": False,
                "require_sentry": True,
                "require_https": True,
                "require_health_checks": True,
            },
            health_check_enabled=True,
            readiness_check_enabled=True,
            resource_requirements={
                "memory_limit": "1Gi",
                "cpu_limit": "1000m",
                "memory_request": "512Mi",
                "cpu_request": "500m",
            }
        )
        
        # Cloud Run configuration
        configs["cloud_run_production"] = DeploymentConfig(
            deployment_type=DeploymentType.CLOUD_RUN,
            environment=Environment.PRODUCTION,
            required_env_vars=[
                "API_DATABASE_URL",
                "API_SECRET_KEY",
                "API_REDIS_URL",
                "API_SENTRY_DSN",
                "PORT",  # Cloud Run specific
            ],
            optional_env_vars={
                "API_DEBUG": False,
                "API_LOG_LEVEL": "INFO",
                "API_HOST": "0.0.0.0",
                "API_WORKERS": 1,  # Cloud Run handles scaling
            },
            config_overrides={
                "debug": False,
                "host": "0.0.0.0",
                "port": lambda: int(os.getenv("PORT", "8080")),
                "workers": 1,
                "log_format": "json",
            },
            validation_rules={
                "min_secret_key_length": 64,
                "allow_debug": False,
                "require_sentry": True,
            },
            resource_requirements={
                "memory_limit": "1Gi",
                "cpu_limit": "1000m",
                "concurrency": 100,
            }
        )
        
        # Heroku configuration
        configs["heroku_production"] = DeploymentConfig(
            deployment_type=DeploymentType.HEROKU,
            environment=Environment.PRODUCTION,
            required_env_vars=[
                "DATABASE_URL",  # Heroku provides this
                "API_SECRET_KEY",
                "REDIS_URL",  # Heroku Redis addon
                "API_SENTRY_DSN",
                "PORT",  # Heroku specific
            ],
            optional_env_vars={
                "API_DEBUG": False,
                "API_LOG_LEVEL": "INFO",
                "API_HOST": "0.0.0.0",
                "API_WORKERS": 2,
            },
            config_overrides={
                "debug": False,
                "host": "0.0.0.0",
                "port": lambda: int(os.getenv("PORT", "8000")),
                "database_url": lambda: os.getenv("DATABASE_URL", "").replace("postgres://", "postgresql+asyncpg://"),
                "redis_url": lambda: os.getenv("REDIS_URL"),
                "workers": 2,
                "log_format": "json",
            },
            validation_rules={
                "min_secret_key_length": 64,
                "allow_debug": False,
                "require_sentry": True,
            }
        )
        
        return configs
    
    def get_current_config(self) -> Optional[DeploymentConfig]:
        """
        Get the deployment configuration for the current environment.
        
        Returns:
            Current deployment configuration or None if not found
        """
        # Try to find exact match first
        config_key = f"{self.deployment_type.value}_{self.current_environment.value}"
        if config_key in self.deployment_configs:
            return self.deployment_configs[config_key]
        
        # Try to find by deployment type
        for key, config in self.deployment_configs.items():
            if (config.deployment_type == self.deployment_type and 
                config.environment == self.current_environment):
                return config
        
        # Fallback to local development
        return self.deployment_configs.get("local_development")
    
    def validate_deployment_config(self, config: Optional[DeploymentConfig] = None) -> Dict[str, Any]:
        """
        Validate the deployment configuration.
        
        Args:
            config: Configuration to validate (uses current if not provided)
            
        Returns:
            Validation results dictionary
        """
        if config is None:
            config = self.get_current_config()
        
        if config is None:
            return {
                "valid": False,
                "errors": ["No deployment configuration found"],
                "warnings": [],
            }
        
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "deployment_type": config.deployment_type.value,
            "environment": config.environment.value,
        }
        
        # Check required environment variables
        for var in config.required_env_vars:
            if not os.getenv(var):
                results["errors"].append(f"Missing required environment variable: {var}")
                results["valid"] = False
        
        # Apply validation rules
        for rule, value in config.validation_rules.items():
            if rule == "min_secret_key_length":
                secret_key = os.getenv("API_SECRET_KEY", "")
                if len(secret_key) < value:
                    results["errors"].append(f"Secret key must be at least {value} characters")
                    results["valid"] = False
            
            elif rule == "allow_debug":
                debug_mode = os.getenv("API_DEBUG", "false").lower() in ("true", "1", "yes")
                if debug_mode and not value:
                    results["errors"].append("Debug mode is not allowed in this environment")
                    results["valid"] = False
            
            elif rule == "require_sentry":
                if value and not os.getenv("API_SENTRY_DSN"):
                    results["errors"].append("Sentry DSN is required for this environment")
                    results["valid"] = False
            
            elif rule == "require_https":
                if value:
                    # This would be checked by reverse proxy/load balancer
                    results["warnings"].append("Ensure HTTPS is configured at the load balancer level")
            
            elif rule == "require_health_checks":
                if value and not (config.health_check_enabled and config.readiness_check_enabled):
                    results["warnings"].append("Health checks should be enabled for this deployment")
        
        # Check optional environment variables and provide defaults
        for var, default_value in config.optional_env_vars.items():
            if not os.getenv(var):
                results["warnings"].append(f"Optional environment variable {var} not set, using default: {default_value}")
        
        return results
    
    def apply_deployment_overrides(self, config: Optional[DeploymentConfig] = None) -> Dict[str, Any]:
        """
        Apply deployment-specific configuration overrides.
        
        Args:
            config: Configuration to apply (uses current if not provided)
            
        Returns:
            Dictionary of configuration overrides
        """
        if config is None:
            config = self.get_current_config()
        
        if config is None:
            return {}
        
        overrides = {}
        
        # Apply static overrides
        for key, value in config.config_overrides.items():
            if callable(value):
                try:
                    overrides[key] = value()
                except Exception as e:
                    print(f"Warning: Failed to apply override for {key}: {e}")
            else:
                overrides[key] = value
        
        # Apply environment variable overrides
        for var, default_value in config.optional_env_vars.items():
            env_key = var.replace("API_", "").lower()
            env_value = os.getenv(var)
            
            if env_value is not None:
                # Convert string values to appropriate types
                if isinstance(default_value, bool):
                    overrides[env_key] = env_value.lower() in ("true", "1", "yes")
                elif isinstance(default_value, int):
                    try:
                        overrides[env_key] = int(env_value)
                    except ValueError:
                        print(f"Warning: Invalid integer value for {var}: {env_value}")
                elif isinstance(default_value, float):
                    try:
                        overrides[env_key] = float(env_value)
                    except ValueError:
                        print(f"Warning: Invalid float value for {var}: {env_value}")
                else:
                    overrides[env_key] = env_value
        
        return overrides
    
    def get_deployment_info(self) -> Dict[str, Any]:
        """
        Get comprehensive deployment information.
        
        Returns:
            Dictionary with deployment information
        """
        config = self.get_current_config()
        validation = self.validate_deployment_config(config)
        overrides = self.apply_deployment_overrides(config)
        
        return {
            "deployment_type": self.deployment_type.value,
            "environment": self.current_environment.value,
            "config_valid": validation["valid"],
            "validation_errors": validation.get("errors", []),
            "validation_warnings": validation.get("warnings", []),
            "config_overrides": overrides,
            "resource_requirements": config.resource_requirements if config else {},
            "health_checks_enabled": config.health_check_enabled if config else False,
            "readiness_checks_enabled": config.readiness_check_enabled if config else False,
        }
    
    def print_deployment_summary(self) -> None:
        """Print a summary of the current deployment configuration."""
        info = self.get_deployment_info()
        
        print("=== Deployment Configuration Summary ===")
        print(f"Deployment Type: {info['deployment_type']}")
        print(f"Environment: {info['environment']}")
        print(f"Configuration Valid: {info['config_valid']}")
        
        if info['validation_errors']:
            print("\nValidation Errors:")
            for error in info['validation_errors']:
                print(f"  ❌ {error}")
        
        if info['validation_warnings']:
            print("\nValidation Warnings:")
            for warning in info['validation_warnings']:
                print(f"  ⚠️  {warning}")
        
        if info['config_overrides']:
            print("\nConfiguration Overrides:")
            for key, value in info['config_overrides'].items():
                print(f"  {key}: {value}")
        
        if info['resource_requirements']:
            print("\nResource Requirements:")
            for key, value in info['resource_requirements'].items():
                print(f"  {key}: {value}")
        
        print(f"\nHealth Checks Enabled: {info['health_checks_enabled']}")
        print(f"Readiness Checks Enabled: {info['readiness_checks_enabled']}")


# Global deployment manager instance
deployment_manager = DeploymentConfigManager()


def get_deployment_config() -> Optional[DeploymentConfig]:
    """Get the current deployment configuration."""
    return deployment_manager.get_current_config()


def validate_deployment() -> Dict[str, Any]:
    """Validate the current deployment configuration."""
    return deployment_manager.validate_deployment_config()


def apply_deployment_overrides() -> Dict[str, Any]:
    """Apply deployment-specific configuration overrides."""
    return deployment_manager.apply_deployment_overrides()


def get_deployment_info() -> Dict[str, Any]:
    """Get comprehensive deployment information."""
    return deployment_manager.get_deployment_info()


if __name__ == "__main__":
    # Allow running this module directly for deployment debugging
    deployment_manager.print_deployment_summary()
