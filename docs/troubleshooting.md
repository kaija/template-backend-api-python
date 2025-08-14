# Troubleshooting Guide

This guide covers common issues you might encounter while developing, testing, or deploying the Production API Framework, along with their solutions.

## Table of Contents

- [Installation and Setup Issues](#installation-and-setup-issues)
- [Database Issues](#database-issues)
- [Configuration Issues](#configuration-issues)
- [Runtime Issues](#runtime-issues)
- [Testing Issues](#testing-issues)
- [Performance Issues](#performance-issues)
- [Docker Issues](#docker-issues)
- [Deployment Issues](#deployment-issues)
- [Monitoring and Logging Issues](#monitoring-and-logging-issues)
- [Security Issues](#security-issues)

## Installation and Setup Issues

### Poetry Installation Problems

**Problem**: `poetry: command not found`

**Solutions**:
1. Install Poetry using the official installer:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```
2. Add Poetry to your PATH:
   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
   ```
3. Verify installation:
   ```bash
   poetry --version
   ```

**Problem**: `Poetry could not find a pyproject.toml file`

**Solutions**:
1. Ensure you're in the project root directory
2. Check if `pyproject.toml` exists:
   ```bash
   ls -la pyproject.toml
   ```
3. If missing, initialize a new Poetry project:
   ```bash
   poetry init
   ```

### Python Version Issues

**Problem**: `The current project's Python requirement (>=3.11) is not compatible with some of the required packages`

**Solutions**:
1. Check your Python version:
   ```bash
   python --version
   ```
2. Install Python 3.11+ using pyenv:
   ```bash
   pyenv install 3.11.0
   pyenv local 3.11.0
   ```
3. Recreate the virtual environment:
   ```bash
   poetry env remove python
   poetry install
   ```

### Dependency Installation Issues

**Problem**: `Failed to install packages`

**Solutions**:
1. Clear Poetry cache:
   ```bash
   poetry cache clear pypi --all
   ```
2. Update Poetry:
   ```bash
   poetry self update
   ```
3. Install with verbose output to see detailed errors:
   ```bash
   poetry install -vvv
   ```
4. For specific package issues, install system dependencies:
   ```bash
   # macOS
   brew install postgresql libpq
   
   # Ubuntu/Debian
   sudo apt-get install postgresql-dev libpq-dev
   ```

## Database Issues

### Connection Issues

**Problem**: `sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) could not connect to server`

**Solutions**:
1. Check if PostgreSQL is running:
   ```bash
   # macOS
   brew services list | grep postgresql
   brew services start postgresql
   
   # Linux
   sudo systemctl status postgresql
   sudo systemctl start postgresql
   ```

2. Verify database exists:
   ```bash
   psql -l | grep your_database_name
   ```

3. Create database if missing:
   ```bash
   createdb your_database_name
   ```

4. Test connection manually:
   ```bash
   psql -h localhost -U your_username -d your_database_name
   ```

5. Check connection string in `.env`:
   ```bash
   grep DATABASE_URL .env
   ```

**Problem**: `psycopg2.OperationalError: FATAL: password authentication failed`

**Solutions**:
1. Reset PostgreSQL password:
   ```bash
   sudo -u postgres psql
   ALTER USER your_username PASSWORD 'new_password';
   \q
   ```

2. Update `.env` file with correct credentials:
   ```bash
   API_DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/dbname
   ```

3. For local development, consider using trust authentication:
   ```bash
   # Edit pg_hba.conf (location varies by system)
   sudo nano /etc/postgresql/13/main/pg_hba.conf
   # Change 'md5' to 'trust' for local connections (development only)
   ```

### Migration Issues

**Problem**: `alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'`

**Solutions**:
1. Check migration history:
   ```bash
   poetry run alembic history
   ```

2. Reset to head if corrupted:
   ```bash
   poetry run alembic stamp head
   ```

3. If migrations are completely corrupted:
   ```bash
   # Backup your data first!
   rm migrations/versions/*.py
   poetry run alembic revision --autogenerate -m "Initial migration"
   poetry run alembic upgrade head
   ```

**Problem**: `alembic.util.exc.CommandError: Target database is not up to date`

**Solutions**:
1. Check current migration:
   ```bash
   poetry run alembic current
   ```

2. Apply pending migrations:
   ```bash
   poetry run alembic upgrade head
   ```

3. If you need to rollback first:
   ```bash
   poetry run alembic downgrade -1
   poetry run alembic upgrade head
   ```

**Problem**: Migration fails with data integrity errors

**Solutions**:
1. Create a data migration to handle the constraint:
   ```bash
   poetry run alembic revision -m "Fix data integrity"
   ```

2. Edit the migration to handle existing data:
   ```python
   def upgrade():
       # Handle existing data first
       op.execute("UPDATE table_name SET column_name = 'default' WHERE column_name IS NULL")
       # Then add the constraint
       op.alter_column('table_name', 'column_name', nullable=False)
   ```

### SQLAlchemy Issues

**Problem**: `AttributeError: 'AsyncSession' object has no attribute 'query'`

**Solutions**:
1. Use SQLAlchemy 2.x syntax with `select()`:
   ```python
   # Wrong (SQLAlchemy 1.x)
   result = session.query(User).filter(User.id == 1).first()
   
   # Correct (SQLAlchemy 2.x)
   result = await session.execute(select(User).where(User.id == 1))
   user = result.scalar_one_or_none()
   ```

**Problem**: `RuntimeError: There is no current event loop in thread`

**Solutions**:
1. Ensure you're using async/await properly:
   ```python
   # Wrong
   def get_user(session, user_id):
       return session.execute(select(User).where(User.id == user_id))
   
   # Correct
   async def get_user(session, user_id):
       result = await session.execute(select(User).where(User.id == user_id))
       return result.scalar_one_or_none()
   ```

2. Use async session properly:
   ```python
   async with async_session() as session:
       result = await session.execute(select(User))
       users = result.scalars().all()
   ```

## Configuration Issues

### Environment Variable Issues

**Problem**: Configuration values not loading correctly

**Solutions**:
1. Check environment variable names (case-sensitive):
   ```bash
   env | grep API_
   ```

2. Verify `.env` file format:
   ```bash
   # Correct format
   API_DATABASE_URL=postgresql://user:pass@localhost/db
   API_SECRET_KEY=your-secret-key
   
   # Incorrect (no spaces around =)
   API_DATABASE_URL = postgresql://user:pass@localhost/db
   ```

3. Check if `.env` file is being loaded:
   ```python
   from src.config.settings import settings
   print(settings.DATABASE_URL)
   ```

4. Validate configuration:
   ```bash
   poetry run python scripts/config_manager.py validate
   ```

**Problem**: `dynaconf.validator.ValidationError: <ValidationError: 'SECRET_KEY' is required>`

**Solutions**:
1. Set required environment variables:
   ```bash
   export API_SECRET_KEY=your-super-secret-key-here
   ```

2. Create `.secrets.toml` file:
   ```toml
   [default]
   secret_key = "your-secret-key"
   ```

3. Check configuration hierarchy:
   ```bash
   poetry run python scripts/config_manager.py info
   ```

### TOML Configuration Issues

**Problem**: `toml.decoder.TomlDecodeError: Invalid TOML file`

**Solutions**:
1. Validate TOML syntax:
   ```bash
   python -c "import toml; toml.load('config/settings.toml')"
   ```

2. Common TOML syntax errors:
   ```toml
   # Wrong - unquoted strings with special characters
   database_url = postgresql://user:pass@localhost/db
   
   # Correct - quoted strings
   database_url = "postgresql://user:pass@localhost/db"
   
   # Wrong - missing quotes in arrays
   cors_origins = [http://localhost:3000, http://localhost:8080]
   
   # Correct - quoted array elements
   cors_origins = ["http://localhost:3000", "http://localhost:8080"]
   ```

## Runtime Issues

### FastAPI Startup Issues

**Problem**: `ImportError: cannot import name 'app' from 'src.main'`

**Solutions**:
1. Check if `src/main.py` exists and has an `app` variable:
   ```python
   from fastapi import FastAPI
   
   app = FastAPI()  # This must exist
   ```

2. Verify PYTHONPATH includes the project root:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

3. Use the correct import path:
   ```bash
   # Correct
   poetry run uvicorn src.main:app --reload
   
   # Wrong
   poetry run uvicorn main:app --reload
   ```

**Problem**: `OSError: [Errno 48] Address already in use`

**Solutions**:
1. Find process using the port:
   ```bash
   lsof -i :8000
   ```

2. Kill the process:
   ```bash
   kill -9 <PID>
   ```

3. Use a different port:
   ```bash
   poetry run uvicorn src.main:app --port 8001
   ```

4. For development, kill all Python processes:
   ```bash
   pkill -f python
   ```

### Authentication Issues

**Problem**: `HTTPException: 401 Unauthorized`

**Solutions**:
1. Check if JWT token is valid:
   ```bash
   # Decode JWT token (use online JWT decoder)
   echo "your-jwt-token" | base64 -d
   ```

2. Verify token expiration:
   ```python
   import jwt
   from datetime import datetime
   
   token = "your-jwt-token"
   decoded = jwt.decode(token, options={"verify_signature": False})
   exp_timestamp = decoded.get('exp')
   exp_datetime = datetime.fromtimestamp(exp_timestamp)
   print(f"Token expires at: {exp_datetime}")
   ```

3. Check secret key configuration:
   ```bash
   poetry run python -c "from src.config.settings import settings; print(len(settings.SECRET_KEY))"
   ```

**Problem**: `HTTPException: 403 Forbidden`

**Solutions**:
1. Check user permissions:
   ```python
   from src.auth.rbac import get_user_permissions
   permissions = get_user_permissions(current_user)
   print(permissions)
   ```

2. Verify RBAC configuration:
   ```python
   # Check if user has required role
   print(f"User roles: {current_user.roles}")
   print(f"Required permissions: {required_permissions}")
   ```

### CORS Issues

**Problem**: `Access to fetch at 'http://localhost:8000/api/v1/users' from origin 'http://localhost:3000' has been blocked by CORS policy`

**Solutions**:
1. Check CORS configuration:
   ```python
   from src.config.settings import settings
   print(settings.CORS_ORIGINS)
   ```

2. Add your frontend URL to CORS origins:
   ```bash
   # In .env file
   API_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
   ```

3. For development, allow all origins (not recommended for production):
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Development only
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

## Testing Issues

### Pytest Issues

**Problem**: `ImportError: No module named 'src'`

**Solutions**:
1. Ensure `pytest.ini` has correct Python path:
   ```ini
   [tool:pytest]
   pythonpath = .
   testpaths = tests
   ```

2. Install package in development mode:
   ```bash
   poetry install
   ```

3. Set PYTHONPATH explicitly:
   ```bash
   PYTHONPATH=. poetry run pytest
   ```

**Problem**: `RuntimeError: There is no current event loop in thread`

**Solutions**:
1. Use `pytest-asyncio` for async tests:
   ```python
   import pytest
   
   @pytest.mark.asyncio
   async def test_async_function():
       result = await some_async_function()
       assert result is not None
   ```

2. Configure pytest for asyncio in `pytest.ini`:
   ```ini
   [tool:pytest]
   asyncio_mode = auto
   ```

### Test Database Issues

**Problem**: `sqlalchemy.exc.InvalidRequestError: Table 'users' is already defined`

**Solutions**:
1. Use separate test database:
   ```python
   # conftest.py
   @pytest.fixture
   async def test_db():
       engine = create_async_engine("sqlite+aiosqlite:///:memory:")
       async with engine.begin() as conn:
           await conn.run_sync(Base.metadata.create_all)
       # ... rest of fixture
   ```

2. Clear metadata between tests:
   ```python
   @pytest.fixture(autouse=True)
   def clear_metadata():
       Base.metadata.clear()
   ```

**Problem**: Tests are not isolated (data persists between tests)

**Solutions**:
1. Use transaction rollback in fixtures:
   ```python
   @pytest.fixture
   async def test_session():
       async with async_session() as session:
           async with session.begin():
               yield session
               await session.rollback()
   ```

2. Truncate tables between tests:
   ```python
   @pytest.fixture(autouse=True)
   async def cleanup_database(test_session):
       yield
       # Cleanup after test
       for table in reversed(Base.metadata.sorted_tables):
           await test_session.execute(table.delete())
       await test_session.commit()
   ```

## Performance Issues

### Slow Database Queries

**Problem**: API responses are slow

**Solutions**:
1. Enable SQL query logging:
   ```bash
   API_DATABASE_ECHO=true poetry run uvicorn src.main:app --reload
   ```

2. Check for N+1 query problems:
   ```python
   # Wrong - N+1 queries
   users = await session.execute(select(User))
   for user in users.scalars():
       posts = await session.execute(select(Post).where(Post.user_id == user.id))
   
   # Correct - use joins or eager loading
   result = await session.execute(
       select(User).options(selectinload(User.posts))
   )
   users = result.scalars().all()
   ```

3. Add database indexes:
   ```python
   # In migration
   op.create_index('ix_users_email', 'users', ['email'])
   op.create_index('ix_posts_user_id', 'posts', ['user_id'])
   ```

4. Use database query profiling:
   ```sql
   EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'user@example.com';
   ```

### High Memory Usage

**Problem**: Application consuming too much memory

**Solutions**:
1. Check database connection pool settings:
   ```python
   # In database configuration
   engine = create_async_engine(
       DATABASE_URL,
       pool_size=5,        # Reduce if too high
       max_overflow=10,    # Reduce if too high
       pool_recycle=3600   # Recycle connections
   )
   ```

2. Monitor memory usage:
   ```bash
   # Using htop
   htop -p $(pgrep -f "uvicorn")
   
   # Using ps
   ps aux | grep uvicorn
   ```

3. Profile memory usage:
   ```bash
   pip install memory-profiler
   poetry run python -m memory_profiler your_script.py
   ```

### Slow Application Startup

**Problem**: Application takes too long to start

**Solutions**:
1. Check for blocking operations in startup:
   ```python
   # Wrong - blocking database check on startup
   @app.on_event("startup")
   async def startup_event():
       await check_database_connection()  # This might be slow
   
   # Better - make it non-blocking or optional
   @app.on_event("startup")
   async def startup_event():
       asyncio.create_task(check_database_connection())
   ```

2. Lazy load heavy dependencies:
   ```python
   # Wrong - import heavy modules at module level
   import heavy_module
   
   # Better - import when needed
   def function_that_needs_heavy_module():
       import heavy_module
       return heavy_module.do_something()
   ```

3. Profile startup time:
   ```bash
   time poetry run uvicorn src.main:app
   ```

## Docker Issues

### Docker Build Issues

**Problem**: `Docker build fails with "No such file or directory"`

**Solutions**:
1. Check Dockerfile paths:
   ```dockerfile
   # Ensure files exist before COPY
   COPY pyproject.toml poetry.lock ./
   COPY src/ ./src/
   ```

2. Use `.dockerignore` to exclude unnecessary files:
   ```
   .git
   .pytest_cache
   __pycache__
   *.pyc
   .env
   ```

3. Build with verbose output:
   ```bash
   docker build --no-cache --progress=plain -t api-framework .
   ```

**Problem**: `Poetry installation fails in Docker`

**Solutions**:
1. Use specific Poetry version:
   ```dockerfile
   RUN pip install poetry==1.4.2
   ```

2. Configure Poetry for Docker:
   ```dockerfile
   ENV POETRY_NO_INTERACTION=1 \
       POETRY_VENV_IN_PROJECT=1 \
       POETRY_CACHE_DIR=/tmp/poetry_cache
   ```

3. Use multi-stage build to reduce image size:
   ```dockerfile
   # Build stage
   FROM python:3.11-slim as builder
   # ... install dependencies
   
   # Production stage
   FROM python:3.11-slim
   COPY --from=builder /app/.venv /app/.venv
   ```

### Docker Compose Issues

**Problem**: `docker-compose up` fails with network errors

**Solutions**:
1. Check port conflicts:
   ```bash
   docker-compose ps
   netstat -tulpn | grep :8000
   ```

2. Recreate containers:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

3. Check service dependencies:
   ```yaml
   # docker-compose.yml
   services:
     api:
       depends_on:
         - db
         - redis
   ```

**Problem**: Database connection fails in Docker

**Solutions**:
1. Use service names for internal communication:
   ```bash
   # Wrong - using localhost
   API_DATABASE_URL=postgresql://user:pass@localhost:5432/db
   
   # Correct - using service name
   API_DATABASE_URL=postgresql://user:pass@db:5432/db
   ```

2. Wait for database to be ready:
   ```dockerfile
   # Install wait-for-it script
   ADD https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh /wait-for-it.sh
   RUN chmod +x /wait-for-it.sh
   
   # Use in command
   CMD ["/wait-for-it.sh", "db:5432", "--", "uvicorn", "src.main:app", "--host", "0.0.0.0"]
   ```

## Deployment Issues

### Environment Configuration

**Problem**: Application fails to start in production

**Solutions**:
1. Validate production configuration:
   ```bash
   API_ENV=production poetry run python scripts/config_manager.py validate
   ```

2. Check required environment variables:
   ```bash
   env | grep API_ | sort
   ```

3. Test configuration loading:
   ```python
   from src.config.settings import settings
   print(f"Environment: {settings.ENV}")
   print(f"Debug mode: {settings.DEBUG}")
   print(f"Database URL: {settings.DATABASE_URL[:20]}...")  # Don't log full URL
   ```

### SSL/TLS Issues

**Problem**: HTTPS not working properly

**Solutions**:
1. Check certificate files:
   ```bash
   openssl x509 -in cert.pem -text -noout
   ```

2. Verify certificate chain:
   ```bash
   openssl verify -CAfile ca-bundle.crt cert.pem
   ```

3. Test SSL connection:
   ```bash
   openssl s_client -connect your-domain.com:443
   ```

### Load Balancer Issues

**Problem**: Health checks failing

**Solutions**:
1. Test health endpoints directly:
   ```bash
   curl -v http://localhost:8000/healthz
   curl -v http://localhost:8000/readyz
   ```

2. Check health check configuration:
   ```python
   # Ensure health endpoints don't require authentication
   @router.get("/healthz", include_in_schema=False)
   async def health_check():
       return {"status": "healthy"}
   ```

3. Verify load balancer configuration:
   ```yaml
   # Example for AWS ALB
   HealthCheckPath: /healthz
   HealthCheckIntervalSeconds: 30
   HealthyThresholdCount: 2
   UnhealthyThresholdCount: 5
   ```

## Monitoring and Logging Issues

### Logging Issues

**Problem**: Logs not appearing or in wrong format

**Solutions**:
1. Check logging configuration:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   logger = logging.getLogger(__name__)
   logger.info("Test log message")
   ```

2. Verify log file permissions:
   ```bash
   ls -la logs/
   touch logs/app.log  # Create if doesn't exist
   ```

3. Check log level configuration:
   ```bash
   echo $API_LOG_LEVEL
   # Should be DEBUG, INFO, WARNING, ERROR, or CRITICAL
   ```

### Metrics Issues

**Problem**: Prometheus metrics not working

**Solutions**:
1. Check metrics endpoint:
   ```bash
   curl http://localhost:8000/metrics
   ```

2. Verify metrics are being recorded:
   ```python
   from src.monitoring.metrics import REQUEST_COUNT
   REQUEST_COUNT.labels(method="GET", endpoint="/test", status_code=200).inc()
   ```

3. Check Prometheus configuration:
   ```yaml
   # prometheus.yml
   scrape_configs:
     - job_name: 'api-framework'
       static_configs:
         - targets: ['localhost:8000']
       metrics_path: '/metrics'
   ```

### Sentry Issues

**Problem**: Errors not appearing in Sentry

**Solutions**:
1. Test Sentry configuration:
   ```python
   import sentry_sdk
   sentry_sdk.capture_message("Test message")
   ```

2. Check Sentry DSN:
   ```bash
   echo $API_SENTRY_DSN
   # Should be a valid Sentry DSN URL
   ```

3. Verify Sentry initialization:
   ```python
   from src.monitoring.sentry import init_sentry
   init_sentry()
   
   # Test error capture
   try:
       1 / 0
   except Exception as e:
       sentry_sdk.capture_exception(e)
   ```

## Security Issues

### JWT Token Issues

**Problem**: JWT tokens not working correctly

**Solutions**:
1. Verify JWT secret key:
   ```bash
   # Secret key should be at least 32 characters
   echo $API_SECRET_KEY | wc -c
   ```

2. Check token format:
   ```bash
   # JWT should have 3 parts separated by dots
   echo "your-jwt-token" | tr '.' '\n' | wc -l
   # Should output 3
   ```

3. Validate token manually:
   ```python
   import jwt
   from src.config.settings import settings
   
   token = "your-jwt-token"
   try:
       payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
       print(payload)
   except jwt.ExpiredSignatureError:
       print("Token has expired")
   except jwt.InvalidTokenError:
       print("Invalid token")
   ```

### CORS Security Issues

**Problem**: CORS blocking legitimate requests

**Solutions**:
1. Check CORS origins configuration:
   ```python
   from src.config.settings import settings
   print(f"Allowed origins: {settings.CORS_ORIGINS}")
   ```

2. Verify request headers:
   ```bash
   curl -H "Origin: http://localhost:3000" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: X-Requested-With" \
        -X OPTIONS \
        http://localhost:8000/v1/users
   ```

3. For development, temporarily allow all origins:
   ```python
   # Development only - never use in production
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

## Getting Additional Help

### Debug Mode

Enable debug mode for detailed error information:

```bash
API_DEBUG=true poetry run uvicorn src.main:app --reload
```

**Warning**: Never enable debug mode in production.

### Logging Debug Information

Increase logging verbosity:

```bash
API_LOG_LEVEL=DEBUG poetry run uvicorn src.main:app --reload
```

### Health Check Endpoints

Use health check endpoints to diagnose issues:

```bash
# Basic health
curl http://localhost:8000/healthz

# Detailed health with dependency status
curl http://localhost:8000/readyz

# Full health information
curl http://localhost:8000/health/detailed
```

### Configuration Validation

Validate your configuration:

```bash
poetry run python scripts/config_manager.py validate
poetry run python scripts/config_manager.py info
```

### Database Diagnostics

Check database connectivity:

```bash
# Test database connection
poetry run python -c "
from src.database.config import get_database_url
from sqlalchemy import create_engine
engine = create_engine(get_database_url())
with engine.connect() as conn:
    result = conn.execute('SELECT 1')
    print('Database connection successful')
"
```

### Performance Profiling

Profile your application:

```bash
# Install profiling tools
pip install py-spy memory-profiler

# Profile CPU usage
py-spy top --pid $(pgrep -f uvicorn)

# Profile memory usage
memory_profiler your_script.py
```

If you continue to experience issues not covered in this guide, consider:

1. Checking the application logs for detailed error messages
2. Reviewing the configuration files for syntax errors
3. Testing individual components in isolation
4. Consulting the FastAPI, SQLAlchemy, and other library documentation
5. Creating a minimal reproduction case to isolate the problem

Remember to never include sensitive information (passwords, API keys, etc.) when seeking help or reporting issues.