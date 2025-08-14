#!/usr/bin/env python3
"""
Deployment configuration validation script.

This script validates the deployment configuration for different environments
and deployment types, ensuring all required settings are properly configured.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.deployment import DeploymentConfigManager, DeploymentType, Environment
from src.config.environment import EnvironmentDetector, ConfigurationPaths


def validate_environment_variables(required_vars: List[str]) -> Dict[str, Any]:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "missing_vars": [],
        "warnings": [],
    }
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            results["missing_vars"].append(var)
            results["valid"] = False
        elif var.lower().endswith(("_key", "_secret", "_password")) and len(value) < 16:
            results["warnings"].append(f"{var} appears to be too short for a secure value")
    
    return results


def validate_database_connection(database_url: str) -> Dict[str, Any]:
    """
    Validate database connection configuration.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
    }
    
    if not database_url:
        results["errors"].append("Database URL is not configured")
        results["valid"] = False
        return results
    
    # Check for async driver
    if "asyncpg" not in database_url and "aiosqlite" not in database_url:
        results["warnings"].append("Database URL should use an async driver (asyncpg for PostgreSQL)")
    
    # Check for default passwords in production
    if "password" in database_url.lower() and os.getenv("API_ENV") == "production":
        results["warnings"].append("Database URL contains 'password' - ensure this is not a default value")
    
    return results


def validate_security_configuration() -> Dict[str, Any]:
    """
    Validate security-related configuration.
    
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
    }
    
    # Check secret key
    secret_key = os.getenv("API_SECRET_KEY", "")
    if not secret_key:
        results["errors"].append("API_SECRET_KEY is not set")
        results["valid"] = False
    elif len(secret_key) < 32:
        results["errors"].append("API_SECRET_KEY should be at least 32 characters long")
        results["valid"] = False
    elif secret_key in ["your-super-secret-key-change-this-in-production", "development-secret-key"]:
        results["errors"].append("API_SECRET_KEY appears to be a default/example value")
        results["valid"] = False
    
    # Check debug mode in production
    env = os.getenv("API_ENV", "development")
    debug = os.getenv("API_DEBUG", "false").lower() in ("true", "1", "yes")
    if env == "production" and debug:
        results["errors"].append("Debug mode should be disabled in production")
        results["valid"] = False
    
    # Check CORS configuration
    cors_origins = os.getenv("API_CORS_ORIGINS", "")
    if env == "production" and ("*" in cors_origins or not cors_origins):
        results["warnings"].append("CORS origins should be explicitly configured in production")
    
    return results


def validate_monitoring_configuration() -> Dict[str, Any]:
    """
    Validate monitoring and observability configuration.
    
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
    }
    
    env = os.getenv("API_ENV", "development")
    
    # Check Sentry configuration for non-development environments
    if env in ("staging", "production"):
        sentry_dsn = os.getenv("API_SENTRY_DSN", "")
        if not sentry_dsn:
            results["warnings"].append(f"Sentry DSN not configured for {env} environment")
        elif "your-sentry-dsn" in sentry_dsn:
            results["errors"].append("Sentry DSN appears to be a placeholder value")
            results["valid"] = False
    
    # Check metrics configuration
    metrics_enabled = os.getenv("API_METRICS_ENABLED", "true").lower() in ("true", "1", "yes")
    if not metrics_enabled and env != "test":
        results["warnings"].append("Metrics are disabled - consider enabling for monitoring")
    
    return results


def validate_deployment_specific(deployment_type: DeploymentType) -> Dict[str, Any]:
    """
    Validate deployment-specific configuration.
    
    Args:
        deployment_type: Type of deployment
        
    Returns:
        Validation results
    """
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
    }
    
    if deployment_type == DeploymentType.DOCKER:
        # Docker-specific validations
        host = os.getenv("API_HOST", "127.0.0.1")
        if host != "0.0.0.0":
            results["warnings"].append("API_HOST should be '0.0.0.0' for Docker deployments")
        
        # Check for Docker networking
        database_url = os.getenv("API_DATABASE_URL", "")
        if "localhost" in database_url:
            results["warnings"].append("Database URL uses 'localhost' - consider using Docker service names")
    
    elif deployment_type == DeploymentType.KUBERNETES:
        # Kubernetes-specific validations
        if not os.getenv("KUBERNETES_SERVICE_HOST"):
            results["warnings"].append("KUBERNETES_SERVICE_HOST not detected - may not be running in Kubernetes")
        
        # Check health check configuration
        health_timeout = int(os.getenv("API_HEALTH_CHECK_TIMEOUT", "5"))
        if health_timeout > 10:
            results["warnings"].append("Health check timeout may be too long for Kubernetes probes")
    
    elif deployment_type == DeploymentType.CLOUD_RUN:
        # Cloud Run specific validations
        port = os.getenv("PORT")
        if not port:
            results["errors"].append("PORT environment variable is required for Cloud Run")
            results["valid"] = False
        
        workers = int(os.getenv("API_WORKERS", "1"))
        if workers > 1:
            results["warnings"].append("Cloud Run handles scaling - consider using 1 worker")
    
    elif deployment_type == DeploymentType.HEROKU:
        # Heroku specific validations
        port = os.getenv("PORT")
        if not port:
            results["errors"].append("PORT environment variable is required for Heroku")
            results["valid"] = False
        
        database_url = os.getenv("DATABASE_URL")
        if database_url and not database_url.startswith("postgresql+asyncpg://"):
            results["warnings"].append("DATABASE_URL may need to be converted to async format")
    
    return results


