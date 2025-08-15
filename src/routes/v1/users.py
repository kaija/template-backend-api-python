"""
Example User API routes for version 1.

This module demonstrates RESTful API patterns using the controller pattern.
It serves as a template for building domain-specific API endpoints.
"""

from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.controllers.users import UserController
from src.schemas.users import User, UserCreate, UserUpdate


# Initialize controller
user_controller = UserController()

# Create router
router = APIRouter(
    prefix="/users",
    tags=["users"],
)


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user account - example endpoint",
)
async def create_user(user_data: UserCreate) -> User:
    """
    Create a new user.

    Example endpoint demonstrating POST operation with validation.
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
    summary="List Users",
    description="Get a paginated list of users - example endpoint with pagination",
)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of users to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, max_length=100, description="Search term"),
) -> Dict[str, Any]:
    """
    Get a paginated list of users.

    Example endpoint demonstrating pagination and filtering patterns.
    """
    # Build filters
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if search:
        filters["search"] = search

    result = await user_controller.get_all(skip=skip, limit=limit, filters=filters)
    return result


@router.get(
    "/{user_id}",
    response_model=User,
    summary="Get User",
    description="Get a specific user by ID - example endpoint",
)
async def get_user(user_id: str) -> User:
    """
    Get a user by ID.

    Example endpoint demonstrating path parameter handling.
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
    description="Update a specific user by ID - example endpoint",
)
async def update_user(user_id: str, user_data: UserUpdate) -> User:
    """
    Update a user.

    Example endpoint demonstrating PUT operation with validation.
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
    description="Delete a specific user by ID - example endpoint",
)
async def delete_user(user_id: str) -> None:
    """
    Delete a user.

    Example endpoint demonstrating DELETE operation.
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
    description="Get a specific user by email address - example custom endpoint",
)
async def get_user_by_email(email: str) -> User:
    """
    Get a user by email address.

    Example endpoint demonstrating custom query patterns beyond basic CRUD.
    """
    user = await user_controller.get_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
