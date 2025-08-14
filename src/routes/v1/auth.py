"""
Authentication routes.

This module provides authentication endpoints for login, token refresh,
and user management.
"""

from datetime import timedelta
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from src.auth import Permission, require_permission, get_current_user
from src.middleware.auth import (
    create_jwt_backend,
    verify_password,
    get_password_hash
)
from src.schemas.base import SuccessResponse
from src.audit.audit_logger import (
    log_authentication_event,
    log_admin_action_event,
    AuditEventType
)
from src.audit.decorators import audit_admin_action

router = APIRouter(prefix="/auth", tags=["Authentication"])

# JWT backend for token operations
jwt_backend = create_jwt_backend()


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserRegistration(BaseModel):
    """User registration schema."""
    username: str
    email: EmailStr
    password: str
    full_name: str = ""


class UserProfile(BaseModel):
    """User profile schema."""
    user_id: str
    username: str
    email: str
    full_name: str
    roles: list[str]
    permissions: list[str]
    is_active: bool = True


# Mock user database (replace with real database in production)
MOCK_USERS = {
    "testuser": {
        "user_id": "user_1",
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": get_password_hash("testpass123"),
        "roles": ["user"],
        "permissions": ["user:read", "content:read", "content:write"],
        "is_active": True,
    },
    "admin": {
        "user_id": "admin_1",
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "hashed_password": get_password_hash("admin123"),
        "roles": ["admin"],
        "permissions": ["*"],
        "is_active": True,
    }
}


def authenticate_user(username: str, password: str) -> Dict[str, Any] | None:
    """
    Authenticate user with username and password.

    Args:
        username: Username
        password: Plain text password

    Returns:
        User information if authenticated, None otherwise
    """
    user = MOCK_USERS.get(username)
    if not user:
        return None

    if not verify_password(password, user["hashed_password"]):
        return None

    return user


@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> TokenResponse:
    """
    Login endpoint to get access and refresh tokens.

    Args:
        form_data: OAuth2 password form data

    Returns:
        Access and refresh tokens

    Raises:
        HTTPException: If authentication fails
    """
    # Authenticate user
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        # Log failed authentication
        log_authentication_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            username=form_data.username,
            outcome="failure",
            message="Login failed: incorrect username or password"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active"):
        # Log failed authentication for inactive user
        log_authentication_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            username=user["username"],
            user_id=user["user_id"],
            outcome="failure",
            message="Login failed: inactive user account"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token data
    token_data = {
        "sub": user["user_id"],
        "username": user["username"],
        "email": user["email"],
        "roles": user["roles"],
        "permissions": user["permissions"],
    }

    # Create tokens
    access_token = jwt_backend.create_access_token(data=token_data)
    refresh_token = jwt_backend.create_refresh_token(data=token_data)

    # Log successful authentication
    log_authentication_event(
        event_type=AuditEventType.LOGIN_SUCCESS,
        username=user["username"],
        user_id=user["user_id"],
        outcome="success",
        message="User logged in successfully",
        details={
            "auth_method": "password",
            "roles": user["roles"]
        }
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=30 * 60  # 30 minutes
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(request: Request) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        request: FastAPI request object

    Returns:
        New access and refresh tokens

    Raises:
        HTTPException: If refresh token is invalid
    """
    # Get current user from refresh token
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if token is a refresh token
    if user.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user data from mock database
    username = user.get("username")
    user_data = MOCK_USERS.get(username)
    if not user_data or not user_data.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new token data
    token_data = {
        "sub": user_data["user_id"],
        "username": user_data["username"],
        "email": user_data["email"],
        "roles": user_data["roles"],
        "permissions": user_data["permissions"],
    }

    # Create new tokens
    access_token = jwt_backend.create_access_token(data=token_data)
    refresh_token = jwt_backend.create_refresh_token(data=token_data)

    # Log token refresh
    log_authentication_event(
        event_type=AuditEventType.TOKEN_REFRESH,
        username=user_data["username"],
        user_id=user_data["user_id"],
        outcome="success",
        message="Access token refreshed successfully"
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=30 * 60  # 30 minutes
    )


@router.post("/register", response_model=SuccessResponse)
async def register_user(user_data: UserRegistration) -> SuccessResponse:
    """
    Register a new user.

    Args:
        user_data: User registration data

    Returns:
        Success response

    Raises:
        HTTPException: If username already exists
    """
    # Check if username already exists
    if user_data.username in MOCK_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Create new user
    new_user = {
        "user_id": f"user_{len(MOCK_USERS) + 1}",
        "username": user_data.username,
        "email": user_data.email,
        "full_name": user_data.full_name,
        "hashed_password": get_password_hash(user_data.password),
        "roles": ["user"],  # Default role
        "permissions": ["user:read", "content:read", "content:write"],
        "is_active": True,
    }

    # Add to mock database
    MOCK_USERS[user_data.username] = new_user

    return SuccessResponse(
        message="User registered successfully",
        data={"user_id": new_user["user_id"], "username": new_user["username"]}
    )


@router.get("/profile", response_model=UserProfile)
@require_permission(Permission.USER_READ)
async def get_user_profile(request: Request) -> UserProfile:
    """
    Get current user profile.

    Args:
        request: FastAPI request object

    Returns:
        User profile information

    Raises:
        HTTPException: If user not authenticated
    """
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    return UserProfile(
        user_id=user["user_id"],
        username=user["username"],
        email=user["email"],
        full_name=user.get("full_name", ""),
        roles=user.get("roles", []),
        permissions=user.get("permissions", []),
        is_active=True
    )


@router.post("/logout", response_model=SuccessResponse)
async def logout(request: Request) -> SuccessResponse:
    """
    Logout current user.

    Note: In a real implementation, you would invalidate the token
    by adding it to a blacklist or removing it from a whitelist.

    Args:
        request: FastAPI request object

    Returns:
        Success response
    """
    user = get_current_user(request)
    username = user.get("username", "unknown") if user else "unknown"

    # In a real implementation, you would:
    # 1. Add token to blacklist
    # 2. Remove token from whitelist
    # 3. Clear user session

    return SuccessResponse(
        message=f"User {username} logged out successfully"
    )


@router.get("/users", response_model=list[UserProfile])
@require_permission(Permission.USER_ADMIN)
@audit_admin_action(message_template="Admin action: list users")
async def list_users(request: Request) -> list[UserProfile]:
    """
    List all users (admin only).

    Args:
        request: FastAPI request object

    Returns:
        List of user profiles
    """
    users = []
    for user_data in MOCK_USERS.values():
        users.append(UserProfile(
            user_id=user_data["user_id"],
            username=user_data["username"],
            email=user_data["email"],
            full_name=user_data.get("full_name", ""),
            roles=user_data.get("roles", []),
            permissions=user_data.get("permissions", []),
            is_active=user_data.get("is_active", True)
        ))

    return users
