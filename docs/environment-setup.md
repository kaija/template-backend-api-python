# Environment Setup Guide

This guide provides detailed instructions for setting up different environments (development, staging, production) and managing configuration for the Production API Framework.

## Table of Contents

- [Environment Overview](#environment-overview)
- [Development Environment](#development-environment)
- [Staging Environment](#staging-environment)
- [Production Environment](#production-environment)
- [Configuration Management](#configuration-management)
- [Environment Variables Reference](#environment-variables-reference)
- [Security Considerations](#security-considerations)
- [Troubleshooting Environment Issues](#troubleshooting-environment-issues)

## Environment Overview

The Production API Framework supports multiple environments with hierarchical configuration:

1. **Development**: Local development with debugging enabled
2. **Staging**: Production-like environment for testing
3. **Production**: Live environment with security and performance optimizations

### Configuration Hierarchy

Configuration is loaded in the following order (later sources override earlier ones):

1. Default settings (`config/settings.toml`)
2. Environment-specific settings (`config/environments/{env}.toml`)
3. Secrets file (`config/.secrets.toml`)
4. Environment variables (`.env` file or system environment)

## Development Environment

### Prerequisites

- Python 3.11+
- Poetry
- PostgreSQL 13+ (or SQLite for simple development)
- Redis 6+ (optional)
- Git

### Setup Steps

1. **Clone the repository**:
```bash
git clone <repository-url>
cd generic-api-framework
```

2. **Install Poetry** (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. **Install dependencies**:
```bash
poetry install
```

4. **Set up pre-commit hooks**:
```bash
poetry run pre-commit install
```

5. **Create development environment file**:
```bash
cp .env.example .env
```

6. **Configure development settings**:
```bash
# Edit .env file
API_ENV=development
API_DEBUG=true
API_LOG_LEVEL=DEBUG
API_DATABASE_URL=sqlite+aiosqlite:///./app.db
API_SECRET_KEY=dev-secret-key-change-in-production
API_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

7. **Initialize database**:
```bash
poetry run alembic upgrade head
```

8. **Optional: Add sample data**:
```bash
poetry run python scripts/seed.py
```

9. **Start development server**:
```bash
poetry run uvicorn src.main:app --reload
```

### Development Configuration

Create `config/environments/development.toml`:

```toml
[default]
debug = true
log_level = "DEBUG"
cors_origins = ["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"]

[database]
echo = true  # Log SQL queries
pool_size = 5
max_overflow = 10
pool_timeout = 30

[auth]
jwt_expire_minutes = 60  # Longer expiration for development
jwt_algorithm = "HS256"

[monitoring]
sentry_environment = "development"
metrics_enabled = true

[features]
registration_enabled = true
email_verification = false  # Disable for easier testing
rate_limiting = false  # Disable for development
```

### Development Tools

#### Database Management

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1

# Reset database (development only)
rm app.db
poetry run alembic upgrade head
poetry run python scripts/seed.py
```

#### Code Quality

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

#### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test categories
poetry run pytest -m unit
poetry run pytest -m integration
```

## Staging Environment

### Purpose

The staging environment should mirror production as closely as possible while allowing for testing and validation.

### Setup Steps

1. **Provision staging infrastructure**:
   - Database server (PostgreSQL)
   - Redis server
   - Application server
   - Load balancer (optional)

2. **Create staging configuration**:

Create `config/environments/staging.toml`:

```toml
[default]
debug = false
log_level = "INFO"
cors_origins = ["https://staging-frontend.example.com"]

[database]
echo = false
pool_size = 10
max_overflow = 20
pool_timeout = 30
pool_recycle = 3600

[auth]
jwt_expire_minutes = 30
jwt_algorithm = "HS256"

[monitoring]
sentry_environment = "staging"
metrics_enabled = true

[features]
registration_enabled = true
email_verification = true
rate_limiting = true

[security]
cors_allow_credentials = true
security_headers_enabled = true
```

3. **Set up environment variables**:

Create `.env.staging`:

```bash
# Application
API_ENV=staging
API_DEBUG=false
API_LOG_LEVEL=INFO

# Database
API_DATABASE_URL=postgresql+asyncpg://staging_user:password@staging-db:5432/staging_db

# Security
API_SECRET_KEY=staging-secret-key-32-chars-minimum
API_JWT_SECRET=staging-jwt-secret-key

# External Services
API_REDIS_URL=redis://staging-redis:6379/0
API_SENTRY_DSN=https://your-sentry-dsn@sentry.io/staging-project

# Email (if using)
API_SMTP_HOST=smtp.example.com
API_SMTP_PORT=587
API_SMTP_USERNAME=staging@example.com
API_SMTP_PASSWORD=smtp-password

# Feature Flags
API_FEATURE_REGISTRATION_ENABLED=true
API_FEATURE_EMAIL_VERIFICATION=true
```

4. **Deploy to staging**:

```bash
# Using Docker
docker build -t api-framework:staging .
docker run -d \
  --name api-framework-staging \
  --env-file .env.staging \
  -p 8000:8000 \
  api-framework:staging

# Or using systemd service
sudo systemctl start api-framework-staging
```

5. **Run migrations**:

```bash
API_ENV=staging poetry run alembic upgrade head
```

6. **Verify deployment**:

```bash
# Health checks
curl https://staging-api.example.com/healthz
curl https://staging-api.example.com/readyz

# API documentation
curl https://staging-api.example.com/docs
```

### Staging Testing

```bash
# Run integration tests against staging
API_BASE_URL=https://staging-api.example.com poetry run pytest tests/integration/

# Load testing
poetry run locust -f tests/load/locustfile.py --host=https://staging-api.example.com
```

## Production Environment

### Prerequisites

- Secure server infrastructure
- SSL/TLS certificates
- Database backup strategy
- Monitoring and alerting setup
- Log aggregation system

### Security Hardening

1. **Server Security**:
   - Disable root login
   - Use SSH keys only
   - Configure firewall
   - Enable automatic security updates
   - Use fail2ban for intrusion prevention

2. **Application Security**:
   - Use strong secret keys (32+ characters)
   - Enable HTTPS only
   - Configure security headers
   - Set up rate limiting
   - Enable audit logging

### Production Configuration

Create `config/environments/production.toml`:

```toml
[default]
debug = false
log_level = "WARNING"
cors_origins = ["https://app.example.com", "https://www.example.com"]

[database]
echo = false
pool_size = 20
max_overflow = 30
pool_timeout = 30
pool_recycle = 3600
pool_pre_ping = true

[auth]
jwt_expire_minutes = 15  # Shorter for security
jwt_algorithm = "HS256"

[monitoring]
sentry_environment = "production"
metrics_enabled = true
log_retention_days = 90

[features]
registration_enabled = true
email_verification = true
rate_limiting = true

[security]
cors_allow_credentials = true
security_headers_enabled = true
force_https = true
session_cookie_secure = true
session_cookie_httponly = true
```

### Production Environment Variables

Create `.env.production` (or use system environment variables):

```bash
# Application
API_ENV=production
API_DEBUG=false
API_LOG_LEVEL=WARNING

# Database (use connection pooling service if available)
API_DATABASE_URL=postgresql+asyncpg://prod_user:secure_password@prod-db:5432/prod_db

# Security (use strong, unique keys)
API_SECRET_KEY=production-secret-key-minimum-32-characters-long
API_JWT_SECRET=production-jwt-secret-key-minimum-32-characters

# External Services
API_REDIS_URL=redis://prod-redis:6379/0
API_SENTRY_DSN=https://your-sentry-dsn@sentry.io/production-project

# Email
API_SMTP_HOST=smtp.example.com
API_SMTP_PORT=587
API_SMTP_USERNAME=noreply@example.com
API_SMTP_PASSWORD=secure-smtp-password

# Monitoring
API_PROMETHEUS_ENABLED=true
API_METRICS_PORT=9090

# Feature Flags
API_FEATURE_REGISTRATION_ENABLED=true
API_FEATURE_EMAIL_VERIFICATION=true
```

### Production Deployment

#### Using Docker

1. **Build production image**:
```bash
docker build -t api-framework:production .
```

2. **Run with Docker Compose**:

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    image: api-framework:production
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - API_ENV=production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      POSTGRES_DB: prod_db
      POSTGRES_USER: prod_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass redis_password

volumes:
  postgres_data:
```

3. **Deploy**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### Using Systemd Service

1. **Create service file** (`/etc/systemd/system/api-framework.service`):

```ini
[Unit]
Description=Production API Framework
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=api-user
Group=api-user
WorkingDirectory=/opt/api-framework
Environment=API_ENV=production
EnvironmentFile=/opt/api-framework/.env.production
ExecStart=/opt/api-framework/.venv/bin/gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

2. **Enable and start service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable api-framework
sudo systemctl start api-framework
```

### Production Monitoring

1. **Health Checks**:
```bash
# Set up monitoring for these endpoints
curl https://api.example.com/healthz
curl https://api.example.com/readyz
```

2. **Metrics Collection**:
```bash
# Prometheus scraping configuration
curl https://api.example.com/metrics
```

3. **Log Monitoring**:
```bash
# Centralized logging (e.g., ELK stack, Fluentd)
tail -f /var/log/api-framework/app.log
```

## Configuration Management

### Using the Configuration CLI

The framework includes a configuration management CLI:

```bash
# Validate current configuration
poetry run python scripts/config_manager.py validate

# Show configuration information
poetry run python scripts/config_manager.py info

# List all configuration keys
poetry run python scripts/config_manager.py list-keys

# Check environment-specific configuration
poetry run python scripts/config_manager.py check-env production

# Initialize secrets file
poetry run python scripts/config_manager.py init-secrets
```

### Secrets Management

#### Development Secrets

Create `config/.secrets.toml` for local development:

```toml
[default]
secret_key = "development-secret-key-32-characters"
jwt_secret = "development-jwt-secret-key"
database_password = "dev_password"

[development]
sentry_dsn = "https://dev-sentry-dsn@sentry.io/dev-project"
```

#### Production Secrets

For production, use one of these approaches:

1. **Environment Variables** (recommended):
```bash
export API_SECRET_KEY="production-secret-key"
export API_JWT_SECRET="production-jwt-secret"
export API_DATABASE_PASSWORD="secure-db-password"
```

2. **Secrets Management Service**:
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Google Secret Manager

3. **Encrypted Secrets File**:
```bash
# Encrypt secrets file
gpg --symmetric --cipher-algo AES256 config/.secrets.toml

# Decrypt at runtime
gpg --quiet --batch --yes --decrypt --passphrase="$GPG_PASSPHRASE" \
    config/.secrets.toml.gpg > config/.secrets.toml
```

### Configuration Validation

Create configuration validation schemas:

```python
# src/config/validation.py
from pydantic import BaseSettings, validator
from typing import List, Optional

class DatabaseSettings(BaseSettings):
    url: str
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 20
    
    @validator('url')
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'sqlite://')):
            raise ValueError('Database URL must use postgresql:// or sqlite://')
        return v

class SecuritySettings(BaseSettings):
    secret_key: str
    jwt_secret: str
    jwt_expire_minutes: int = 30
    
    @validator('secret_key', 'jwt_secret')
    def validate_key_length(cls, v):
        if len(v) < 32:
            raise ValueError('Security keys must be at least 32 characters')
        return v

class AppSettings(BaseSettings):
    env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    cors_origins: List[str] = []
    
    database: DatabaseSettings
    security: SecuritySettings
    
    @validator('env')
    def validate_environment(cls, v):
        if v not in ['development', 'staging', 'production']:
            raise ValueError('Environment must be development, staging, or production')
        return v
```

## Environment Variables Reference

### Core Application Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_ENV` | Environment name | `development` | Yes |
| `API_DEBUG` | Enable debug mode | `false` | No |
| `API_LOG_LEVEL` | Logging level | `INFO` | No |
| `API_HOST` | Server host | `0.0.0.0` | No |
| `API_PORT` | Server port | `8000` | No |

### Database Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_DATABASE_URL` | Database connection URL | - | Yes |
| `API_DATABASE_ECHO` | Log SQL queries | `false` | No |
| `API_DATABASE_POOL_SIZE` | Connection pool size | `10` | No |
| `API_DATABASE_MAX_OVERFLOW` | Max overflow connections | `20` | No |

### Security Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_SECRET_KEY` | Application secret key | - | Yes |
| `API_JWT_SECRET` | JWT signing secret | - | Yes |
| `API_JWT_ALGORITHM` | JWT algorithm | `HS256` | No |
| `API_JWT_EXPIRE_MINUTES` | JWT expiration time | `30` | No |

### External Services

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_REDIS_URL` | Redis connection URL | - | No |
| `API_SENTRY_DSN` | Sentry error tracking DSN | - | No |
| `API_SMTP_HOST` | SMTP server host | - | No |
| `API_SMTP_PORT` | SMTP server port | `587` | No |
| `API_SMTP_USERNAME` | SMTP username | - | No |
| `API_SMTP_PASSWORD` | SMTP password | - | No |

### CORS Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_CORS_ORIGINS` | Allowed CORS origins | `[]` | No |
| `API_CORS_ALLOW_CREDENTIALS` | Allow credentials | `true` | No |
| `API_CORS_ALLOW_METHODS` | Allowed methods | `["*"]` | No |
| `API_CORS_ALLOW_HEADERS` | Allowed headers | `["*"]` | No |

### Feature Flags

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `API_FEATURE_REGISTRATION_ENABLED` | Enable user registration | `true` | No |
| `API_FEATURE_EMAIL_VERIFICATION` | Enable email verification | `false` | No |
| `API_FEATURE_RATE_LIMITING` | Enable rate limiting | `true` | No |

## Security Considerations

### Secret Key Management

1. **Generate Strong Keys**:
```bash
# Generate secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or use OpenSSL
openssl rand -base64 32
```

2. **Key Rotation**:
   - Rotate keys regularly (quarterly for production)
   - Use multiple keys for zero-downtime rotation
   - Store old keys temporarily for token validation

3. **Key Storage**:
   - Never commit secrets to version control
   - Use environment variables or secrets management
   - Encrypt secrets at rest

### Environment Isolation

1. **Network Isolation**:
   - Use separate networks for each environment
   - Implement firewall rules
   - Use VPNs for staging/production access

2. **Database Isolation**:
   - Separate database instances per environment
   - Use different credentials for each environment
   - Implement backup and recovery procedures

3. **Access Control**:
   - Use different service accounts per environment
   - Implement least privilege access
   - Enable audit logging

## Troubleshooting Environment Issues

### Configuration Not Loading

1. **Check environment detection**:
```bash
poetry run python -c "from src.config.settings import settings; print(f'Environment: {settings.ENV}')"
```

2. **Validate configuration files**:
```bash
poetry run python scripts/config_manager.py validate
```

3. **Check file permissions**:
```bash
ls -la config/
ls -la .env*
```

### Environment Variables Not Working

1. **Check variable names** (case-sensitive):
```bash
env | grep API_ | sort
```

2. **Test variable loading**:
```bash
poetry run python -c "
import os
from src.config.settings import settings
print(f'From env: {os.getenv(\"API_SECRET_KEY\", \"Not found\")}')
print(f'From settings: {getattr(settings, \"SECRET_KEY\", \"Not found\")}')
"
```

### Database Connection Issues

1. **Test connection string**:
```bash
poetry run python -c "
from sqlalchemy import create_engine
from src.config.settings import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('Connection successful')
"
```

2. **Check database server**:
```bash
# PostgreSQL
pg_isready -h localhost -p 5432

# Test with psql
psql -h localhost -U username -d database_name -c "SELECT version();"
```

For additional troubleshooting, refer to the [Troubleshooting Guide](troubleshooting.md).