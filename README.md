# Production API Framework

A production-ready backend API framework built with FastAPI, featuring comprehensive configuration management, security, monitoring, and testing capabilities.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs with automatic OpenAPI documentation
- **Configuration Management**: Hierarchical configuration with Dynaconf supporting multiple environments
- **Security**: JWT authentication, RBAC, CORS, security headers, and audit logging
- **Database**: SQLAlchemy 2.x with async support, connection pooling, and Alembic migrations
- **Monitoring**: Structured JSON logging, Prometheus metrics, Sentry integration, and health checks
- **Testing**: Comprehensive test suite with pytest, fixtures, and 80%+ coverage target
- **Code Quality**: Black, isort, flake8, mypy, and pre-commit hooks
- **Containerization**: Docker support with multi-stage builds and docker-compose for local development
- **Deployment**: Production-ready with graceful shutdown, health checks, and environment-based configuration

## Documentation

- **[Quick Start](#quick-start)** - Get up and running quickly
- **[Developer Guide](docs/developer-guide.md)** - Comprehensive development workflows
- **[Environment Setup](docs/environment-setup.md)** - Environment configuration and deployment
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions
- **[API Documentation](#api-documentation)** - Interactive API docs

## Table of Contents

- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Running the Application](#running-the-application)
- [Testing](#testing)
- [Development Workflow](#development-workflow)
- [Configuration Management](#configuration-management)
- [Database Operations](#database-operations)
- [Docker Development](#docker-development)
- [API Documentation](#api-documentation)
- [Monitoring and Observability](#monitoring-and-observability)
- [Additional Resources](#additional-resources)

## Quick Start

### Prerequisites

- **Python 3.11+**: Required for modern async features and type hints
- **Poetry**: For dependency management and virtual environment handling
- **PostgreSQL 13+**: Primary database (SQLite for development/testing)
- **Redis 6+**: For caching and session storage (optional for basic functionality)
- **Docker & Docker Compose**: For containerized development (optional)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd production-api-framework
```

2. **Install Poetry** (if not already installed):
```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

3. **Install dependencies**:
```bash
poetry install
```

4. **Set up environment configuration**:
```bash
cp .env.example .env
# Edit .env with your specific configuration
```

5. **Initialize database**:
```bash
# Run migrations
poetry run alembic upgrade head

# Optional: Seed with sample data
poetry run python scripts/seed.py
```

6. **Start the application**:
```bash
poetry run uvicorn src.main:app --reload
```

7. **Verify installation**:
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/healthz

## Detailed Setup

### Environment Configuration

The application supports multiple configuration sources in order of precedence:

1. **Environment variables** (highest priority)
2. **Secrets file**: `config/.secrets.toml`
3. **Environment-specific config**: `config/environments/{ENV}.toml`
4. **Default config**: `config/settings.toml` (lowest priority)

#### Setting up .env file

```bash
# Copy and customize the environment file
cp .env.example .env
```

Key variables to configure:

```bash
# Application Environment
API_ENV=development  # development, staging, production

# Database Configuration
API_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname

# Security
API_SECRET_KEY=your-super-secret-key-here
API_JWT_ALGORITHM=HS256
API_JWT_EXPIRE_MINUTES=30

# External Services
API_REDIS_URL=redis://localhost:6379/0
API_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id

# Feature Flags
API_FEATURE_REGISTRATION_ENABLED=true
API_FEATURE_EMAIL_VERIFICATION=false
```

#### Setting up secrets (Production)

For production environments, create a secrets file:

```bash
cp config/.secrets.toml.example config/.secrets.toml
```

Edit `config/.secrets.toml`:

```toml
[default]
secret_key = "your-production-secret-key"
database_password = "your-database-password"
jwt_secret = "your-jwt-secret"

[production]
sentry_dsn = "https://your-sentry-dsn@sentry.io/project-id"
redis_password = "your-redis-password"
```

### Database Setup

#### PostgreSQL Setup

1. **Install PostgreSQL**:
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql
CREATE DATABASE api_framework;
CREATE USER api_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE api_framework TO api_user;
\q
```

2. **Update database URL in .env**:
```bash
API_DATABASE_URL=postgresql+asyncpg://api_user:your_password@localhost:5432/api_framework
```

#### SQLite Setup (Development)

For development, you can use SQLite:

```bash
API_DATABASE_URL=sqlite+aiosqlite:///./app.db
```

## Running the Application

### Development Mode

```bash
# Start with auto-reload
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# With specific environment
API_ENV=development poetry run uvicorn src.main:app --reload

# With debug logging
API_LOG_LEVEL=DEBUG poetry run uvicorn src.main:app --reload
```

### Production Mode

```bash
# Basic production run
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Gunicorn (recommended for production)
poetry run gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Using Make Commands

The project includes a Makefile for common tasks:

```bash
# Start development server
make dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make format

# Lint code
make lint

# Run all quality checks
make quality

# Build Docker image
make docker-build

# Start with Docker Compose
make docker-up
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage report
poetry run pytest --cov=src --cov-report=html --cov-report=term

# Run specific test categories
poetry run pytest -m unit          # Unit tests only
poetry run pytest -m integration   # Integration tests only
poetry run pytest -m slow          # Slow tests only

# Run specific test file
poetry run pytest tests/unit/test_auth.py

# Run with verbose output
poetry run pytest -v

# Run tests in parallel (faster)
poetry run pytest -n auto
```

### Test Configuration

Tests are organized into categories:

- **Unit tests** (`tests/unit/`): Fast, isolated tests for individual components
- **Integration tests** (`tests/integration/`): Tests that involve multiple components
- **End-to-end tests** (`tests/e2e/`): Full application workflow tests

### Writing Tests

Example test structure:

```python
# tests/unit/test_example.py
import pytest
from src.services.example_service import ExampleService

class TestExampleService:
    @pytest.fixture
    def service(self):
        return ExampleService()
    
    def test_example_method(self, service):
        result = service.example_method("input")
        assert result == "expected_output"
    
    @pytest.mark.asyncio
    async def test_async_method(self, service):
        result = await service.async_method("input")
        assert result is not None
```

### Test Database

Tests use a separate test database that's automatically created and cleaned up:

```python
# conftest.py handles test database setup
@pytest.fixture
async def test_db():
    # Creates in-memory SQLite database for tests
    # Automatically rolls back transactions after each test
```

## Development Workflow

### Code Quality Tools

The project uses several tools to maintain code quality:

```bash
# Format code with Black
poetry run black src tests

# Sort imports with isort
poetry run isort src tests

# Lint with flake8
poetry run flake8 src tests

# Type checking with mypy
poetry run mypy src

# Run all quality checks
poetry run pre-commit run --all-files
```

### Pre-commit Hooks

Install pre-commit hooks to automatically run quality checks:

```bash
poetry run pre-commit install

# Run hooks manually
poetry run pre-commit run --all-files
```

### Adding New Dependencies

```bash
# Add runtime dependency
poetry add package-name

# Add development dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show dependency tree
poetry show --tree
```

## Configuration Management

### Configuration Hierarchy

The application uses Dynaconf for hierarchical configuration:

1. **Default settings** (`config/settings.toml`)
2. **Environment-specific** (`config/environments/{env}.toml`)
3. **Secrets** (`config/.secrets.toml`)
4. **Environment variables** (`.env` or system)

### Configuration CLI

Use the configuration management script:

```bash
# Validate current configuration
poetry run python scripts/config_manager.py validate

# Show configuration information
poetry run python scripts/config_manager.py info

# Initialize secrets file
poetry run python scripts/config_manager.py init-secrets

# Check environment-specific configuration
poetry run python scripts/config_manager.py check-env production

# List all configuration keys
poetry run python scripts/config_manager.py list-keys
```

### Environment Profiles

#### Development Profile
```toml
# config/environments/development.toml
[default]
debug = true
log_level = "DEBUG"
database_url = "sqlite+aiosqlite:///./app.db"
cors_origins = ["http://localhost:3000", "http://localhost:8080"]
```

#### Staging Profile
```toml
# config/environments/staging.toml
[default]
debug = false
log_level = "INFO"
cors_origins = ["https://staging.example.com"]
sentry_environment = "staging"
```

#### Production Profile
```toml
# config/environments/production.toml
[default]
debug = false
log_level = "WARNING"
cors_origins = ["https://api.example.com"]
sentry_environment = "production"
```

## Database Operations

### Migrations with Alembic

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
poetry run alembic upgrade head

# Rollback to previous migration
poetry run alembic downgrade -1

# Show migration history
poetry run alembic history

# Show current migration
poetry run alembic current

# Rollback to specific revision
poetry run alembic downgrade <revision_id>
```

### Database Management Scripts

```bash
# Initialize database with sample data
poetry run python scripts/seed.py

# Backup database
poetry run python scripts/backup.py

# Restore database from backup
poetry run python scripts/restore.py backup_file.sql

# Reset database (development only)
poetry run python scripts/reset_db.py
```

## Docker Development

### Using Docker Compose

```bash
# Start all services (app, database, redis)
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build
```

### Docker Commands

```bash
# Build production image
docker build -t api-framework .

# Run container
docker run -p 8000:8000 --env-file .env api-framework

# Run with database
docker run -p 8000:8000 --link postgres:db api-framework
```

### Development with Docker

The `docker-compose.yml` includes:
- **API service**: The FastAPI application
- **PostgreSQL**: Database service
- **Redis**: Caching service
- **Adminer**: Database administration tool

Access services:
- API: http://localhost:8000
- Adminer: http://localhost:8080
- Redis: localhost:6379

## API Documentation

### Interactive Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### API Versioning

The API supports versioning through URL prefixes:

```
/v1/users          # Version 1 endpoints
/v2/users          # Version 2 endpoints (future)
```

### Authentication

Most endpoints require authentication. Get a token:

```bash
# Login to get token
curl -X POST "http://localhost:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "user@example.com", "password": "password"}'

# Use token in requests
curl -X GET "http://localhost:8000/v1/users/me" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## Monitoring and Observability

### Health Checks

The application provides several health check endpoints:

```bash
# Basic health check
curl http://localhost:8000/healthz

# Readiness check (includes dependencies)
curl http://localhost:8000/readyz

# Detailed health information
curl http://localhost:8000/health/detailed
```

### Metrics

Prometheus metrics are available at:

```bash
# Application metrics
curl http://localhost:8000/metrics
```

Key metrics include:
- Request duration and count
- Database connection pool status
- Custom business metrics
- Error rates by endpoint

### Logging

The application uses structured JSON logging:

```bash
# View logs in development
tail -f logs/app.log

# Filter by log level
grep '"level":"ERROR"' logs/app.log

# View audit logs
tail -f logs/audit.log
```

### Error Tracking

Sentry integration provides error tracking and performance monitoring:

1. Configure `API_SENTRY_DSN` in your environment
2. Errors are automatically captured and sent to Sentry
3. Performance transactions are tracked for slow endpoints

## Troubleshooting

### Common Issues

#### Database Connection Issues

**Problem**: `sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server`

**Solutions**:
1. Verify PostgreSQL is running: `brew services list | grep postgresql`
2. Check database URL in `.env` file
3. Ensure database exists: `createdb api_framework`
4. Test connection: `psql -h localhost -U api_user -d api_framework`

#### Migration Issues

**Problem**: `alembic.util.exc.CommandError: Can't locate revision identified by`

**Solutions**:
1. Check migration history: `poetry run alembic history`
2. Reset to head: `poetry run alembic stamp head`
3. If corrupted, recreate migrations: `rm migrations/versions/*.py && poetry run alembic revision --autogenerate -m "Initial"`

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solutions**:
1. Ensure you're in the project root directory
2. Use Poetry shell: `poetry shell`
3. Install dependencies: `poetry install`
4. Check PYTHONPATH: `export PYTHONPATH="${PYTHONPATH}:$(pwd)"`

#### Port Already in Use

**Problem**: `OSError: [Errno 48] Address already in use`

**Solutions**:
1. Find process using port: `lsof -i :8000`
2. Kill process: `kill -9 <PID>`
3. Use different port: `uvicorn src.main:app --port 8001`

#### Configuration Issues

**Problem**: Configuration not loading correctly

**Solutions**:
1. Validate configuration: `poetry run python scripts/config_manager.py validate`
2. Check environment: `echo $API_ENV`
3. Verify file paths: `ls -la config/`
4. Check syntax: `python -c "import toml; toml.load('config/settings.toml')"`

### Performance Issues

#### Slow Database Queries

1. Enable query logging: `API_LOG_LEVEL=DEBUG`
2. Check database indexes
3. Use database query analyzer
4. Monitor connection pool: Check `/metrics` endpoint

#### High Memory Usage

1. Check connection pool settings
2. Monitor with: `docker stats` or `htop`
3. Profile with: `py-spy top --pid <PID>`

#### Slow Startup

1. Check database connectivity
2. Verify external service availability
3. Review initialization code
4. Check for blocking operations in startup

### Getting Help

1. **Check logs**: Always start with application and error logs
2. **Validate configuration**: Use the config management CLI
3. **Test components**: Use health check endpoints
4. **Check dependencies**: Verify external services are running
5. **Review documentation**: Check this README and inline code docs

### Debug Mode

Enable debug mode for detailed error information:

```bash
# Set debug mode
API_DEBUG=true poetry run uvicorn src.main:app --reload

# Or in configuration
echo 'debug = true' >> config/environments/development.toml
```

**Warning**: Never enable debug mode in production as it exposes sensitive information.

## Project Structure

```
├── src/                          # Application source code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── app.py                    # Application factory
│   ├── dependencies.py           # Dependency injection
│   ├── exceptions.py             # Custom exceptions
│   ├── config/                   # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py           # Dynaconf settings
│   │   ├── environment.py        # Environment detection
│   │   ├── deployment.py         # Deployment configuration
│   │   └── documentation.py      # API documentation config
│   ├── routes/                   # API route definitions
│   │   ├── __init__.py
│   │   ├── v1/                   # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── health.py         # Health check endpoints
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   └── users.py          # User management endpoints
│   │   └── docs.py               # Documentation routes
│   ├── controllers/              # Request/response handling
│   │   ├── __init__.py
│   │   ├── base.py               # Base controller
│   │   └── users.py              # User controller
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   └── base.py               # Base service
│   ├── models/                   # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── base.py               # Base model
│   ├── schemas/                  # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── base.py               # Base schemas
│   │   ├── common.py             # Common schemas
│   │   └── users.py              # User schemas
│   ├── middleware/               # Custom middleware
│   │   ├── __init__.py
│   │   ├── auth.py               # Authentication middleware
│   │   ├── security.py           # Security headers
│   │   ├── error_handling.py     # Error handling
│   │   ├── observability.py      # Logging and metrics
│   │   └── connection_tracking.py # Connection tracking
│   ├── database/                 # Database utilities
│   │   ├── __init__.py
│   │   ├── base.py               # Database base classes
│   │   ├── config.py             # Database configuration
│   │   ├── models.py             # Model definitions
│   │   └── repositories.py       # Repository pattern
│   ├── auth/                     # Authentication and authorization
│   │   ├── __init__.py
│   │   └── rbac.py               # Role-based access control
│   ├── audit/                    # Audit logging
│   │   ├── __init__.py
│   │   ├── audit_logger.py       # Audit logging implementation
│   │   ├── decorators.py         # Audit decorators
│   │   └── middleware.py         # Audit middleware
│   ├── monitoring/               # Monitoring and observability
│   │   ├── __init__.py
│   │   ├── metrics.py            # Prometheus metrics
│   │   └── sentry.py             # Sentry integration
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       └── logging.py            # Logging utilities
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── factories.py              # Test data factories
│   ├── utils.py                  # Test utilities
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_auth.py          # Authentication tests
│   │   ├── test_controllers.py   # Controller tests
│   │   ├── test_database.py      # Database tests
│   │   └── ...                   # Other unit tests
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api.py           # API integration tests
│   │   ├── test_database_integration.py
│   │   └── test_health_endpoints.py
│   └── fixtures/                 # Test fixtures
│       ├── __init__.py
│       └── sample_data.py        # Sample test data
├── config/                       # Configuration files
│   ├── settings.toml             # Default settings
│   ├── .secrets.toml.example     # Secrets template
│   └── environments/             # Environment-specific configs
│       ├── development.toml      # Development settings
│       ├── staging.toml          # Staging settings
│       └── production.toml       # Production settings
├── scripts/                      # Utility scripts
│   ├── __init__.py
│   ├── config_manager.py         # Configuration management CLI
│   ├── migrate.py                # Database migration script
│   ├── seed.py                   # Database seeding
│   ├── health-check.py           # Health check script
│   ├── deployment-config.py      # Deployment configuration
│   └── docker-entrypoint.sh      # Docker entrypoint
├── docs/                         # Documentation
│   ├── __init__.py
│   ├── deployment.md             # Deployment guide
│   ├── docker.md                 # Docker guide
│   ├── migrations.md             # Migration guide
│   └── graceful-shutdown.md      # Graceful shutdown guide
├── migrations/                   # Alembic migrations
│   ├── env.py                    # Migration environment
│   ├── script.py.mako            # Migration template
│   └── versions/                 # Migration versions
│       └── 001_initial_schema.py # Initial migration
├── logs/                         # Log files
│   ├── app.log                   # Application logs
│   └── audit.log                 # Audit logs
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── docker-compose.yml            # Local development services
├── docker-compose.prod.yml       # Production Docker Compose
├── Dockerfile                    # Production container
├── Makefile                      # Common tasks
├── pyproject.toml                # Poetry configuration
├── pytest.ini                   # Pytest configuration
├── alembic.ini                   # Alembic configuration
└── README.md                     # This file
```

## Additional Resources

### Documentation

- **[Developer Guide](docs/developer-guide.md)** - Comprehensive guide for developers including:
  - Creating API endpoints
  - Database operations and migrations
  - Testing procedures
  - Authentication and authorization
  - Error handling patterns
  - Code quality standards

- **[Environment Setup Guide](docs/environment-setup.md)** - Environment configuration including:
  - Development environment setup
  - Staging environment configuration
  - Production deployment
  - Configuration management
  - Security considerations

- **[Troubleshooting Guide](docs/troubleshooting.md)** - Solutions for common issues:
  - Installation and setup problems
  - Database connection issues
  - Configuration problems
  - Runtime errors
  - Performance issues
  - Docker and deployment issues

### Additional Documentation

- **[Deployment Guide](docs/deployment.md)** - Production deployment strategies
- **[Docker Guide](docs/docker.md)** - Container development and deployment
- **[Migration Guide](docs/migrations.md)** - Database migration procedures
- **[Graceful Shutdown Guide](docs/graceful-shutdown.md)** - Proper application shutdown

## Contributing

### Development Process

1. **Fork the repository** and create a feature branch
2. **Set up development environment**:
   ```bash
   poetry install
   poetry run pre-commit install
   cp .env.example .env
   ```
3. **Make your changes** following the coding standards
4. **Write tests** for new functionality
5. **Run quality checks**:
   ```bash
   make quality  # Runs formatting, linting, and type checking
   make test     # Runs test suite
   ```
6. **Submit a pull request** with a clear description

### Coding Standards

- **Python Style**: Follow PEP 8, enforced by Black and flake8
- **Type Hints**: Use type hints for all function signatures
- **Docstrings**: Use Google-style docstrings for all public functions
- **Testing**: Maintain 80%+ test coverage
- **Commits**: Use conventional commit messages

### Code Review Checklist

- [ ] Code follows project style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced
- [ ] Performance impact considered
- [ ] Backward compatibility maintained

For detailed development workflows, see the [Developer Guide](docs/developer-guide.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.