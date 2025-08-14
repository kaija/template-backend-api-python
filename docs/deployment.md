# Deployment Configuration Guide

This guide covers environment-based deployment configuration for the Production API Framework, including setup for different deployment scenarios and environments.

## Overview

The framework supports multiple deployment types and environments with automatic configuration detection and validation:

- **Deployment Types**: Local, Docker, Kubernetes, Cloud Run, Heroku, Serverless
- **Environments**: Development, Staging, Production, Test
- **Configuration Sources**: Environment variables, TOML files, secrets management

## Quick Start

### 1. Validate Current Configuration

```bash
# Validate current deployment configuration
python scripts/validate-deployment.py

# Validate specific environment
python scripts/validate-deployment.py --environment production

# Validate specific deployment type
python scripts/validate-deployment.py --deployment-type kubernetes --verbose
```

### 2. Environment Detection

The framework automatically detects the deployment environment and type:

```python
from src.config.deployment import deployment_manager

# Get current deployment info
info = deployment_manager.get_deployment_info()
print(f"Environment: {info['environment']}")
print(f"Deployment Type: {info['deployment_type']}")
```

## Deployment Types

### Local Development

**Detection**: Default when no other deployment indicators are found.

**Configuration Files**:
- `config/environments/development.toml`
- `.env` (copy from `.env.example`)

**Required Environment Variables**:
```bash
API_DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/api_dev"
API_SECRET_KEY="development-secret-key-replace-in-production"
```

**Setup**:
```bash
# Copy environment file
cp .env.example .env

# Edit configuration
vim .env

# Validate configuration
python scripts/validate-deployment.py --environment development
```

### Docker Development

**Detection**: Presence of `/.dockerenv` file or `DOCKER_CONTAINER` environment variable.

**Configuration Files**:
- `config/environments/docker-development.toml`
- `config/deployment/.env.docker.example`

**Required Environment Variables**:
```bash
API_DATABASE_URL="postgresql+asyncpg://api_user:api_password@postgres:5432/api_db"
API_SECRET_KEY="docker-development-secret-key"
API_REDIS_URL="redis://redis:6379/0"
```

**Setup**:
```bash
# Copy Docker environment file
cp config/deployment/.env.docker.example .env.docker

# Edit configuration
vim .env.docker

# Start with Docker Compose
docker-compose up -d

# Validate configuration
python scripts/validate-deployment.py --deployment-type docker
```

### Docker Production

**Detection**: Docker environment with `API_ENV=production`.

**Configuration Files**:
- `config/environments/docker-production.toml`
- `docker-compose.prod.yml`

**Required Environment Variables**:
```bash
API_ENV=production
API_DATABASE_URL="postgresql+asyncpg://user:secure_password@postgres:5432/api_prod"
API_SECRET_KEY="production-secret-key-must-be-cryptographically-secure"
API_REDIS_URL="redis://redis:6379/0"
API_SENTRY_DSN="https://your-sentry-dsn@sentry.io/project-id"
```

**Setup**:
```bash
# Create production environment file
cp config/deployment/.env.docker.example .env.prod
vim .env.prod

# Deploy with production compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Validate configuration
python scripts/validate-deployment.py --environment production --deployment-type docker
```

### Kubernetes

**Detection**: Presence of `KUBERNETES_SERVICE_HOST` environment variable.

**Configuration Files**:
- `config/environments/kubernetes.toml`
- `config/deployment/.env.kubernetes.example`

**Required Environment Variables**:
```bash
API_ENV=production
API_DATABASE_URL="postgresql+asyncpg://api_user:${DB_PASSWORD}@postgres-service:5432/api_db"
API_SECRET_KEY="${JWT_SECRET_KEY}"
API_REDIS_URL="redis://redis-service:6379/0"
API_SENTRY_DSN="${SENTRY_DSN}"
```

**Setup**:

1. **Create ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
data:
  API_ENV: "production"
  API_LOG_LEVEL: "INFO"
  API_LOG_FORMAT: "json"
  API_WORKERS: "4"
  API_CORS_ORIGINS: "https://yourdomain.com"
