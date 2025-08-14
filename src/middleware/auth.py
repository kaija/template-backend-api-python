"""
Authentication middleware for handling various authentication methods.

This module provides extensible authentication middleware supporting
JWT tokens, OAuth2, and API key authentication methods.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import jwt
from passlib.context import CryptContext

# Import configuration functions with fallback for testing
try:
    from src.config.settings import settings, is_development
except Exception:
    # Fallback for testing when configuration is not available
    class MockSettings:
        secret_key = "test-secret-key"
        algorithm = "HS256"
        access_token_expire_minutes = 30
        refresh_token_expire_days = 7

    settings = MockSettings()

    def is_development():
        return True

logger = logging.getLogger(__name__)


class AuthenticationBackend(ABC):
    """
    Abstract base class for authentication backends.

    This class defines the interface that all authentication backends
    must implement.
    """

    @abstractmethod
    async def authenticate(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Authenticate a request and return user information.

        Args:
            request: FastAPI request object

        Returns:
            User information dict if authenticated, None otherwise
        """
        pass

    @abstractmethod
    def get_scheme_name(self) -> str:
        """
        Get the authentication scheme name.

        Returns:
            Authentication scheme name
        """
        pass


class JWTAuthenticationBackend(AuthenticationBackend):
    """
    JWT token authentication backend.

    This backend validates JWT tokens and extracts user information.
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        token_url: str = "/auth/token",
        auto_error: bool = True
    ):
        """
        Initialize JWT authentication backend.

        Args:
            secret_key: Secret key for JWT signing/verification
            algorithm: JWT algorithm to use
            token_url: URL for token endpoint
            auto_error: Whether to automatically raise errors
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_url = token_url
        self.auto_error = auto_error
        self.bearer = HTTPBearer(auto_error=auto_error)

    async def authenticate(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Authenticate JWT token from request.

        Args:
            request: FastAPI request object

        Returns:
            User information from token payload
        """
        try:
            # Extract token from Authorization header
            credentials: HTTPAuthorizationCredentials = await self.bearer(request)
            if not credentials:
                return None

            # Verify and decode token
            payload = jwt.decode(
                credentials.credentials,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            # Check token expiration
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                logger.warning("JWT token expired")
                return None

            # Extract user information
            user_info = {
                "user_id": payload.get("sub"),
                "username": payload.get("username"),
                "email": payload.get("email"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "token_type": payload.get("token_type", "access"),
                "exp": exp,
                "iat": payload.get("iat"),
            }

            return user_info

        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        except Exception as e:
            logger.error(f"JWT authentication error: {e}")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication failed",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

    def get_scheme_name(self) -> str:
        """Get JWT scheme name."""
        return "JWT"

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.access_token_expire_minutes
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": "access"
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token.

        Args:
            data: Data to encode in token
            expires_delta: Token expiration time

        Returns:
            Encoded JWT refresh token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                days=settings.refresh_token_expire_days
            )

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": "refresh"
        })

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt


class APIKeyAuthenticationBackend(AuthenticationBackend):
    """
    API Key authentication backend.

    This backend validates API keys from headers or query parameters.
    """

    def __init__(
        self,
        api_keys: Dict[str, Dict[str, Any]],
        header_name: str = "X-API-Key",
        query_param: str = "api_key",
        auto_error: bool = True
    ):
        """
        Initialize API key authentication backend.

        Args:
            api_keys: Dictionary mapping API keys to user information
            header_name: Header name for API key
            query_param: Query parameter name for API key
            auto_error: Whether to automatically raise errors
        """
        self.api_keys = api_keys
        self.header_name = header_name
        self.query_param = query_param
        self.auto_error = auto_error

    async def authenticate(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Authenticate API key from request.

        Args:
            request: FastAPI request object

        Returns:
            User information associated with API key
        """
        # Try to get API key from header
        api_key = request.headers.get(self.header_name)

        # If not in header, try query parameter
        if not api_key:
            api_key = request.query_params.get(self.query_param)

        if not api_key:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key required",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            return None

        # Validate API key
        user_info = self.api_keys.get(api_key)
        if not user_info:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "ApiKey"},
                )
            return None

        # Add API key info to user data
        user_info = user_info.copy()
        user_info["api_key"] = api_key[:8] + "..."  # Masked for logging
        user_info["auth_method"] = "api_key"

        return user_info

    def get_scheme_name(self) -> str:
        """Get API key scheme name."""
        return "ApiKey"


