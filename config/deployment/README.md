# Deployment Configuration

This directory contains deployment-specific configuration templates and examples for different deployment scenarios.

## Files

### Environment Variable Templates

- **`.env.docker.example`** - Docker deployment environment variables
- **`.env.kubernetes.example`** - Kubernetes deployment environment variables  
- **`.env.cloud-run.example`** - Google Cloud Run deployment environment variables

### Usage

1. **Copy the appropriate template** for your deployment type:
   ```bash
   # For Docker deployment
   cp config/deployment/.env.docker.example .env.docker
   
   # For Kubernetes deployment
   cp config/deployment/.env.kubernetes.example .env.kubernetes
   
   # For Cloud Run deployment
   cp config/deployment/.env.cloud-run.example .env.cloudrun
   ```

2. **Edit the configuration** with your actual values:
   ```bash
   vim .env.docker  # or your preferred editor
   ```

3. **Validate the configuration**:
   ```bash
   python scripts/validate-deployment.py --deployment-type docker
   ```

## Quick Setup

Use the deployment configuration CLI tool for automated setup:

```bash
# Setup Docker development environment
python scripts/deployment-config.py setup docker development

# Setup Kubernetes production environment
python scripts/deployment-config.py setup kubernetes production

# Setup Cloud Run staging environment
python scripts/deployment-config.py setup cloud_run staging
```

## Environment-Specific Configurations

### Development
- Debug mode enabled
- Verbose logging
- Local database connections
- Relaxed security settings

### Staging
- Production-like settings
- Moderate logging
- External service connections
- Security enabled

### Production
- Optimized performance
- Minimal logging
- Secure configurations
- All monitoring enabled

## Security Notes

⚠️ **Important Security Considerations:**

1. **Never commit actual secrets** to version control
2. **Use strong, unique secret keys** for each environment
3. **Configure CORS origins** explicitly for production
4. **Enable HTTPS** at the load balancer level
5. **Use secure secret management** systems (Kubernetes Secrets, Cloud Secret Manager, etc.)

## Validation

Always validate your configuration before deployment:

```bash
# Validate current configuration
python scripts/validate-deployment.py

# Validate specific deployment
python scripts/validate-deployment.py --deployment-type kubernetes --environment production

# Get detailed validation output
python scripts/validate-deployment.py --verbose
```

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**
   - Check the validation output for required variables
   - Ensure all secrets are properly configured

2. **Database Connection Issues**
   - Verify database URL format
   - Check network connectivity
   - Ensure async driver is used (asyncpg for PostgreSQL)

3. **Docker Networking**
   - Use service names instead of localhost
   - Ensure API_HOST=0.0.0.0 for Docker

4. **Kubernetes Issues**
   - Verify ConfigMaps and Secrets are mounted
   - Check health check probe configuration
   - Ensure proper resource limits

### Debug Commands

```bash
# Show current deployment configuration
python scripts/deployment-config.py current

# List all available configurations
python scripts/deployment-config.py list

# Generate environment file for testing
python scripts/deployment-config.py generate-env docker development --output .env.test
```

For more detailed information, see the [Deployment Guide](../../docs/deployment.md).