# Developer Guide

This guide covers the essential development workflows for the Production API Framework, including creating endpoints, managing database migrations, testing procedures, and following project conventions.

## Table of Contents

- [Getting Started](#getting-started)
- [Creating API Endpoints](#creating-api-endpoints)
- [Database Operations](#database-operations)
- [Testing Procedures](#testing-procedures)
- [Configuration Management](#configuration-management)
- [Authentication and Authorization](#authentication-and-authorization)
- [Error Handling](#error-handling)
- [Logging and Monitoring](#logging-and-monitoring)
- [Code Quality and Standards](#code-quality-and-standards)
- [Deployment Workflows](#deployment-workflows)

## Getting Started

### Development Environment Setup

1. **Clone and setup the project**:
```bash
git clone <repository-url>
cd production-api-framework
poetry install
poetry run pre-commit install
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your local configuration
```

3. **Initialize database**:
```bash
poetry run alembic upgrade head
poetry run python scripts/seed.py  # Optional: add sample data
```

4. **Start development server**:
```bash
poetry run uvicorn src.main:app --reload
```

### Project Architecture Overview

The project follows a layered architecture:

```
Request → Middleware → Routes → Controllers → Services → Repositories → Database
```

- **Middleware**: Cross-cutting concerns (auth, logging, error handling)
- **Routes**: URL routing and request validation
- **Controllers**: Request/response handling and coordination
- **Services**: Business logic and orchestration
- **Repositories**: Data access abstraction
- **Models**: Database entity definitions

## Creating API Endpoints

### Step 1: Define the Data Model

Create or update SQLAlchemy models in `src/database/models.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from src.database.base import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

### Step 2: Create Pydantic Schemas

Define request/response schemas in `src/schemas/`:

```python
# src/schemas/users.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
```

### Step 3: Create Repository

Implement data access in `src/database/repositories.py`:

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from src.database.models import User
from src.schemas.users import UserCreate, UserUpdate

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, user_data: UserCreate) -> User:
        user = User(**user_data.dict(exclude={'password'}))
        user.hashed_password = hash_password(user_data.password)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_by_id(self, user_id: int) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def delete(self, user_id: int) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        
        await self.session.delete(user)
        await self.session.commit()
        return True
```

### Step 4: Create Service Layer

Implement business logic in `src/services/`:

```python
# src/services/user_service.py
from typing import Optional, List
from src.database.repositories import UserRepository
from src.schemas.users import UserCreate, UserUpdate, UserResponse
from src.exceptions import UserNotFoundError, UserAlreadyExistsError

class UserService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        # Check if user already exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise UserAlreadyExistsError("User with this email already exists")
        
        # Create user
        user = await self.user_repo.create(user_data)
        return UserResponse.from_orm(user)
    
    async def get_user(self, user_id: int) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError("User not found")
        
        return UserResponse.from_orm(user)
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> UserResponse:
        user = await self.user_repo.update(user_id, user_data)
        if not user:
            raise UserNotFoundError("User not found")
        
        return UserResponse.from_orm(user)
    
    async def delete_user(self, user_id: int) -> bool:
        success = await self.user_repo.delete(user_id)
        if not success:
            raise UserNotFoundError("User not found")
        
        return True
```

### Step 5: Create Controller

Implement request handling in `src/controllers/`:

```python
# src/controllers/users.py
from fastapi import Depends, HTTPException, status
from typing import List
from src.controllers.base import BaseController
from src.services.user_service import UserService
from src.schemas.users import UserCreate, UserUpdate, UserResponse
from src.dependencies import get_user_service
from src.exceptions import UserNotFoundError, UserAlreadyExistsError

class UserController(BaseController):
    def __init__(self, user_service: UserService = Depends(get_user_service)):
        self.user_service = user_service
    
    async def create_user(self, user_data: UserCreate) -> UserResponse:
        try:
            return await self.user_service.create_user(user_data)
        except UserAlreadyExistsError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
    
    async def get_user(self, user_id: int) -> UserResponse:
        try:
            return await self.user_service.get_user(user_id)
        except UserNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> UserResponse:
        try:
            return await self.user_service.update_user(user_id, user_data)
        except UserNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
    
    async def delete_user(self, user_id: int) -> dict:
        try:
            await self.user_service.delete_user(user_id)
            return {"message": "User deleted successfully"}
        except UserNotFoundError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
```

### Step 6: Create Routes

Define API routes in `src/routes/v1/`:

```python
# src/routes/v1/users.py
from fastapi import APIRouter, Depends, status
from typing import List
from src.controllers.users import UserController
from src.schemas.users import UserCreate, UserUpdate, UserResponse
from src.auth.rbac import require_permissions

router = APIRouter(prefix="/users", tags=["users"])

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Create a new user account with email and username"
)
async def create_user(
    user_data: UserCreate,
    controller: UserController = Depends()
):
    return await controller.create_user(user_data)

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve a user by their unique identifier"
)
async def get_user(
    user_id: int,
    controller: UserController = Depends(),
    _: dict = Depends(require_permissions(["users:read"]))
):
    return await controller.get_user(user_id)

@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Update user information"
)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    controller: UserController = Depends(),
    _: dict = Depends(require_permissions(["users:write"]))
):
    return await controller.update_user(user_id, user_data)

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user account"
)
async def delete_user(
    user_id: int,
    controller: UserController = Depends(),
    _: dict = Depends(require_permissions(["users:delete"]))
):
    await controller.delete_user(user_id)
```

### Step 7: Register Routes

Add the new routes to the main router in `src/routes/v1/__init__.py`:

```python
from fastapi import APIRouter
from .users import router as users_router
from .health import router as health_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(health_router)
v1_router.include_router(users_router)
```

## Database Operations

### Creating Migrations

1. **Auto-generate migration from model changes**:
```bash
poetry run alembic revision --autogenerate -m "Add users table"
```

2. **Create empty migration for custom changes**:
```bash
poetry run alembic revision -m "Add custom indexes"
```

3. **Edit the generated migration** in `migrations/versions/`:
```python
"""Add users table

Revision ID: abc123
Revises: def456
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123'
down_revision = 'def456'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    # ### end Alembic commands ###

def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    # ### end Alembic commands ###
```

### Running Migrations

```bash
# Apply all pending migrations
poetry run alembic upgrade head

# Apply specific migration
poetry run alembic upgrade abc123

# Rollback one migration
poetry run alembic downgrade -1

# Rollback to specific migration
poetry run alembic downgrade def456

# Show migration history
poetry run alembic history

# Show current migration
poetry run alembic current
```

### Data Migrations

For data migrations, create a custom migration:

```python
"""Migrate user data

Revision ID: xyz789
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

def upgrade() -> None:
    # Define table structure for data migration
    users_table = table('users',
        column('id', sa.Integer),
        column('old_field', sa.String),
        column('new_field', sa.String)
    )
    
    # Migrate data
    connection = op.get_bind()
    result = connection.execute(
        sa.select([users_table.c.id, users_table.c.old_field])
    )
    
    for row in result:
        connection.execute(
            users_table.update()
            .where(users_table.c.id == row.id)
            .values(new_field=transform_data(row.old_field))
        )

def downgrade() -> None:
    # Reverse data migration
    pass

def transform_data(old_value):
    # Custom data transformation logic
    return old_value.upper()
```

## Testing Procedures

### Writing Unit Tests

Create unit tests in `tests/unit/`:

```python
# tests/unit/test_user_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.services.user_service import UserService
from src.schemas.users import UserCreate, UserUpdate
from src.exceptions import UserNotFoundError, UserAlreadyExistsError

class TestUserService:
    @pytest.fixture
    def mock_user_repo(self):
        return AsyncMock()
    
    @pytest.fixture
    def user_service(self, mock_user_repo):
        return UserService(mock_user_repo)
    
    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, mock_user_repo):
        # Arrange
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="password123"
        )
        mock_user = Mock()
        mock_user.id = 1
        mock_user.email = user_data.email
        mock_user.username = user_data.username
        
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.create.return_value = mock_user
        
        # Act
        result = await user_service.create_user(user_data)
        
        # Assert
        assert result.email == user_data.email
        assert result.username == user_data.username
        mock_user_repo.get_by_email.assert_called_once_with(user_data.email)
        mock_user_repo.create.assert_called_once_with(user_data)
    
    @pytest.mark.asyncio
    async def test_create_user_already_exists(self, user_service, mock_user_repo):
        # Arrange
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="password123"
        )
        mock_user_repo.get_by_email.return_value = Mock()  # User exists
        
        # Act & Assert
        with pytest.raises(UserAlreadyExistsError):
            await user_service.create_user(user_data)
```

### Writing Integration Tests

Create integration tests in `tests/integration/`:

```python
# tests/integration/test_user_api.py
import pytest
from httpx import AsyncClient
from src.main import app
from tests.factories import UserFactory

class TestUserAPI:
    @pytest.mark.asyncio
    async def test_create_user(self, async_client: AsyncClient):
        # Arrange
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123"
        }
        
        # Act
        response = await async_client.post("/v1/users/", json=user_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "id" in data
        assert "password" not in data
    
    @pytest.mark.asyncio
    async def test_get_user(self, async_client: AsyncClient, test_user):
        # Act
        response = await async_client.get(f"/v1/users/{test_user.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_get_user_not_found(self, async_client: AsyncClient):
        # Act
        response = await async_client.get("/v1/users/999")
        
        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
```

### Test Fixtures and Factories

Create reusable test data in `tests/factories.py`:

```python
# tests/factories.py
import factory
from factory.alchemy import SQLAlchemyModelFactory
from src.database.models import User
from tests.conftest import TestSession

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = TestSession
        sqlalchemy_session_persistence = "commit"
    
    id = factory.Sequence(lambda n: n)
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"user{n}")
    hashed_password = factory.LazyAttribute(lambda obj: hash_password("password123"))
    is_active = True
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/unit/test_user_service.py

# Run specific test method
poetry run pytest tests/unit/test_user_service.py::TestUserService::test_create_user_success

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run only unit tests
poetry run pytest -m unit

# Run only integration tests
poetry run pytest -m integration

# Run tests in parallel
poetry run pytest -n auto

# Run tests with verbose output
poetry run pytest -v

# Run tests and stop on first failure
poetry run pytest -x
```

## Configuration Management

### Environment-Specific Configuration

Create environment-specific configuration files in `config/environments/`:

```toml
# config/environments/development.toml
[default]
debug = true
log_level = "DEBUG"
database_url = "sqlite+aiosqlite:///./app.db"
cors_origins = ["http://localhost:3000", "http://localhost:8080"]

[database]
echo = true  # Log SQL queries
pool_size = 5
max_overflow = 10

[auth]
jwt_expire_minutes = 60  # Longer expiration for development
```

```toml
# config/environments/production.toml
[default]
debug = false
log_level = "INFO"
cors_origins = ["https://api.example.com"]

[database]
echo = false
pool_size = 20
max_overflow = 30

[auth]
jwt_expire_minutes = 15  # Shorter expiration for security
```

### Using Configuration in Code

```python
# src/config/settings.py
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="API",
    settings_files=["config/settings.toml", "config/.secrets.toml"],
    environments=True,
    load_dotenv=True,
)

# Usage in application code
from src.config.settings import settings

# Access configuration values
database_url = settings.DATABASE_URL
debug_mode = settings.DEBUG
jwt_secret = settings.JWT_SECRET

# Environment-specific values
cors_origins = settings.CORS_ORIGINS
log_level = settings.LOG_LEVEL
```

### Configuration Validation

Create configuration validation:

```python
# src/config/validation.py
from pydantic import BaseSettings, validator
from typing import List, Optional

class Settings(BaseSettings):
    # Database
    database_url: str
    database_echo: bool = False
    
    # Security
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] = []
    
    # External Services
    redis_url: Optional[str] = None
    sentry_dsn: Optional[str] = None
    
    @validator('cors_origins', pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    class Config:
        env_prefix = "API_"
        case_sensitive = False
```

## Authentication and Authorization

### Implementing JWT Authentication

```python
# src/auth/jwt.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
from src.config.settings import settings

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.SECRET_KEY, 
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.PyJWTError:
        return None
```

### Role-Based Access Control (RBAC)

```python
# src/auth/rbac.py
from functools import wraps
from fastapi import HTTPException, status, Depends
from src.auth.dependencies import get_current_user

def require_permissions(permissions: list):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get('current_user') or await get_current_user()
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_permissions = get_user_permissions(current_user)
            
            for permission in permissions:
                if permission not in user_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission '{permission}' required"
                    )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_user_permissions(user) -> list:
    # Implement your permission logic here
    # This could involve checking user roles, groups, etc.
    permissions = []
    
    if user.is_admin:
        permissions.extend(["users:read", "users:write", "users:delete"])
    elif user.is_moderator:
        permissions.extend(["users:read", "users:write"])
    else:
        permissions.append("users:read")
    
    return permissions
```

## Error Handling

### Custom Exceptions

```python
# src/exceptions.py
class APIException(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationError(APIException):
    def __init__(self, message: str):
        super().__init__(message, 400)

class NotFoundError(APIException):
    def __init__(self, message: str):
        super().__init__(message, 404)

class UserNotFoundError(NotFoundError):
    def __init__(self, message: str = "User not found"):
        super().__init__(message)

class UserAlreadyExistsError(APIException):
    def __init__(self, message: str = "User already exists"):
        super().__init__(message, 409)
```

### Global Error Handler

```python
# src/middleware/error_handling.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from src.exceptions import APIException
import logging

logger = logging.getLogger(__name__)

async def api_exception_handler(request: Request, exc: APIException):
    logger.error(f"API Exception: {exc.message}", extra={
        "path": request.url.path,
        "method": request.method,
        "status_code": exc.status_code
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "type": exc.__class__.__name__,
                "path": request.url.path,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "type": "HTTPException",
                "path": request.url.path,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

## Logging and Monitoring

### Structured Logging

```python
# src/utils/logging.py
import logging
import json
from datetime import datetime
from typing import Dict, Any

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/app.log')
        ]
    )
    
    # Set JSON formatter for all handlers
    for handler in logging.root.handlers:
        handler.setFormatter(JSONFormatter())
```

### Request Logging Middleware

```python
# src/middleware/observability.py
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Log request
        start_time = time.time()
        logger.info("Request started", extra={
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent")
        })
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info("Request completed", extra={
            "correlation_id": correlation_id,
            "status_code": response.status_code,
            "process_time": process_time
        })
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
```

### Prometheus Metrics

```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

def record_request_metrics(method: str, endpoint: str, status_code: int, duration: float):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

def get_metrics():
    return generate_latest()
```

## Code Quality and Standards

### Code Formatting

```bash
# Format code with Black
poetry run black src tests

# Sort imports with isort
poetry run isort src tests

# Combine both
poetry run black src tests && poetry run isort src tests
```

### Linting

```bash
# Lint with flake8
poetry run flake8 src tests

# Type checking with mypy
poetry run mypy src

# Security linting with bandit
poetry run bandit -r src
```

### Pre-commit Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### Code Review Checklist

Before submitting code for review:

- [ ] Code follows PEP 8 style guidelines
- [ ] All functions have type hints
- [ ] Docstrings are present for public functions
- [ ] Tests are written and passing
- [ ] No security vulnerabilities introduced
- [ ] Error handling is appropriate
- [ ] Logging is implemented where needed
- [ ] Configuration is externalized
- [ ] Database migrations are included if needed

## Deployment Workflows

### Environment Preparation

1. **Staging Deployment**:
```bash
# Set environment
export API_ENV=staging

# Run migrations
poetry run alembic upgrade head

# Start application
poetry run gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. **Production Deployment**:
```bash
# Set environment
export API_ENV=production

# Validate configuration
poetry run python scripts/config_manager.py validate

# Run migrations
poetry run alembic upgrade head

# Start with proper configuration
poetry run gunicorn src.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Docker Deployment

```bash
# Build production image
docker build -t api-framework:latest .

# Run container
docker run -d \
  --name api-framework \
  -p 8000:8000 \
  --env-file .env.production \
  api-framework:latest
```

### Health Checks

Verify deployment health:

```bash
# Basic health check
curl http://localhost:8000/healthz

# Readiness check
curl http://localhost:8000/readyz

# Detailed health information
curl http://localhost:8000/health/detailed
```

This developer guide provides comprehensive coverage of the essential development workflows. Refer to specific sections as needed during development, and keep this guide updated as the project evolves.