```

2. **Create Secrets**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
type: Opaque
stringData:
  API_SECRET_KEY: "your-cryptographically-secure-secret-key"
  API_DATABASE_URL: "postgresql+asyncpg://user:password@postgres:5432/api_db"
  API_SENTRY_DSN: "https://your-sentry-dsn@sentry.io/project-id"
```

3. **Deploy Application**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
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
        envFrom:
        - configMapRef:
            name: api-config
        - secretRef:
            name: api-secrets
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Google Cloud Run

**Detection**: Presence of `K_SERVICE` or `GOOGLE_CLOUD_PROJECT` environment variables.

**Configuration Files**:
- `config/environments/kubernetes.toml` (reused)
- `config/deployment/.env.cloud-run.example`

**Required Environment Variables**:
```bash
API_ENV=production
PORT=8080  # Automatically set by Cloud Run
API_DATABASE_URL="postgresql+asyncpg://user:password@/db?host=/cloudsql/project:region:instance"
API_SECRET_KEY="${JWT_SECRET_KEY}"
API_REDIS_URL="redis://${REDIS_HOST}:6379/0"
API_SENTRY_DSN="${SENTRY_DSN}"
```

**Setup**:

1. **Deploy with gcloud**:
```bash
# Build and deploy
gcloud run deploy api \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars API_ENV=production \
  --set-env-vars API_LOG_LEVEL=INFO \
  --set-secrets API_SECRET_KEY=jwt-secret:latest \
  --set-secrets API_DATABASE_URL=db-url:latest \
  --set-secrets API_SENTRY_DSN=sentry-dsn:latest \
  --allow-unauthenticated
```

2. **Using Cloud Run YAML**:
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: api
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/cloudsql-instances: project:region:instance
    spec:
      containers:
      - image: gcr.io/project/api:latest
        ports:
        - containerPort: 8080
        env:
        - name: API_ENV
          value: "production"
        - name: API_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: latest
```

### Heroku

**Detection**: Presence of `DYNO` or `HEROKU_APP_NAME` environment variables.

**Configuration Files**:
- `config/environments/production.toml`

**Required Environment Variables**:
```bash
API_ENV=production
PORT=5000  # Automatically set by Heroku
DATABASE_URL="postgres://user:password@host:5432/db"  # Automatically set
REDIS_URL="redis://host:port"  # Set by Redis addon
API_SECRET_KEY="your-secret-key"
API_SENTRY_DSN="https://your-sentry-dsn@sentry.io/project-id"
```

**Setup**:

1. **Create Heroku App**:
```bash
# Create app
heroku create your-api-app

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Add Redis
heroku addons:create heroku-redis:hobby-dev

# Set environment variables
heroku config:set API_ENV=production
heroku config:set API_SECRET_KEY=$(openssl rand -hex 32)
heroku config:set API_SENTRY_DSN=your-sentry-dsn

# Deploy
git push heroku main
```

2. **Procfile**:
```
web: python -m src.main
release: python -m alembic upgrade head
```

## Environment Variables Reference

### Core Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_ENV` | Yes | `development` | Environment name |
| `API_DEBUG` | No | `false` | Enable debug mode |
| `API_HOST` | No | `0.0.0.0` | Server host |
| `API_PORT` | No | `8000` | Server port |
| `API_LOG_LEVEL` | No | `INFO` | Logging level |
| `API_LOG_FORMAT` | No | `json` | Log format |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_DATABASE_URL` | Yes | - | Database connection URL |
| `API_DB_POOL_SIZE` | No | `10` | Connection pool size |
| `API_DB_MAX_OVERFLOW` | No | `20` | Max pool overflow |
| `API_DB_POOL_TIMEOUT` | No | `30` | Pool timeout (seconds) |

### Security Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_SECRET_KEY` | Yes | - | JWT secret key |
| `API_ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Token expiration |
| `API_CORS_ORIGINS` | No | `[]` | Allowed CORS origins |

### Monitoring Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_SENTRY_DSN` | No | - | Sentry error tracking DSN |
| `API_METRICS_ENABLED` | No | `true` | Enable Prometheus metrics |
| `API_SENTRY_ENVIRONMENT` | No | `${API_ENV}` | Sentry environment tag |

## Configuration Validation

### Automatic Validation

The framework automatically validates configuration on startup:

