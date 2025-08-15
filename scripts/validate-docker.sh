#!/bin/bash
# Docker setup validation script

set -e

echo "🐳 Validating Docker setup..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "✅ Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

echo "✅ docker-compose is available"

# Validate docker-compose configuration
echo "🔍 Validating docker-compose configuration..."
if docker-compose config --quiet; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has configuration errors"
    exit 1
fi

# Validate production configuration
echo "🔍 Validating production docker-compose configuration..."
if docker-compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet; then
    echo "✅ Production docker-compose configuration is valid"
else
    echo "❌ Production docker-compose configuration has errors"
    exit 1
fi

# Check if Dockerfile builds successfully
echo "🏗️  Testing Docker image build..."
if docker build -t generic-api-framework:validation-test . > /dev/null 2>&1; then
    echo "✅ Docker image builds successfully"
    # Clean up test image
    docker rmi generic-api-framework:validation-test > /dev/null 2>&1
else
    echo "❌ Docker image build failed"
    exit 1
fi

# Check required files exist
echo "📁 Checking required files..."
required_files=(
    "Dockerfile"
    "docker-compose.yml"
    "docker-compose.prod.yml"
    "docker-compose.override.yml"
    ".dockerignore"
    "scripts/docker-entrypoint.sh"
    "scripts/init-db.sql"
    "config/nginx.conf"
    "config/prometheus.yml"
    ".env.docker"
)

for file in "${required_files[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
        exit 1
    fi
done

# Check if entrypoint script is executable
if [[ -x "scripts/docker-entrypoint.sh" ]]; then
    echo "✅ docker-entrypoint.sh is executable"
else
    echo "❌ docker-entrypoint.sh is not executable"
    exit 1
fi

echo ""
echo "🎉 Docker setup validation completed successfully!"
echo ""
echo "Next steps:"
echo "1. Copy .env.docker to .env and customize for your environment"
echo "2. Run 'make docker-up' to start the development environment"
echo "3. Run 'make docker-test' to run tests in containers"
echo "4. Run 'make docker-monitoring' to start with monitoring stack"
echo ""
echo "For production deployment:"
echo "1. Set up production environment variables"
echo "2. Run 'make docker-prod-up' to start production services"
echo ""
echo "Documentation: docs/docker.md"