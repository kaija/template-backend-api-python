# Makefile for API Framework Development and Testing
.PHONY: help migrate-up migrate-down migrate-current migrate-history migrate-check migrate-test migrate-backup migrate-rollback test test-unit test-integration test-coverage test-watch test-fast test-slow install-dev lint format type-check quality-check

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Testing:"
	@echo "  test                - Run all tests"
	@echo "  test-unit           - Run unit tests only"
	@echo "  test-integration    - Run integration tests only"
	@echo "  test-coverage       - Run tests with coverage report"
	@echo "  test-watch          - Run tests in watch mode"
	@echo "  test-fast           - Run fast tests only"
	@echo "  test-slow           - Run slow tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  install-dev         - Install development dependencies"
	@echo "  lint                - Run linting (flake8)"
	@echo "  format              - Format code (black, isort)"
	@echo "  type-check          - Run type checking (mypy)"
	@echo "  quality-check       - Run all quality checks"
	@echo ""
	@echo "Database Migration:"
	@echo "  migrate-up          - Upgrade database to latest version"
	@echo "  migrate-down REV    - Downgrade database to specific revision"
	@echo "  migrate-current     - Show current database revision"
	@echo "  migrate-history     - Show migration history"
	@echo "  migrate-check       - Check for pending migrations"
	@echo "  migrate-test        - Test migration up/down cycle"
	@echo "  migrate-backup      - Create data backup"
	@echo "  migrate-rollback REV - Safe rollback to revision"
	@echo "  migrate-new MSG     - Create new migration"
	@echo ""
	@echo "Deployment Configuration:"
	@echo "  deploy-validate     - Validate current deployment configuration"
	@echo "  deploy-current      - Show current deployment configuration"
	@echo "  deploy-list         - List available deployment configurations"
	@echo "  deploy-setup TYPE ENV - Setup deployment (docker/k8s/cloud_run + dev/staging/prod)"
	@echo "  deploy-generate-env TYPE ENV - Generate environment file"
	@echo "  deploy-generate-k8s ENV - Generate Kubernetes manifests"
	@echo "  deploy-docker-dev   - Quick setup Docker development"
	@echo "  deploy-docker-prod  - Quick setup Docker production"
	@echo "  deploy-k8s-prod     - Quick setup Kubernetes production"
	@echo ""
	@echo "Examples:"
	@echo "  make test"
	@echo "  make test-unit"
	@echo "  make migrate-up"
	@echo "  make migrate-down REV=001"
	@echo "  make migrate-rollback REV=001"
	@echo "  make migrate-new MSG='Add user preferences table'"
	@echo "  make deploy-validate"
	@echo "  make deploy-setup TYPE=docker ENV=production"
	@echo "  make deploy-generate-k8s ENV=production"

# Testing targets
test:
	@echo "Running all tests..."
	pytest

test-unit:
	@echo "Running unit tests..."
	pytest tests/unit/ -m unit

test-integration:
	@echo "Running integration tests..."
	pytest tests/integration/ -m integration

test-coverage:
	@echo "Running tests with coverage report..."
	pytest --cov=src --cov-report=term-missing --cov-report=html

test-watch:
	@echo "Running tests in watch mode..."
	pytest-watch -- --testmon

test-fast:
	@echo "Running fast tests..."
	pytest -m "not slow"

test-slow:
	@echo "Running slow tests..."
	pytest -m slow

test-parallel:
	@echo "Running tests in parallel..."
	pytest -n auto

test-verbose:
	@echo "Running tests with verbose output..."
	pytest -v

test-debug:
	@echo "Running tests with debug output..."
	pytest -s --pdb

# Code quality targets
install-dev:
	@echo "Installing development dependencies..."
	poetry install --with dev,test

lint:
	@echo "Running linting checks..."
	flake8 src tests

format:
	@echo "Formatting code..."
	black src tests
	isort src tests

format-check:
	@echo "Checking code formatting..."
	black --check src tests
	isort --check-only src tests

type-check:
	@echo "Running type checks..."
	mypy src

quality-check: format-check lint type-check
	@echo "All quality checks passed!"