def print_validation_results(results: Dict[str, Any], title: str) -> None:
    """
    Print validation results in a formatted way.
    
    Args:
        results: Validation results dictionary
        title: Title for the validation section
    """
    print(f"\n=== {title} ===")
    
    if results["valid"]:
        print("✅ Valid")
    else:
        print("❌ Invalid")
    
    # Print errors
    if "errors" in results and results["errors"]:
        print("\nErrors:")
        for error in results["errors"]:
            print(f"  ❌ {error}")
    
    # Print warnings
    if "warnings" in results and results["warnings"]:
        print("\nWarnings:")
        for warning in results["warnings"]:
            print(f"  ⚠️  {warning}")
    
    # Print missing variables
    if "missing_vars" in results and results["missing_vars"]:
        print("\nMissing Environment Variables:")
        for var in results["missing_vars"]:
            print(f"  ❌ {var}")


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(description="Validate deployment configuration")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production", "test"],
        help="Override environment detection"
    )
    parser.add_argument(
        "--deployment-type",
        choices=["local", "docker", "kubernetes", "cloud_run", "heroku", "serverless"],
        help="Override deployment type detection"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed configuration information"
    )
    parser.add_argument(
        "--exit-on-error",
        action="store_true",
        help="Exit with non-zero code if validation fails"
    )
    
    args = parser.parse_args()
    
    # Override environment variables if specified
    if args.environment:
        os.environ["API_ENV"] = args.environment
    
    # Initialize deployment manager
    deployment_manager = DeploymentConfigManager()
    
    # Override deployment type if specified
    if args.deployment_type:
        deployment_manager.deployment_type = DeploymentType(args.deployment_type)
    
    print("=== Deployment Configuration Validation ===")
    print(f"Environment: {deployment_manager.current_environment.value}")
    print(f"Deployment Type: {deployment_manager.deployment_type.value}")
    
    # Get current configuration
    config = deployment_manager.get_current_config()
    if not config:
        print("❌ No deployment configuration found")
        if args.exit_on_error:
            sys.exit(1)
        return
    
    overall_valid = True
    
    # Validate deployment configuration
    deployment_results = deployment_manager.validate_deployment_config(config)
    print_validation_results(deployment_results, "Deployment Configuration")
    if not deployment_results["valid"]:
        overall_valid = False
    
    # Validate environment variables
    env_var_results = validate_environment_variables(config.required_env_vars)
    print_validation_results(env_var_results, "Environment Variables")
    if not env_var_results["valid"]:
        overall_valid = False
    
    # Validate database configuration
    database_url = os.getenv("API_DATABASE_URL", "")
    db_results = validate_database_connection(database_url)
    print_validation_results(db_results, "Database Configuration")
    if not db_results["valid"]:
        overall_valid = False
    
    # Validate security configuration
    security_results = validate_security_configuration()
    print_validation_results(security_results, "Security Configuration")
    if not security_results["valid"]:
        overall_valid = False
    
    # Validate monitoring configuration
    monitoring_results = validate_monitoring_configuration()
    print_validation_results(monitoring_results, "Monitoring Configuration")
    if not monitoring_results["valid"]:
        overall_valid = False
    
    # Validate deployment-specific configuration
    deployment_specific_results = validate_deployment_specific(deployment_manager.deployment_type)
    print_validation_results(deployment_specific_results, f"{deployment_manager.deployment_type.value.title()} Specific Configuration")
    if not deployment_specific_results["valid"]:
        overall_valid = False
    
    # Show verbose information if requested
    if args.verbose:
        print("\n=== Configuration Details ===")
        deployment_info = deployment_manager.get_deployment_info()
        for key, value in deployment_info.items():
            if key not in ["validation_errors", "validation_warnings"]:
                print(f"{key}: {value}")
    
    # Final result
    print(f"\n=== Overall Validation Result ===")
    if overall_valid:
        print("✅ All validations passed")
        sys.exit(0)
    else:
        print("❌ Validation failed")
        if args.exit_on_error:
            sys.exit(1)


if __name__ == "__main__":
    main()