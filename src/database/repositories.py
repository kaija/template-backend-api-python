"""
Repository pattern implementation for data access.

This module provides repository classes that abstract database operations
and provide a clean interface for data access.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from datetime import datetime
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, NoResultFound

from .base import Base
from .models import User, Post

logger = logging.getLogger(__name__)

# Type variable for generic repository
T = TypeVar('T', bound=Base)


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class NotFoundError(RepositoryError):
    """Exception raised when a record is not found."""
    pass


class DuplicateError(RepositoryError):
    """Exception raised when trying to create a duplicate record."""
    pass


class BaseRepository(Generic[T], ABC):
    """
    Abstract base repository class.

    Provides common CRUD operations for all repositories.
    """

    def __init__(self, session: AsyncSession, model_class: Type[T]):
        """
        Initialize repository.

        Args:
            session: SQLAlchemy async session
            model_class: Model class for this repository
        """
        self.session = session
        self.model_class = model_class

    async def create(self, **kwargs) -> T:
        """
        Create a new record.

        Args:
            **kwargs: Field values for the new record

        Returns:
            Created model instance

        Raises:
            DuplicateError: If record violates unique constraints
        """
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)

            logger.info(
                f"Created {self.model_class.__name__} with ID: {instance.id}",
                extra={
                    "event_type": "record_created",
                    "model": self.model_class.__name__,
                    "record_id": instance.id,
                }
            )

            return instance

        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(
                f"Failed to create {self.model_class.__name__}: {e}",
                extra={
                    "event_type": "record_create_failed",
                    "model": self.model_class.__name__,
                    "error": str(e),
                }
            )
            raise DuplicateError(f"Record violates unique constraints: {e}")

    async def get_by_id(self, record_id: str) -> Optional[T]:
        """
        Get record by ID.

        Args:
            record_id: Record ID

        Returns:
            Model instance or None if not found
        """
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, record_id: str) -> T:
        """
        Get record by ID or raise exception.

        Args:
            record_id: Record ID

        Returns:
            Model instance

        Raises:
            NotFoundError: If record is not found
        """
        instance = await self.get_by_id(record_id)
        if instance is None:
            raise NotFoundError(f"{self.model_class.__name__} with ID {record_id} not found")
        return instance

    async def update(self, record_id: str, **kwargs) -> T:
        """
        Update record by ID.

        Args:
            record_id: Record ID
            **kwargs: Field values to update

        Returns:
            Updated model instance

        Raises:
            NotFoundError: If record is not found
        """
        instance = await self.get_by_id_or_raise(record_id)

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)

        logger.info(
            f"Updated {self.model_class.__name__} with ID: {record_id}",
            extra={
                "event_type": "record_updated",
                "model": self.model_class.__name__,
                "record_id": record_id,
                "updated_fields": list(kwargs.keys()),
            }
        )

        return instance

    async def delete(self, record_id: str) -> bool:
        """
        Delete record by ID.

        Args:
            record_id: Record ID

        Returns:
            True if record was deleted, False if not found
        """
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == record_id)
        )

        deleted = result.rowcount > 0

        if deleted:
            logger.info(
                f"Deleted {self.model_class.__name__} with ID: {record_id}",
                extra={
                    "event_type": "record_deleted",
                    "model": self.model_class.__name__,
                    "record_id": record_id,
                }
            )

        return deleted

    async def list_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[T]:
        """
        List all records.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field name to order by

        Returns:
            List of model instances
        """
        query = select(self.model_class)

        if order_by and hasattr(self.model_class, order_by):
            query = query.order_by(getattr(self.model_class, order_by))

        if offset:
            query = query.offset(offset)

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self) -> int:
        """
        Count total number of records.

        Returns:
            Total record count
        """
        result = await self.session.execute(
            select(func.count(self.model_class.id))
        )
        return result.scalar() or 0

    async def exists(self, record_id: str) -> bool:
        """
        Check if record exists.

        Args:
            record_id: Record ID

        Returns:
            True if record exists, False otherwise
        """
        result = await self.session.execute(
            select(func.count(self.model_class.id)).where(
                self.model_class.id == record_id
            )
        )
        return (result.scalar() or 0) > 0


class UserRepository(BaseRepository[User]):
    """
    Example repository for User model operations.

    This serves as a template for implementing domain-specific repositories.
    Shows common patterns for custom queries and business logic.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.

        Example of a custom query method that extends the base repository.
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.

        Another example of a domain-specific query method.
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, limit: int = 100) -> List[User]:
        """
        Get active users.

        Example of a business logic query that filters by status.
        """
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)
            .limit(limit)
        )
        return list(result.scalars().all())


class PostRepository(BaseRepository[Post]):
    """
    Example repository for Post model operations.

    Demonstrates relationship handling and complex queries.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session, Post)

    async def get_by_author(self, author_id: str) -> List[Post]:
        """
        Get posts by author.

        Example of querying with relationships.
        """
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.author))
            .where(Post.author_id == author_id)
        )
        return list(result.scalars().all())

    async def get_published_posts(self, limit: int = 100) -> List[Post]:
        """
        Get published posts.

        Example of filtering by business logic status.
        """
        result = await self.session.execute(
            select(Post)
            .options(selectinload(Post.author))
            .where(Post.is_published == True)
            .order_by(Post.published_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


# Repository factory for dependency injection
class RepositoryFactory:
    """
    Factory class for creating repository instances.

    Provides a centralized way to create repositories with proper session management.
    This pattern makes it easy to inject repositories into services and controllers.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @property
    def users(self) -> UserRepository:
        """Get user repository instance."""
        return UserRepository(self.session)

    @property
    def posts(self) -> PostRepository:
        """Get post repository instance."""
        return PostRepository(self.session)

    def get_repository(self, model_class: Type[T]) -> BaseRepository[T]:
        """
        Get a generic repository for any model class.

        This is useful for creating repositories dynamically
        or for models that don't need custom repository methods.
        """
        return BaseRepository(self.session, model_class)
