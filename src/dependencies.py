"""
Dependency injection system for FastAPI.

This module provides dependency injection utilities for FastAPI routes,
including authentication, database sessions, and other common dependencies.
"""

import logging
from typing import Optional, Dict, Any, Annotated
from datetime import datetime

from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config import settings


# Security scheme for JWT authentication
security = HTTPBearer(auto_error=False)

# Logger for dependencies
logger = logging.getLogger(__name__)


async def get_request_id(
    request: Request,
    x_request_id: Annotated[Optional[str], Header()] = None
) -> str:
    """
    Get or generate a request ID for tracing.

    Args:
        request: FastAPI request object
        x_request_id: Optional request ID from header

    Returns:
        Request ID string
    """
    if x_request_id:
        return x_request_id

    # Generate request ID if not provided
    request_id = f"req_{datetime.utcnow().timestamp()}_{id(request)}"
    return request_id


async def get_correlation_id(
    x_correlation_id: Annotated[Optional[str], Header()] = None,
    request_id: str = Depends(get_request_id)
) -> str:
    """
    Get or generate a correlation ID for distributed tracing.

    Args:
        x_correlation_id: Optional correlation ID from header
        request_id: Request ID from dependency

    Returns:
        Correlation ID string
    """
    if x_correlation_id:
        return x_correlation_id

    # Use request ID as correlation ID if not provided
    return request_id


async def get_user_agent(
    user_agent: Annotated[Optional[str], Header()] = None
) -> Optional[str]:
    """
    Get user agent from request headers.

    Args:
        user_agent: User agent string from header

    Returns:
        User agent string or None
    """
    return user_agent


async def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check for forwarded headers (behind proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"


async def get_request_context(
    request: Request,
    request_id: str = Depends(get_request_id),
    correlation_id: str = Depends(get_correlation_id),
    user_agent: Optional[str] = Depends(get_user_agent),
    client_ip: str = Depends(get_client_ip)
) -> Dict[str, Any]:
    """
    Get comprehensive request context for logging and tracing.

    Args:
        request: FastAPI request object
        request_id: Request ID from dependency
        correlation_id: Correlation ID from dependency
        user_agent: User agent from dependency
        client_ip: Client IP from dependency

    Returns:
        Dictionary with request context information
    """
    return {
        "request_id": request_id,
        "correlation_id": correlation_id,
        "method": request.method,
        "url": str(request.url),
        "path": request.url.path,
        "query_params": dict(request.query_params),
        "user_agent": user_agent,
        "client_ip": client_ip,
        "timestamp": datetime.utcnow().isoformat(),
    }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User information if authenticated, None otherwise

    Raises:
        HTTPException: If token is invalid
    """
    if not credentials:
        return None

    try:
        # TODO: Implement JWT token validation
        # For now, return a placeholder
        token = credentials.credentials

        # Validate token format (basic check)
        if not token or len(token) < 10:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # TODO: Decode and validate JWT token
        # This is a placeholder implementation
        user_data = {
            "user_id": "user_123",
            "username": "test_user",
            "email": "test@example.com",
            "roles": ["user"],
            "permissions": ["read"],
        }

        logger.info(f"User authenticated: {user_data['user_id']}")
        return user_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_authentication(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Require user authentication.

    Args:
        current_user: Current user from dependency

    Returns:
        User information

    Raises:
        HTTPException: If user is not authenticated
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return current_user


def require_permissions(*required_permissions: str):
    """
    Create a dependency that requires specific permissions.

    Args:
        *required_permissions: Required permission names

    Returns:
        Dependency function
    """
    async def check_permissions(
        current_user: Dict[str, Any] = Depends(require_authentication)
    ) -> Dict[str, Any]:
        """
        Check if user has required permissions.

        Args:
            current_user: Current authenticated user

        Returns:
            User information if authorized

        Raises:
            HTTPException: If user lacks required permissions
        """
        user_permissions = set(current_user.get("permissions", []))
        required_perms = set(required_permissions)

        if not required_perms.issubset(user_permissions):
            missing_perms = required_perms - user_permissions
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing_perms)}"
            )

        return current_user

    return check_permissions


def require_roles(*required_roles: str):
    """
    Create a dependency that requires specific roles.

    Args:
        *required_roles: Required role names

    Returns:
        Dependency function
    """
    async def check_roles(
        current_user: Dict[str, Any] = Depends(require_authentication)
    ) -> Dict[str, Any]:
        """
        Check if user has required roles.

        Args:
            current_user: Current authenticated user

        Returns:
            User information if authorized

        Raises:
            HTTPException: If user lacks required roles
        """
        user_roles = set(current_user.get("roles", []))
        required_role_set = set(required_roles)

        if not required_role_set.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required roles: {', '.join(required_roles)}"
            )

        return current_user

    return check_roles


async def get_database_session():
    """
    Get database session dependency.

    Returns:
        Database session
    """
    # TODO: Implement actual database session management
    # This is a placeholder for now
    session = {"db": "placeholder_session"}
    try:
        yield session
    finally:
        # Close session
        pass


async def get_redis_client():
    """
    Get Redis client dependency.

    Returns:
        Redis client
    """
    # TODO: Implement actual Redis client management
    # This is a placeholder for now
    client = {"redis": "placeholder_client"}
    try:
        yield client
    finally:
        # Close client
        pass


async def get_rate_limiter(
    request: Request,
    client_ip: str = Depends(get_client_ip)
) -> None:
    """
    Rate limiting dependency.

    Args:
        request: FastAPI request object
        client_ip: Client IP address

    Raises:
        HTTPException: If rate limit is exceeded
    """
    # TODO: Implement actual rate limiting
    # This is a placeholder for now

    if not getattr(settings, "rate_limit_enabled", True):
        return

    # Placeholder rate limiting logic
    # In a real implementation, this would check Redis or another store
    # for request counts per IP/user

    logger.debug(f"Rate limit check for {client_ip} on {request.url.path}")


# Common dependency combinations
RequestContext = Annotated[Dict[str, Any], Depends(get_request_context)]
AuthenticatedUser = Annotated[Dict[str, Any], Depends(require_authentication)]
DatabaseSession = Annotated[Dict[str, Any], Depends(get_database_session)]
RedisClient = Annotated[Dict[str, Any], Depends(get_redis_client)]
