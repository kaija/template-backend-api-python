#!/usr/bin/env python3
"""
Deployment configuration management CLI tool.

This script provides utilities for managing deployment configurations,
generating environment files, and setting up deployments.
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.deployment import DeploymentConfigManager, DeploymentType, Environment
from src.config.environment import EnvironmentDetector, ConfigurationPaths


def generate_env_file(deployment_type: str, environment: str, output_path: str) -> None:
    """
    Generate an environment file for a specific deployment scenario.
    
    Args:
        deployment_type: Type of deployment
        environment: Target environment
        output_path: Output file path
    """
    # Map deployment types to template files
    template_map = {
        "docker": "config/deployment/.env.docker.example",
        "kubernetes": "config/deployment/.env.kubernetes.example",
        "cloud_run": "config/deployment/.env.cloud-run.example",
        "local": ".env.example",
    }
    
    template_file = template_map.get(deployment_type, ".env.example")
    
    if not Path(template_file).exists():
        print(f"❌ Template file not found: {template_file}")
        return
    
    # Copy template file
    shutil.copy2(template_file, output_path)
    
    # Update environment-specific values
    with open(output_path, 'r') as f:
        content = f.read()
    
    # Replace environment placeholder
    content = content.replace('API_ENV=development', f'API_ENV={environment}')
    
    # Environment-specific replacements
    if environment == "production":
        content = content.replace('API_DEBUG=true', 'API_DEBUG=false')
        content = content.replace('API_LOG_LEVEL=DEBUG', 'API_LOG_LEVEL=WARNING')
        content = content.replace('development-secret-key', 'CHANGE-THIS-TO-SECURE-KEY')
    elif environment == "staging":
        content = content.replace('API_DEBUG=true', 'API_DEBUG=false')
        content = content.replace('API_LOG_LEVEL=DEBUG', 'API_LOG_LEVEL=INFO')
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Generated environment file: {output_path}")
    print(f"📝 Please review and update the configuration values")


def generate_docker_compose_override(environment: str, output_path: str) -> None:
    """
    Generate a Docker Compose override file for a specific environment.
    
    Args:
        environment: Target environment
        output_path: Output file path
    """
    if environment == "production":
        compose_content = """# Docker Compose override for production
services:
  api:
    environment:
      - API_ENV=production
      - API_DEBUG=false
      - API_LOG_LEVEL=WARNING
      - API_LOG_FORMAT=json
    # Remove volume mounts for production
    volumes: []
    # Use production command
    command: ["python", "-m", "src.main"]
    
  # Production-specific resource limits
  deploy:
    resources:
      limits:
        cpus: '1.0'
        memory: 512M
      reservations:
        cpus: '0.5'
        memory: 256M
"""
    elif environment == "staging":
        compose_content = """# Docker Compose override for staging
services:
  api:
    environment:
      - API_ENV=staging
      - API_DEBUG=false
      - API_LOG_LEVEL=INFO
      - API_LOG_FORMAT=json
    # Limited volume mounts for staging
    volumes:
      - ./logs:/app/logs
    
  # Staging-specific resource limits
  deploy:
    resources:
      limits:
        cpus: '0.5'
        memory: 256M
      reservations:
        cpus: '0.25'
        memory: 128M
"""
    else:
        print(f"❌ No Docker Compose override template for environment: {environment}")
        return
    
    with open(output_path, 'w') as f:
        f.write(compose_content)
    
    print(f"✅ Generated Docker Compose override: {output_path}")


def generate_kubernetes_manifests(environment: str, output_dir: str) -> None:
    """
    Generate Kubernetes manifests for deployment.
    
    Args:
        environment: Target environment
        output_dir: Output directory for manifests
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # ConfigMap
    configmap_content = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: default
data:
  API_ENV: "{environment}"
  API_DEBUG: "false"
  API_LOG_LEVEL: "INFO"
  API_LOG_FORMAT: "json"
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  API_WORKERS: "4"
  API_METRICS_ENABLED: "true"
  API_HEALTH_CHECK_TIMEOUT: "5"
  API_SHUTDOWN_TIMEOUT: "30"
"""
    
    with open(output_path / "configmap.yaml", 'w') as f:
        f.write(configmap_content)
    
    # Secret template
    secret_content = """apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
  namespace: default
type: Opaque
stringData:
  API_SECRET_KEY: "CHANGE-THIS-TO-SECURE-KEY"
  API_DATABASE_URL: "postgresql+asyncpg://user:password@postgres-service:5432/api_db"
  API_REDIS_URL: "redis://redis-service:6379/0"
  API_SENTRY_DSN: "https://your-sentry-dsn@sentry.io/project-id"
"""
    
    with open(output_path / "secret.yaml", 'w') as f:
        f.write(secret_content)
    
    # Deployment
    deployment_content = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
  namespace: default
  labels:
    app: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: your-registry/api:latest
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: api-config
        - secretRef:
            name: api-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10"]
---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: default
  labels:
    app: api
spec:
  selector:
    app: api
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
    name: http
  type: ClusterIP
"""
    
    with open(output_path / "deployment.yaml", 'w') as f:
        f.write(deployment_content)
    
    print(f"✅ Generated Kubernetes manifests in: {output_dir}")
    print("📝 Please update the image registry and secret values")


