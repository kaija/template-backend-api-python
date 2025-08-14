"""
User controller with CRUD operations.

This module provides user management functionality using the base controller pattern.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from src.controllers.base import CRUDController
from src.schemas.users import User, UserCreate, UserUpdate


class UserController(CRUDController[User, UserCreate, UserUpdate]):
    """
    User controller implementing CRUD operations.

    This controller manages user-related operations including
    creation, retrieval, updating, and deletion of users.
    """

    def __init__(self):
        """Initialize the user controller."""
        super().__init__(User)
        self._users_db: Dict[str, Dict[str, Any]] = {}  # In-memory storage for demo

    async def create(self, data: UserCreate) -> User:
        """
        Create a new user.

        Args:
            data: User creation data

        Returns:
            Created user

        Raises:
            ValueError: If user already exists
        """
        self._log_request("POST", "/users")

        try:
            # Check if user already exists
            if any(user.get("email") == data.email for user in self._users_db.values()):
                raise ValueError(f"User with email {data.email} already exists")

            # Generate user ID
            user_id = f"user_{len(self._users_db) + 1}"

            # Create user data
            user_data = {
                "id": user_id,
                "username": data.username,
                "email": data.email,
                "full_name": data.full_name,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            # Store user
            self._users_db[user_id] = user_data

            # Create user model
            user = User(**user_data)

            self._log_response("POST", "/users", 201, user_id=user_id)
            return user

        except Exception as e:
            raise self._handle_error(e, "create_user")

    async def get_by_id(self, resource_id: str) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            resource_id: User ID

        Returns:
            User if found, None otherwise
        """
        self._log_request("GET", f"/users/{resource_id}")

        try:
            user_data = self._users_db.get(resource_id)
            if not user_data:
                self._log_response("GET", f"/users/{resource_id}", 404)
                return None

            user = User(**user_data)
            self._log_response("GET", f"/users/{resource_id}", 200)
            return user

        except Exception as e:
            raise self._handle_error(e, f"get_user_{resource_id}")

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get all users with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply

        Returns:
            Dictionary with users and pagination info
        """
        self._log_request("GET", "/users", skip=skip, limit=limit)

        try:
            self._validate_pagination(skip, limit)

            # Apply filters if provided
            users_data = list(self._users_db.values())
            if filters:
                if "is_active" in filters:
                    users_data = [u for u in users_data if u.get("is_active") == filters["is_active"]]
                if "search" in filters:
                    search_term = filters["search"].lower()
                    users_data = [
                        u for u in users_data
                        if search_term in u.get("username", "").lower()
                        or search_term in u.get("email", "").lower()
                        or search_term in u.get("full_name", "").lower()
                    ]

            # Apply pagination
            total = len(users_data)
            paginated_data = users_data[skip:skip + limit]

            # Convert to User models
            users = [User(**user_data) for user_data in paginated_data]

            # Create paginated response
            response = self._create_paginated_response(users, total, skip, limit)

            self._log_response("GET", "/users", 200, total=total, returned=len(users))
            return response

        except Exception as e:
            raise self._handle_error(e, "get_all_users")

    async def update(self, resource_id: str, data: UserUpdate) -> Optional[User]:
        """
        Update a user.

        Args:
            resource_id: User ID
            data: User update data

        Returns:
            Updated user if found, None otherwise
        """
        self._log_request("PUT", f"/users/{resource_id}")

        try:
            user_data = self._users_db.get(resource_id)
            if not user_data:
                self._log_response("PUT", f"/users/{resource_id}", 404)
                return None

            # Update user data
            update_dict = data.dict(exclude_unset=True)
            user_data.update(update_dict)
            user_data["updated_at"] = datetime.utcnow()

            # Create updated user model
            user = User(**user_data)

            self._log_response("PUT", f"/users/{resource_id}", 200)
            return user

        except Exception as e:
            raise self._handle_error(e, f"update_user_{resource_id}")

    async def delete(self, resource_id: str) -> bool:
        """
        Delete a user.

        Args:
            resource_id: User ID

        Returns:
            True if deleted, False if not found
        """
        self._log_request("DELETE", f"/users/{resource_id}")

        try:
            if resource_id not in self._users_db:
                self._log_response("DELETE", f"/users/{resource_id}", 404)
                return False

            del self._users_db[resource_id]

            self._log_response("DELETE", f"/users/{resource_id}", 204)
            return True

        except Exception as e:
            raise self._handle_error(e, f"delete_user_{resource_id}")

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Args:
            email: User email address

        Returns:
            User if found, None otherwise
        """
        self._log_request("GET", f"/users/by-email/{email}")

        try:
            for user_data in self._users_db.values():
                if user_data.get("email") == email:
                    user = User(**user_data)
                    self._log_response("GET", f"/users/by-email/{email}", 200)
                    return user

            self._log_response("GET", f"/users/by-email/{email}", 404)
            return None

        except Exception as e:
            raise self._handle_error(e, f"get_user_by_email_{email}")

    async def activate_user(self, resource_id: str) -> Optional[User]:
        """
        Activate a user account.

        Args:
            resource_id: User ID

        Returns:
            Updated user if found, None otherwise
        """
        self._log_request("POST", f"/users/{resource_id}/activate")

        try:
            user_data = self._users_db.get(resource_id)
            if not user_data:
                self._log_response("POST", f"/users/{resource_id}/activate", 404)
                return None

            user_data["is_active"] = True
            user_data["updated_at"] = datetime.utcnow()

            user = User(**user_data)
            self._log_response("POST", f"/users/{resource_id}/activate", 200)
            return user

        except Exception as e:
            raise self._handle_error(e, f"activate_user_{resource_id}")

    async def deactivate_user(self, resource_id: str) -> Optional[User]:
        """
        Deactivate a user account.

        Args:
            resource_id: User ID

        Returns:
            Updated user if found, None otherwise
        """
        self._log_request("POST", f"/users/{resource_id}/deactivate")

        try:
            user_data = self._users_db.get(resource_id)
            if not user_data:
                self._log_response("POST", f"/users/{resource_id}/deactivate", 404)
                return None

            user_data["is_active"] = False
            user_data["updated_at"] = datetime.utcnow()

            user = User(**user_data)
            self._log_response("POST", f"/users/{resource_id}/deactivate", 200)
            return user

        except Exception as e:
            raise self._handle_error(e, f"deactivate_user_{resource_id}")