# Development helpers
clean:
	@echo "Cleaning up temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/

clean-test:
	@echo "Cleaning test artifacts..."
	rm -rf .coverage htmlcov/ .pytest_cache/ coverage.xml

setup-dev: install-dev
	@echo "Setting up development environment..."
	pre-commit install

run-dev:
	@echo "Starting development server..."
	python -m src.main

run-prod:
	@echo "Starting production server..."
	uvicorn src.main:app --host 0.0.0.0 --port 8000

# Upgrade database to latest version
migrate-up:
	@echo "Upgrading database to latest version..."
	python scripts/migrate.py upgrade

# Downgrade database to specific revision
migrate-down:
	@if [ -z "$(REV)" ]; then \
		echo "Error: REV parameter required. Usage: make migrate-down REV=001"; \
		exit 1; \
	fi
	@echo "Downgrading database to revision $(REV)..."
	python scripts/migrate.py downgrade $(REV)

# Show current database revision
migrate-current:
	@echo "Current database revision:"
	python scripts/migrate.py current

# Show migration history
migrate-history:
	@echo "Migration history:"
	python scripts/migrate.py history -v

# Check for pending migrations
migrate-check:
	@echo "Checking for pending migrations..."
	python scripts/migrate.py check

# Test migration up/down cycle
migrate-test:
	@echo "Testing migration up/down cycle..."
	python scripts/migrate.py test

# Create data backup
migrate-backup:
	@echo "Creating data backup..."
	python scripts/rollback.py backup

# Safe rollback to revision
migrate-rollback:
	@if [ -z "$(REV)" ]; then \
		echo "Error: REV parameter required. Usage: make migrate-rollback REV=001"; \
		exit 1; \
	fi
	@echo "Rolling back database to revision $(REV)..."
	python scripts/rollback.py rollback $(REV)

# Create new migration
migrate-new:
	@if [ -z "$(MSG)" ]; then \
		echo "Error: MSG parameter required. Usage: make migrate-new MSG='Migration message'"; \
		exit 1; \
	fi
	@echo "Creating new migration: $(MSG)"
	python scripts/migrate.py revision -m "$(MSG)"

# Validate rollback safety
migrate-validate:
	@if [ -z "$(REV)" ]; then \
		echo "Error: REV parameter required. Usage: make migrate-validate REV=001"; \
		exit 1; \
	fi
	@echo "Validating rollback to revision $(REV)..."
	python scripts/rollback.py validate $(REV)

# List available backups
migrate-list-backups:
	@echo "Available backups:"
	python scripts/rollback.py list-backups

# Show backup information
migrate-show-backup:
	@if [ -z "$(BACKUP)" ]; then \
		echo "Error: BACKUP parameter required. Usage: make migrate-show-backup BACKUP=backup_file.json"; \
		exit 1; \
	fi
	@echo "Backup information:"
	python scripts/rollback.py show-backup $(BACKUP)

# Development helpers
migrate-reset-dev:
	@echo "WARNING: This will reset the development database!"
	@read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	python scripts/migrate.py downgrade base
	python scripts/migrate.py upgrade head

# Production safety check
migrate-prod-check:
	@echo "Production migration safety check..."
	@if [ "$$API_ENV" = "production" ]; then \
		echo "PRODUCTION ENVIRONMENT DETECTED!"; \
		echo "Please ensure you have:"; \
		echo "1. Created a full database backup"; \
		echo "2. Tested migrations in staging"; \
		echo "3. Scheduled maintenance window"; \
		echo "4. Notified relevant stakeholders"; \
		read -p "Continue with production migration? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1; \
	fi
	python scripts/migrate.py check

# Docker Development Commands
.PHONY: docker-build docker-up docker-down docker-logs docker-shell docker-test docker-clean
.PHONY: docker-prod-up docker-prod-down docker-monitoring docker-dev-tools

docker-build:
	@echo "Building Docker image..."
	docker-compose build

docker-up:
	@echo "Starting all services with Docker Compose..."
	docker-compose up -d
	@echo "Services started. API available at http://localhost:8000"
	@echo "Health check: http://localhost:8000/healthz"