def setup_deployment(deployment_type: str, environment: str) -> None:
    """
    Set up a complete deployment configuration.
    
    Args:
        deployment_type: Type of deployment
        environment: Target environment
    """
    print(f"🚀 Setting up {deployment_type} deployment for {environment} environment")
    
    if deployment_type == "docker":
        # Generate environment file
        env_file = f".env.{environment}"
        generate_env_file("docker", environment, env_file)
        
        # Generate Docker Compose override if needed
        if environment in ["staging", "production"]:
            override_file = f"docker-compose.{environment}.yml"
            generate_docker_compose_override(environment, override_file)
    
    elif deployment_type == "kubernetes":
        # Generate Kubernetes manifests
        manifest_dir = f"k8s/{environment}"
        generate_kubernetes_manifests(environment, manifest_dir)
        
        # Generate environment file for reference
        env_file = f".env.{environment}.k8s"
        generate_env_file("kubernetes", environment, env_file)
    
    elif deployment_type == "cloud_run":
        # Generate environment file
        env_file = f".env.{environment}.cloudrun"
        generate_env_file("cloud_run", environment, env_file)
    
    elif deployment_type == "local":
        # Generate local environment file
        env_file = ".env"
        generate_env_file("local", environment, env_file)
    
    else:
        print(f"❌ Unsupported deployment type: {deployment_type}")
        return
    
    print(f"✅ Deployment setup complete for {deployment_type}/{environment}")
    print("📋 Next steps:")
    print("  1. Review and update configuration values")
    print("  2. Validate configuration: python scripts/validate-deployment.py")
    print("  3. Test deployment in staging environment first")


def list_configurations() -> None:
    """List available deployment configurations."""
    deployment_manager = DeploymentConfigManager()
    
    print("=== Available Deployment Configurations ===")
    
    for config_name, config in deployment_manager.deployment_configs.items():
        print(f"\n{config_name}:")
        print(f"  Deployment Type: {config.deployment_type.value}")
        print(f"  Environment: {config.environment.value}")
        print(f"  Required Variables: {len(config.required_env_vars)}")
        print(f"  Optional Variables: {len(config.optional_env_vars)}")
        print(f"  Health Checks: {'✅' if config.health_check_enabled else '❌'}")


def show_current_config() -> None:
    """Show current deployment configuration."""
    deployment_manager = DeploymentConfigManager()
    deployment_manager.print_deployment_summary()


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Deployment configuration management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate environment file
    gen_env_parser = subparsers.add_parser("generate-env", help="Generate environment file")
    gen_env_parser.add_argument("deployment_type", choices=["local", "docker", "kubernetes", "cloud_run"])
    gen_env_parser.add_argument("environment", choices=["development", "staging", "production"])
    gen_env_parser.add_argument("--output", "-o", default=None, help="Output file path")
    
    # Generate Kubernetes manifests
    gen_k8s_parser = subparsers.add_parser("generate-k8s", help="Generate Kubernetes manifests")
    gen_k8s_parser.add_argument("environment", choices=["staging", "production"])
    gen_k8s_parser.add_argument("--output-dir", "-o", default="k8s", help="Output directory")
    
    # Setup deployment
    setup_parser = subparsers.add_parser("setup", help="Setup complete deployment")
    setup_parser.add_argument("deployment_type", choices=["local", "docker", "kubernetes", "cloud_run"])
    setup_parser.add_argument("environment", choices=["development", "staging", "production"])
    
    # List configurations
    subparsers.add_parser("list", help="List available configurations")
    
    # Show current configuration
    subparsers.add_parser("current", help="Show current configuration")
    
    # Validate configuration
    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    validate_parser.add_argument("--environment", choices=["development", "staging", "production"])
    validate_parser.add_argument("--deployment-type", choices=["local", "docker", "kubernetes", "cloud_run"])
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "generate-env":
        output_path = args.output or f".env.{args.environment}.{args.deployment_type}"
        generate_env_file(args.deployment_type, args.environment, output_path)
    
    elif args.command == "generate-k8s":
        output_dir = f"{args.output_dir}/{args.environment}"
        generate_kubernetes_manifests(args.environment, output_dir)
    
    elif args.command == "setup":
        setup_deployment(args.deployment_type, args.environment)
    
    elif args.command == "list":
        list_configurations()
    
    elif args.command == "current":
        show_current_config()
    
    elif args.command == "validate":
        # Import and run validation
        cmd = ["python", "scripts/validate-deployment.py"]
        if args.environment:
            cmd.extend(["--environment", args.environment])
        if args.deployment_type:
            cmd.extend(["--deployment-type", args.deployment_type])
        
        os.system(" ".join(cmd))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()