```python
from src.config.deployment import validate_deployment

# Validate current deployment
results = validate_deployment()
if not results["valid"]:
    print("Configuration errors:", results["errors"])
```

### Manual Validation

Use the validation script for detailed checks:

```bash
# Basic validation
python scripts/validate-deployment.py

# Verbose output
python scripts/validate-deployment.py --verbose

# Exit with error code on failure
python scripts/validate-deployment.py --exit-on-error

# Validate specific configuration
python scripts/validate-deployment.py \
  --environment production \
  --deployment-type kubernetes \
  --verbose
```

### Validation Rules

#### Development Environment
- Secret key minimum 32 characters
- Debug mode allowed
- Localhost connections allowed

#### Staging Environment
- Secret key minimum 32 characters
- Debug mode disabled
- Sentry DSN recommended
- Production-like settings

#### Production Environment
- Secret key minimum 64 characters
- Debug mode disabled
- Sentry DSN required
- HTTPS required (at load balancer level)
- Secure CORS configuration

## Configuration Override Hierarchy

Configuration is loaded in the following order (later sources override earlier ones):

1. **Default settings** (`config/settings.toml`)
2. **Environment-specific settings** (`config/environments/{environment}.toml`)
3. **Deployment-specific settings** (`config/environments/{deployment-type}.toml`)
4. **Secrets file** (`config/.secrets.toml`)
5. **Environment variables** (`API_*` prefixed)
6. **Deployment overrides** (programmatic overrides)

## Best Practices

### Security
- Use strong, unique secret keys for each environment
- Store secrets in secure secret management systems
- Disable debug mode in production
- Configure CORS origins explicitly
- Use HTTPS in production (configure at load balancer level)

### Performance
- Adjust worker count based on deployment type
- Configure appropriate database pool sizes
- Set reasonable request timeouts
- Enable connection pooling

### Monitoring
- Configure Sentry for error tracking in staging/production
- Enable Prometheus metrics
- Set up proper health checks
- Use structured JSON logging in production

### Deployment
- Validate configuration before deployment
- Use infrastructure as code (Kubernetes YAML, Terraform)
- Implement proper CI/CD pipelines
- Test deployments in staging first

## Troubleshooting

### Common Issues

1. **Configuration Validation Fails**
   ```bash
   # Check specific validation errors
   python scripts/validate-deployment.py --verbose
   ```

2. **Database Connection Issues**
   ```bash
   # Test database connection
   python -c "from src.config.settings import get_database_url; print(get_database_url())"
   ```

3. **Environment Detection Issues**
   ```bash
   # Check environment detection
   python -c "from src.config.deployment import deployment_manager; deployment_manager.print_deployment_summary()"
   ```

4. **Docker Networking Issues**
   - Use service names instead of `localhost`
   - Ensure `API_HOST=0.0.0.0` for Docker deployments
   - Check Docker network configuration

5. **Kubernetes Issues**
   - Verify ConfigMaps and Secrets are properly mounted
   - Check health check probe configuration
   - Ensure proper RBAC permissions

### Debug Commands

```bash
# Print current configuration
python -c "from src.config.settings import print_configuration_summary; print_configuration_summary()"

# Print deployment information
python -c "from src.config.deployment import deployment_manager; deployment_manager.print_deployment_summary()"

# Print environment information
python -c "from src.config.environment import print_environment_info; print_environment_info()"

# Validate specific deployment
python scripts/validate-deployment.py --deployment-type docker --environment production --verbose
```

## Migration Guide

### From Environment Variables Only

1. **Identify current variables**:
   ```bash
   env | grep API_ | sort
   ```

2. **Create environment-specific TOML file**:
   ```toml
   [default]
   debug = false
   log_level = "INFO"
   # ... other settings
   ```

3. **Update deployment scripts** to use new configuration system

4. **Validate new configuration**:
   ```bash
   python scripts/validate-deployment.py
   ```

### From Single Configuration File

1. **Split configuration** by environment
2. **Move secrets** to separate files or environment variables
3. **Update deployment scripts** to use environment-specific files
4. **Test each environment** separately

## Examples

See the `config/deployment/` directory for complete examples of environment variable configurations for different deployment scenarios.