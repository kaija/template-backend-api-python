"""
Base service classes with common business logic patterns.

This module provides base service classes that encapsulate business logic
and serve as templates for domain-specific services.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from datetime import datetime

from pydantic import BaseModel

from src.database.repositories import BaseRepository


# Type variables for generic services
T = TypeVar('T')  # Domain model type
CreateT = TypeVar('CreateT', bound=BaseModel)  # Create schema type
UpdateT = TypeVar('UpdateT', bound=BaseModel)  # Update schema type
ResponseT = TypeVar('ResponseT', bound=BaseModel)  # Response schema type


class ServiceError(Exception):
    """Base exception for service layer operations."""
    pass


class ValidationError(ServiceError):
    """Exception raised when business validation fails."""
    pass


class NotFoundError(ServiceError):
    """Exception raised when a resource is not found."""
    pass


class DuplicateError(ServiceError):
    """Exception raised when trying to create a duplicate resource."""
    pass


class BaseService(ABC):
    """
    Base service class with common business logic patterns.

    This class provides common functionality that all services can inherit,
    including logging, validation, and error handling patterns.
    """

    def __init__(self):
        """Initialize the base service."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def _log_operation(self, operation: str, resource_type: str, **kwargs) -> None:
        """
        Log service operations.

        Args:
            operation: Operation being performed (create, update, delete, etc.)
            resource_type: Type of resource being operated on
            **kwargs: Additional context to log
        """
        self.logger.info(
            f"{operation} {resource_type}",
            extra={
                "operation": operation,
                "resource_type": resource_type,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )

    def _validate_business_rules(self, data: Any, context: str = "") -> None:
        """
        Template method for business rule validation.

        Override this method in concrete services to implement
        domain-specific business rules.

        Args:
            data: Data to validate
            context: Context of the validation (create, update, etc.)

        Raises:
            ValidationError: If business rules are violated
        """
        # Default implementation - override in concrete services
        pass

    def _handle_repository_error(self, error: Exception, operation: str) -> None:
        """
        Handle repository layer errors and convert to service errors.

        Args:
            error: Repository error
            operation: Operation that caused the error

        Raises:
            ServiceError: Appropriate service layer error
        """
        from src.database.repositories import NotFoundError as RepoNotFoundError
        from src.database.repositories import DuplicateError as RepoDuplicateError

        if isinstance(error, RepoNotFoundError):
            raise NotFoundError(str(error))
        elif isinstance(error, RepoDuplicateError):
            raise DuplicateError(str(error))
        else:
            self.logger.error(f"Repository error in {operation}: {error}")
            raise ServiceError(f"Operation {operation} failed: {str(error)}")


class CRUDService(BaseService, Generic[T, CreateT, UpdateT, ResponseT]):
    """
    Base CRUD service with common business logic operations.

    This class provides a template for services that need to implement
    Create, Read, Update, Delete operations with business logic.
    """

    def __init__(self, repository: BaseRepository[T]):
        """
        Initialize the CRUD service.

        Args:
            repository: Repository instance for data access
        """
        super().__init__()
        self.repository = repository

    @abstractmethod
    async def create(self, data: CreateT) -> ResponseT:
        """
        Create a new resource with business logic validation.

        Args:
            data: Data for creating the resource

        Returns:
            Created resource response

        Raises:
            ValidationError: If business validation fails
            DuplicateError: If resource already exists
        """
        pass

    @abstractmethod
    async def get_by_id(self, resource_id: str) -> Optional[ResponseT]:
        """
        Get a resource by ID.

        Args:
            resource_id: ID of the resource

        Returns:
            Resource response if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get all resources with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply

        Returns:
            Dictionary with resources and pagination info
        """
        pass

    @abstractmethod
    async def update(self, resource_id: str, data: UpdateT) -> Optional[ResponseT]:
        """
        Update a resource with business logic validation.

        Args:
            resource_id: ID of the resource to update
            data: Data for updating the resource

        Returns:
            Updated resource response if found, None otherwise

        Raises:
            ValidationError: If business validation fails
            NotFoundError: If resource is not found
        """
        pass

    @abstractmethod
    async def delete(self, resource_id: str) -> bool:
        """
        Delete a resource with business logic validation.

        Args:
            resource_id: ID of the resource to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValidationError: If business validation prevents deletion
        """
        pass

    def _validate_pagination(self, skip: int, limit: int) -> None:
        """
        Validate pagination parameters.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Raises:
            ValidationError: If pagination parameters are invalid
        """
        if skip < 0:
            raise ValidationError("Skip parameter must be non-negative")

        if limit <= 0:
            raise ValidationError("Limit parameter must be positive")

        # Default max limit - can be overridden in concrete services
        max_limit = 1000
        if limit > max_limit:
            raise ValidationError(f"Limit parameter cannot exceed {max_limit}")

    def _create_paginated_response(
        self,
        items: List[ResponseT],
        total: int,
        skip: int,
        limit: int
    ) -> Dict[str, Any]:
        """
        Create a paginated response.

        Args:
            items: List of items for current page
            total: Total number of items
            skip: Number of records skipped
            limit: Maximum number of records per page

        Returns:
            Paginated response dictionary
        """
        return {
            "items": items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "page": (skip // limit) + 1,
                "pages": (total + limit - 1) // limit,
                "has_next": skip + limit < total,
                "has_prev": skip > 0,
            }
        }


class ExampleUserService(CRUDService):
    """
    Example service demonstrating common patterns.

    This serves as a template for implementing domain-specific services.
    Shows how to implement business logic, validation, and error handling.
    """

    def __init__(self, user_repository):
        """
        Initialize the user service.

        Args:
            user_repository: User repository instance
        """
        super().__init__(user_repository)

    async def create(self, data) -> Dict[str, Any]:
        """
        Create a new user with business logic validation.

        This is an example implementation showing common patterns:
        - Business rule validation
        - Duplicate checking
        - Password hashing
        - Logging
        """
        try:
            self._log_operation("create", "user", username=data.get("username"))

            # Example business rule validation
            self._validate_business_rules(data, "create")

            # Example: Check for duplicates
            existing_user = await self.repository.get_by_email(data.get("email", ""))
            if existing_user:
                raise DuplicateError("User with this email already exists")

            # Example: Hash password (in real implementation, use proper hashing)
            create_data = data.copy()
            if "password" in create_data:
                # In real implementation, use bcrypt or similar
                create_data["hashed_password"] = f"hashed_{create_data.pop('password')}"

            # Create the user
            user = await self.repository.create(**create_data)

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            }

        except Exception as e:
            self._handle_repository_error(e, "create_user")

    async def get_by_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            user = await self.repository.get_by_id(resource_id)
            if not user:
                return None

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            }

        except Exception as e:
            self._handle_repository_error(e, "get_user_by_id")

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get all users with pagination."""
        try:
            self._validate_pagination(skip, limit)

            users = await self.repository.list_all(limit=limit, offset=skip)
            total = await self.repository.count()

            user_responses = [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "status": user.status,
                    "created_at": user.created_at.isoformat(),
                }
                for user in users
            ]

            return self._create_paginated_response(user_responses, total, skip, limit)

        except Exception as e:
            self._handle_repository_error(e, "get_all_users")

    async def update(self, resource_id: str, data) -> Optional[Dict[str, Any]]:
        """Update user with business logic validation."""
        try:
            self._log_operation("update", "user", user_id=resource_id)

            # Example business rule validation
            self._validate_business_rules(data, "update")

            # Update the user
            user = await self.repository.update(resource_id, **data)

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "status": user.status,
                "updated_at": user.updated_at.isoformat(),
            }

        except Exception as e:
            self._handle_repository_error(e, "update_user")

    async def delete(self, resource_id: str) -> bool:
        """Delete user with business logic validation."""
        try:
            self._log_operation("delete", "user", user_id=resource_id)

            # Example: Check if user can be deleted
            user = await self.repository.get_by_id(resource_id)
            if not user:
                return False

            # Example business rule: Don't delete active users
            if user.status == "active":
                raise ValidationError("Cannot delete active users")

            return await self.repository.delete(resource_id)

        except Exception as e:
            self._handle_repository_error(e, "delete_user")

    def _validate_business_rules(self, data: Any, context: str = "") -> None:
        """
        Example business rule validation.

        Override this method to implement domain-specific validation rules.
        """
        if context == "create":
            # Example: Validate required fields
            if not data.get("username"):
                raise ValidationError("Username is required")
            if not data.get("email"):
                raise ValidationError("Email is required")

            # Example: Validate username format
            username = data.get("username", "")
            if len(username) < 3:
                raise ValidationError("Username must be at least 3 characters")

        elif context == "update":
            # Example: Validate update data
            if "email" in data and not data["email"]:
                raise ValidationError("Email cannot be empty")
