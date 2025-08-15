"""
Example User controller demonstrating CRUD operations.

This module serves as a template for implementing domain-specific controllers.
It shows common patterns for CRUD operations using the base controller.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone

from src.controllers.base import CRUDController
from src.schemas.users import User, UserCreate, UserUpdate


class UserController(CRUDController[User, UserCreate, UserUpdate]):
    """
    Example User controller implementing basic CRUD operations.

    This serves as a template for building domain-specific controllers.
    Shows how to extend the base CRUDController with concrete implementations.
    """

    def __init__(self):
        """Initialize the user controller."""
        super().__init__(User)
        # In-memory storage for demonstration purposes
        # In a real application, this would use a service layer
        self._users_db: Dict[str, Dict[str, Any]] = {}

    async def create(self, data: UserCreate) -> User:
        """
        Create a new user.

        Example implementation showing basic creation logic.
        In a real application, this would delegate to a service layer.
        """
        self._log_request("POST", "/users")

        try:
            # Basic duplicate check
            if any(user.get("email") == data.email for user in self._users_db.values()):
                raise ValueError(f"User with email {data.email} already exists")

            # Generate simple ID
            user_id = f"user_{len(self._users_db) + 1}"

            # Create user data
            user_data = {
                "id": user_id,
                "username": data.username,
                "email": data.email,
                "full_name": data.full_name,
                "is_active": True,
                "login_count": 0,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }

            # Store in memory (demo only)
            self._users_db[user_id] = user_data

            # Return user model
            user = User(**user_data)
            self._log_response("POST", "/users", 201, user_id=user_id)
            return user

        except Exception as e:
            raise self._handle_error(e, "create_user")

    async def get_by_id(self, resource_id: str) -> Optional[User]:
        """
        Get a user by ID.

        Example implementation showing basic retrieval logic.
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

        Example implementation showing pagination and basic filtering patterns.
        """
        self._log_request("GET", "/users", skip=skip, limit=limit)

        try:
            self._validate_pagination(skip, limit)

            # Get all users
            users_data = list(self._users_db.values())

            # Apply simple filters (example pattern)
            if filters:
                if "is_active" in filters:
                    users_data = [u for u in users_data if u.get("is_active") == filters["is_active"]]
                if "search" in filters:
                    search_term = filters["search"].lower()
                    users_data = [
                        u for u in users_data
                        if search_term in u.get("username", "").lower()
                        or search_term in u.get("email", "").lower()
                    ]

            # Apply pagination
            total = len(users_data)
            paginated_data = users_data[skip:skip + limit]

            # Convert to models
            users = [User(**user_data) for user_data in paginated_data]

            # Create response
            response = self._create_paginated_response(users, total, skip, limit)
            self._log_response("GET", "/users", 200, total=total, returned=len(users))
            return response

        except Exception as e:
            raise self._handle_error(e, "get_all_users")

    async def update(self, resource_id: str, data: UserUpdate) -> Optional[User]:
        """
        Update a user.

        Example implementation showing basic update logic.
        """
        self._log_request("PUT", f"/users/{resource_id}")

        try:
            user_data = self._users_db.get(resource_id)
            if not user_data:
                self._log_response("PUT", f"/users/{resource_id}", 404)
                return None

            # Update with provided data
            update_dict = data.model_dump(exclude_unset=True)
            user_data.update(update_dict)
            user_data["updated_at"] = datetime.now(timezone.utc)

            # Return updated user
            user = User(**user_data)
            self._log_response("PUT", f"/users/{resource_id}", 200)
            return user

        except Exception as e:
            raise self._handle_error(e, f"update_user_{resource_id}")

    async def delete(self, resource_id: str) -> bool:
        """
        Delete a user.

        Example implementation showing basic deletion logic.
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

    # Additional methods showing common patterns

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email address.

        Example of a custom query method beyond basic CRUD.
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
