"""
User API routes for version 1.

This module provides user management endpoints using the controller pattern
and dependency injection system.
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.controllers.users import UserController
from src.schemas.users import User, UserCreate, UserUpdate, UserList, UserFilters
from src.dependencies import (
    RequestContext,
    AuthenticatedUser,
    require_permissions,
    get_rate_limiter
)


# Initialize controller
user_controller = UserController()

# Create router
router = APIRouter(
    prefix="/users",
    tags=["users"],
    dependencies=[Depends(get_rate_limiter)],
)


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user account",
)
async def create_user(
    user_data: UserCreate,
    context: RequestContext,
    current_user: Dict[str, Any] = Depends(require_permissions("user:create"))
) -> User:
    """
    Create a new user.

    Args:
        user_data: User creation data
        context: Request context
        current_user: Current authenticated user with create permissions

    Returns:
        Created user

    Raises:
        HTTPException: If user creation fails
    """
    try:
        user = await user_controller.create(user_data)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/",
    response_model=UserList,
    summary="List Users",
    description="Get a paginated list of users with optional filtering",
)
async def list_users(
    context: RequestContext,
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of users to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, max_length=100, description="Search in username, email, or full name"),
    current_user: Dict[str, Any] = Depends(require_permissions("user:read"))
) -> UserList:
    """
    Get a paginated list of users.

    Args:
        context: Request context
        skip: Number of users to skip
        limit: Maximum number of users to return
        is_active: Filter by active status
        search: Search term
        current_user: Current authenticated user with read permissions

    Returns:
        Paginated list of users
    """
    # Build filters
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if search:
        filters["search"] = search

    result = await user_controller.get_all(skip=skip, limit=limit, filters=filters)
    return UserList(**result)


@router.get(
    "/{user_id}",
    response_model=User,
    summary="Get User",
    description="Get a specific user by ID",
)
async def get_user(
    user_id: str,
    context: RequestContext,
    current_user: Dict[str, Any] = Depends(require_permissions("user:read"))
) -> User:
    """
    Get a user by ID.

    Args:
        user_id: User ID
        context: Request context
        current_user: Current authenticated user with read permissions

    Returns:
        User information

    Raises:
        HTTPException: If user is not found
    """
    user = await user_controller.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.put(
    "/{user_id}",
    response_model=User,
    summary="Update User",
    description="Update a specific user by ID",
)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    context: RequestContext,
    current_user: Dict[str, Any] = Depends(require_permissions("user:update"))
) -> User:
    """
    Update a user.

    Args:
        user_id: User ID
        user_data: User update data
        context: Request context
        current_user: Current authenticated user with update permissions

    Returns:
        Updated user information

    Raises:
        HTTPException: If user is not found
    """
    user = await user_controller.update(user_id, user_data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User",
    description="Delete a specific user by ID",
)
async def delete_user(
    user_id: str,
    context: RequestContext,
    current_user: Dict[str, Any] = Depends(require_permissions("user:delete"))
) -> None:
    """
    Delete a user.

    Args:
        user_id: User ID
        context: Request context
        current_user: Current authenticated user with delete permissions

    Raises:
        HTTPException: If user is not found
    """
    deleted = await user_controller.delete(user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.get(
    "/by-email/{email}",
    response_model=User,
    summary="Get User by Email",
    description="Get a specific user by email address",
)
async def get_user_by_email(
    email: str,
    context: RequestContext,
    current_user: Dict[str, Any] = Depends(require_permissions("user:read"))
) -> User:
    """
    Get a user by email address.

    Args:
        email: User email address
        context: Request context
        current_user: Current authenticated user with read permissions

    Returns:
        User information

    Raises:
        HTTPException: If user is not found
    """
    user = await user_controller.get_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post(
    "/{user_id}/activate",
    response_model=User,
    summary="Activate User",
    description="Activate a user account",
)
async def activate_user(
    user_id: str,
    context: RequestContext,
    current_user: Dict[str, Any] = Depends(require_permissions("user:update"))
) -> User:
    """
    Activate a user account.

    Args:
        user_id: User ID
        context: Request context
        current_user: Current authenticated user with update permissions

    Returns:
        Updated user information

    Raises:
        HTTPException: If user is not found
    """
    user = await user_controller.activate_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.post(
    "/{user_id}/deactivate",
    response_model=User,
    summary="Deactivate User",
    description="Deactivate a user account",
)
async def deactivate_user(
    user_id: str,
    context: RequestContext,
    current_user: Dict[str, Any] = Depends(require_permissions("user:update"))
) -> User:
    """
    Deactivate a user account.

    Args:
        user_id: User ID
        context: Request context
        current_user: Current authenticated user with update permissions

    Returns:
        Updated user information

    Raises:
        HTTPException: If user is not found
    """
    user = await user_controller.deactivate_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