class OAuth2AuthenticationBackend(AuthenticationBackend):
    """
    OAuth2 authentication backend.

    This backend handles OAuth2 token validation.
    """

    def __init__(
        self,
        token_url: str = "/auth/token",
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True
    ):
        """
        Initialize OAuth2 authentication backend.

        Args:
            token_url: URL for token endpoint
            scopes: Available OAuth2 scopes
            auto_error: Whether to automatically raise errors
        """
        self.token_url = token_url
        self.scopes = scopes or {}
        self.auto_error = auto_error
        self.bearer = HTTPBearer(auto_error=auto_error)

    async def authenticate(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Authenticate OAuth2 token from request.

        Args:
            request: FastAPI request object

        Returns:
            User information from OAuth2 token
        """
        try:
            # Extract token from Authorization header
            credentials: HTTPAuthorizationCredentials = await self.bearer(request)
            if not credentials:
                return None

            # In a real implementation, you would validate the token
            # against the OAuth2 provider (e.g., Google, GitHub, etc.)
            # For now, we'll use a simple validation

            token = credentials.credentials

            # TODO: Implement actual OAuth2 token validation
            # This would typically involve:
            # 1. Validating token with OAuth2 provider
            # 2. Extracting user information from provider
            # 3. Mapping provider data to internal user format

            # Placeholder implementation
            if token.startswith("oauth2_"):
                user_info = {
                    "user_id": "oauth2_user",
                    "username": "oauth2_user",
                    "email": "oauth2@example.com",
                    "roles": ["user"],
                    "permissions": [],
                    "auth_method": "oauth2",
                    "token": token[:16] + "...",  # Masked for logging
                }
                return user_info

            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid OAuth2 token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

        except Exception as e:
            logger.error(f"OAuth2 authentication error: {e}")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="OAuth2 authentication failed",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return None

    def get_scheme_name(self) -> str:
        """Get OAuth2 scheme name."""
        return "OAuth2"


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware supporting multiple authentication backends.

    This middleware tries multiple authentication backends in order
    and sets user information in request state.
    """

    def __init__(
        self,
        app: ASGIApp,
        backends: List[AuthenticationBackend],
        exempt_paths: Optional[List[str]] = None,
        require_auth: bool = False
    ):
        """
        Initialize authentication middleware.

        Args:
            app: ASGI application instance
            backends: List of authentication backends to try
            exempt_paths: Paths that don't require authentication
            require_auth: Whether authentication is required by default
        """
        super().__init__(app)
        self.backends = backends
        self.exempt_paths = exempt_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/healthz",
            "/readyz",
            "/metrics",
        ]
        self.require_auth = require_auth

    async def dispatch(self, request: Request, call_next) -> Any:
        """
        Process request with authentication.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response object
        """
        # Check if path is exempt from authentication
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Try authentication backends
        user_info = None
        auth_backend = None

        for backend in self.backends:
            try:
                user_info = await backend.authenticate(request)
                if user_info:
                    auth_backend = backend
                    break
            except HTTPException:
                # If backend raises an exception, re-raise it
                raise
            except Exception as e:
                # Log unexpected errors but continue to next backend
                logger.error(f"Authentication backend {backend.get_scheme_name()} error: {e}")
                continue

        # Set authentication information in request state
        request.state.user = user_info
        request.state.auth_backend = auth_backend
        request.state.is_authenticated = user_info is not None

        # Check if authentication is required
        if self.require_auth and not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Log authentication event
        if user_info:
            logger.info(
                f"User authenticated: {user_info.get('username', 'unknown')} "
                f"via {auth_backend.get_scheme_name()}",
                extra={
                    "event_type": "authentication_success",
                    "user_id": user_info.get("user_id"),
                    "username": user_info.get("username"),
                    "auth_method": auth_backend.get_scheme_name(),
                    "path": request.url.path,
                    "method": request.method,
                    "correlation_id": getattr(request.state, "correlation_id", None),
                }
            )

            # Log audit event for successful authentication
            try:
                from src.audit.audit_logger import log_authentication_event, AuditEventType
                log_authentication_event(
                    event_type=AuditEventType.LOGIN_SUCCESS,
                    username=user_info.get("username"),
                    user_id=user_info.get("user_id"),
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    correlation_id=getattr(request.state, "correlation_id", None),
                    outcome="success",
                    details={
                        "auth_method": auth_backend.get_scheme_name(),
                        "path": request.url.path,
                        "method": request.method,
                    }
                )
            except ImportError:
                # Audit logging not available
                pass

        return await call_next(request)

    def _is_exempt_path(self, path: str) -> bool:
        """
        Check if path is exempt from authentication.

        Args:
            path: Request path

        Returns:
            True if path is exempt
        """
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address or None
        """
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",
            "x-client-ip",
        ]

        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one
                return ip.split(",")[0].strip()

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None


# Password hashing utilities
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


# Convenience functions for creating authentication backends
def create_jwt_backend(
    secret_key: Optional[str] = None,
    algorithm: str = "HS256",
    auto_error: bool = True
) -> JWTAuthenticationBackend:
    """
    Create a JWT authentication backend with default settings.

    Args:
        secret_key: JWT secret key (uses settings if not provided)
        algorithm: JWT algorithm
        auto_error: Whether to automatically raise errors

    Returns:
        Configured JWT authentication backend
    """
    if secret_key is None:
        secret_key = settings.secret_key

    return JWTAuthenticationBackend(
        secret_key=secret_key,
        algorithm=algorithm,
        auto_error=auto_error
    )


def create_api_key_backend(
    api_keys: Optional[Dict[str, Dict[str, Any]]] = None,
    auto_error: bool = True
) -> APIKeyAuthenticationBackend:
    """
    Create an API key authentication backend with default settings.

    Args:
        api_keys: API key to user info mapping
        auto_error: Whether to automatically raise errors

    Returns:
        Configured API key authentication backend
    """
    if api_keys is None:
        # Default API keys for development/testing
        api_keys = {
            "dev-api-key-123": {
                "user_id": "api_user_1",
                "username": "api_user",
                "email": "api@example.com",
                "roles": ["api_user"],
                "permissions": ["read", "write"],
            }
        }

    return APIKeyAuthenticationBackend(
        api_keys=api_keys,
        auto_error=auto_error
    )


def create_oauth2_backend(
    token_url: str = "/auth/token",
    scopes: Optional[Dict[str, str]] = None,
    auto_error: bool = True
) -> OAuth2AuthenticationBackend:
    """
    Create an OAuth2 authentication backend with default settings.

    Args:
        token_url: Token endpoint URL
        scopes: Available OAuth2 scopes
        auto_error: Whether to automatically raise errors

    Returns:
        Configured OAuth2 authentication backend
    """
    if scopes is None:
        scopes = {
            "read": "Read access",
            "write": "Write access",
            "admin": "Admin access",
        }

    return OAuth2AuthenticationBackend(
        token_url=token_url,
        scopes=scopes,
        auto_error=auto_error
    )