docker-down:
	@echo "Stopping all services..."
	docker-compose down

docker-logs:
	@echo "Viewing logs from all services..."
	docker-compose logs -f

docker-shell:
	@echo "Opening shell in API container..."
	docker-compose exec api /bin/bash

docker-test:
	@echo "Running tests in Docker container..."
	docker-compose exec api pytest

docker-clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f

# Docker Production Commands
docker-prod-up:
	@echo "Starting production services..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

docker-prod-down:
	@echo "Stopping production services..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Start with monitoring stack
docker-monitoring:
	@echo "Starting services with monitoring stack..."
	docker-compose --profile monitoring up -d
	@echo "Prometheus available at http://localhost:9090"
	@echo "Grafana available at http://localhost:3000 (admin/admin)"

# Start with development tools
docker-dev-tools:
	@echo "Starting services with development tools..."
	docker-compose --profile dev-tools up -d
	@echo "Adminer available at http://localhost:8080"
	@echo "Redis Commander available at http://localhost:8081"

# Docker utility commands
docker-migrate:
	@echo "Running database migrations in Docker..."
	docker-compose exec api python -m alembic upgrade head

docker-reset:
	@echo "Resetting Docker environment..."
	docker-compose down -v
	docker-compose up -d

docker-status:
	@echo "Docker services status:"
	docker-compose ps

# Deployment Configuration Commands
.PHONY: deploy-validate deploy-setup deploy-generate-env deploy-generate-k8s deploy-current deploy-list

deploy-validate:
	@echo "Validating deployment configuration..."
	python scripts/validate-deployment.py

deploy-validate-env:
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV parameter required. Usage: make deploy-validate-env ENV=production"; \
		exit 1; \
	fi
	@echo "Validating $(ENV) environment configuration..."
	python scripts/validate-deployment.py --environment $(ENV) --verbose

deploy-validate-type:
	@if [ -z "$(TYPE)" ]; then \
		echo "Error: TYPE parameter required. Usage: make deploy-validate-type TYPE=docker"; \
		exit 1; \
	fi
	@echo "Validating $(TYPE) deployment configuration..."
	python scripts/validate-deployment.py --deployment-type $(TYPE) --verbose

deploy-setup:
	@if [ -z "$(TYPE)" ] || [ -z "$(ENV)" ]; then \
		echo "Error: TYPE and ENV parameters required. Usage: make deploy-setup TYPE=docker ENV=production"; \
		exit 1; \
	fi
	@echo "Setting up $(TYPE) deployment for $(ENV) environment..."
	python scripts/deployment-config.py setup $(TYPE) $(ENV)

deploy-generate-env:
	@if [ -z "$(TYPE)" ] || [ -z "$(ENV)" ]; then \
		echo "Error: TYPE and ENV parameters required. Usage: make deploy-generate-env TYPE=docker ENV=production"; \
		exit 1; \
	fi
	@echo "Generating environment file for $(TYPE)/$(ENV)..."
	python scripts/deployment-config.py generate-env $(TYPE) $(ENV)

deploy-generate-k8s:
	@if [ -z "$(ENV)" ]; then \
		echo "Error: ENV parameter required. Usage: make deploy-generate-k8s ENV=production"; \
		exit 1; \
	fi
	@echo "Generating Kubernetes manifests for $(ENV) environment..."
	python scripts/deployment-config.py generate-k8s $(ENV)

deploy-current:
	@echo "Current deployment configuration:"
	python scripts/deployment-config.py current

deploy-list:
	@echo "Available deployment configurations:"
	python scripts/deployment-config.py list

# Deployment Examples
deploy-docker-dev:
	@echo "Setting up Docker development environment..."
	python scripts/deployment-config.py setup docker development

deploy-docker-prod:
	@echo "Setting up Docker production environment..."
	python scripts/deployment-config.py setup docker production

deploy-k8s-prod:
	@echo "Setting up Kubernetes production environment..."
	python scripts/deployment-config.py setup kubernetes production

deploy-cloud-run-prod:
	@echo "Setting up Cloud Run production environment..."
	python scripts/deployment-config.py setup cloud_run production