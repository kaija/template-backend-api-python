# Production API Framework

A production-ready backend API framework built with FastAPI, featuring comprehensive configuration management, security, monitoring, and testing capabilities.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Configuration Management**: Hierarchical configuration with Dynaconf
- **Security**: JWT authentication, CORS, security headers
- **Database**: SQLAlchemy 2.x with async support and migrations
- **Monitoring**: Structured logging, Prometheus metrics, Sentry integration
- **Testing**: Comprehensive test suite with pytest
- **Code Quality**: Black, isort, flake8, mypy, pre-commit hooks
- **Containerization**: Docker support with multi-stage builds

## Quick Start

### Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- PostgreSQL (for database)
- Redis (for caching)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd production-api-framework
```

2. Install dependencies:
```bash
poetry install
```

3. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Set up secrets (optional):
```bash
cp config/.secrets.toml.example config/.secrets.toml
# Edit .secrets.toml with your secrets
```

### Configuration

The application uses hierarchical configuration management:

1. **Default settings**: `config/settings.toml`
2. **Environment-specific**: `config/environments/{env}.toml`
3. **Secrets**: `config/.secrets.toml` (optional)
4. **Environment variables**: `.env` file or system environment

### Running the Application

```bash
# Development
poetry run uvicorn src.main:app --reload

# Production
poetry run uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Configuration Management

Use the configuration management CLI:

```bash
# Validate configuration
poetry run python scripts/config_manager.py validate

# Show configuration info
poetry run python scripts/config_manager.py info

# Initialize secrets file
poetry run python scripts/config_manager.py init-secrets

# Check environment-specific configuration
poetry run python scripts/config_manager.py check-env production
```

## Development

### Code Quality

```bash
# Format code
poetry run black src tests
poetry run isort src tests

# Lint code
poetry run flake8 src tests
poetry run mypy src

# Run all quality checks
poetry run pre-commit run --all-files
```

### Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration
```

## Project Structure

```
├── src/                    # Application source code
│   ├── config/            # Configuration management
│   ├── routes/            # API routes
│   ├── controllers/       # Request controllers
│   ├── services/          # Business logic
│   ├── models/            # Database models
│   ├── schemas/           # Pydantic schemas
│   ├── middleware/        # Custom middleware
│   ├── database/          # Database utilities
│   └── utils/             # Utility functions
├── tests/                 # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── fixtures/          # Test fixtures
├── config/                # Configuration files
│   └── environments/      # Environment-specific configs
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── pyproject.toml         # Project configuration
```

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

- `API_ENV`: Environment (development, staging, production)
- `API_DATABASE_URL`: Database connection URL
- `API_SECRET_KEY`: JWT secret key
- `API_REDIS_URL`: Redis connection URL
- `API_SENTRY_DSN`: Sentry error tracking DSN

### Feature Flags

- `API_FEATURE_REGISTRATION_ENABLED`: Enable user registration
- `API_FEATURE_EMAIL_VERIFICATION`: Enable email verification
- `API_FEATURE_SOCIAL_LOGIN`: Enable social login

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and quality checks
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.