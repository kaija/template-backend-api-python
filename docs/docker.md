# Docker Deployment Guide

This guide covers containerization and deployment options for the FastAPI application using Docker and Docker Compose.

## Overview

The application provides multiple Docker configurations:

- **Development**: Hot reload, debugging tools, mounted volumes
- **Production**: Optimized images, security hardening, resource limits
- **Monitoring**: Prometheus, Grafana for observability
- **Tools**: Database admin, Redis management

## Quick Start

### Development Environment

```bash
# Start all services
make docker-up

# View logs
make docker-logs

# Stop services
make docker-down
```

### Production Environment

```bash
# Start production services
make docker-prod-up

# Stop production services
make docker-prod-down
```

## Docker Files

### Dockerfile

Multi-stage build optimized for production:

- **Builder stage**: Installs Poetry and exports dependencies
- **Production stage**: Minimal runtime image with security hardening
- **Non-root user**: Runs as `appuser` for security
- **Health checks**: Built-in health monitoring
- **Signal handling**: Proper graceful shutdown

### docker-compose.yml

Main development configuration:

- **API service**: FastAPI application with hot reload
- **PostgreSQL**: Database with health checks
- **Redis**: Caching layer
- **Migration service**: Automatic database setup

### docker-compose.prod.yml

Production overrides:

- **Resource limits**: CPU and memory constraints
- **Replicas**: Multiple API instances
- **Nginx**: Reverse proxy with rate limiting
- **No volume mounts**: Immutable containers

## Services

### API Application

```yaml
api:
  build: .
  ports:
    - "8000:8000"
  environment:
    - ENV_FOR_DYNACONF=development
    - DATABASE_URL=postgresql+asyncpg://api_user:api_password@postgres:5432/api_db
  depends_on:
    - postgres
    - redis
```

**Environment Variables:**
- `ENV_FOR_DYNACONF`: Environment profile (development/staging/production)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SENTRY_DSN`: Error tracking (optional)
- `SECRET_KEY`: Application secret key

### PostgreSQL Database

```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_DB: api_db
    POSTGRES_USER: api_user
    POSTGRES_PASSWORD: api_password
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

**Features:**
- Alpine Linux for minimal size
- Persistent data storage
- Health checks
- Initialization scripts

### Redis Cache

```yaml
redis:
  image: redis:7-alpine
  volumes:
    - redis_data:/data
  command: redis-server --appendonly yes --maxmemory 256mb
```

**Configuration:**
- Persistent storage with AOF
- Memory limit: 256MB
- LRU eviction policy

## Profiles

### Development Tools

```bash
# Start with database admin and Redis management
make docker-dev-tools
```

**Includes:**
- **Adminer**: Database administration at http://localhost:8080
- **Redis Commander**: Redis management at http://localhost:8081

### Monitoring Stack

```bash
# Start with monitoring tools
make docker-monitoring
```

**Includes:**
- **Prometheus**: Metrics collection at http://localhost:9090
- **Grafana**: Visualization at http://localhost:3000 (admin/admin)

## Production Deployment

### Environment Variables

Create a `.env` file for production:

```bash
# Application
ENV_FOR_DYNACONF=production
SECRET_KEY=your-secret-key-here
DEBUG=false

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
POSTGRES_DB=api_db
POSTGRES_USER=api_user
POSTGRES_PASSWORD=secure-password

# Cache
REDIS_URL=redis://redis:6379/0

# Monitoring
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project

# Security
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### SSL/TLS Configuration

For HTTPS in production, update `config/nginx.conf`:

1. Uncomment the HTTPS server block
2. Add SSL certificates to `config/ssl/`
3. Update domain names

### Resource Limits

Production services include resource constraints:

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      cpus: '0.5'
      memory: 256M
```

## Health Checks

### Application Health

- **Liveness**: `/healthz` - Application is running
- **Readiness**: `/readyz` - Application can serve traffic

### Container Health

Docker health checks monitor:
- HTTP endpoint availability
- Database connectivity
- Redis connectivity

### Monitoring Health

```bash
# Check service status
make docker-status

# View health check logs
docker-compose logs api | grep health
```

## Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check database status
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

**Application Won't Start**
```bash
# Check application logs
docker-compose logs api

# Check environment variables
docker-compose exec api env | grep -E "(DATABASE|REDIS)"
```

**Permission Denied**
```bash
# Fix file permissions
chmod +x scripts/docker-entrypoint.sh

# Rebuild image
make docker-build
```

### Performance Tuning

**Database Performance**
```yaml
postgres:
  environment:
    POSTGRES_SHARED_PRELOAD_LIBRARIES: pg_stat_statements
    POSTGRES_MAX_CONNECTIONS: 100
    POSTGRES_SHARED_BUFFERS: 256MB
```

**Redis Performance**
```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru --save 900 1
```

**Application Performance**
```yaml
api:
  environment:
    UVICORN_WORKERS: 4
    UVICORN_MAX_REQUESTS: 1000
    UVICORN_MAX_REQUESTS_JITTER: 100
```

## Security Considerations

### Container Security

- **Non-root user**: Application runs as `appuser`
- **Read-only filesystem**: Minimal write permissions
- **Security scanning**: Regular image vulnerability scans
- **Secrets management**: Environment variables, not embedded

### Network Security

- **Internal networks**: Services communicate on private network
- **Port exposure**: Only necessary ports exposed
- **Rate limiting**: Nginx configuration includes rate limits
- **CORS**: Configurable cross-origin policies

### Production Hardening

```dockerfile
# Security headers
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser appuser
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U api_user api_db > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U api_user api_db < backup.sql
```

### Volume Backup

```bash
# Backup volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore volumes
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

## CI/CD Integration

### Build Pipeline

```yaml
# Example GitHub Actions
- name: Build Docker image
  run: docker build -t api:${{ github.sha }} .

- name: Run tests
  run: docker run --rm api:${{ github.sha }} pytest

- name: Push to registry
  run: docker push api:${{ github.sha }}
```

### Deployment Pipeline

```yaml
- name: Deploy to production
  run: |
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Monitoring and Logging

### Log Aggregation

```yaml
api:
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

### Metrics Collection

Prometheus scrapes metrics from:
- `/metrics` endpoint
- Container metrics
- Database metrics (with exporters)

### Alerting

Configure alerts for:
- High error rates
- Database connection failures
- Memory/CPU usage
- Disk space

## Development Workflow

### Local Development

```bash
# Start development environment
make docker-up

# Make code changes (hot reload enabled)
# Test changes
make docker-test

# View logs
make docker-logs

# Clean up
make docker-down
```

### Testing

```bash
# Run tests in container
make docker-test

# Run specific test suite
docker-compose exec api pytest tests/unit/

# Run with coverage
docker-compose exec api pytest --cov=src
```

### Database Operations

```bash
# Run migrations
make docker-migrate

# Access database
docker-compose exec postgres psql -U api_user api_db

# Reset database
make docker-reset
```