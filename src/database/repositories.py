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
from .models import User, APIKey, UserSession, UserStatus, APIKeyStatus

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
    Repository for User model operations.
    
    Provides user-specific database operations and queries.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Get user by username.
        
        Args:
            username: Username to search for
            
        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: Email to search for
            
        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username_or_email(self, identifier: str) -> Optional[User]:
        """
        Get user by username or email.
        
        Args:
            identifier: Username or email to search for
            
        Returns:
            User instance or None if not found
        """
        result = await self.session.execute(
            select(User).where(
                or_(User.username == identifier, User.email == identifier)
            )
        )
        return result.scalar_one_or_none()
    
    async def create_user(
        self,
        username: str,
        email: str,
        hashed_password: str,
        **kwargs
    ) -> User:
        """
        Create a new user.
        
        Args:
            username: Unique username
            email: Unique email address
            hashed_password: Bcrypt hashed password
            **kwargs: Additional user fields
            
        Returns:
            Created user instance
            
        Raises:
            DuplicateError: If username or email already exists
        """
        return await self.create(
            username=username,
            email=email,
            hashed_password=hashed_password,
            **kwargs
        )


class APIKeyRepository(BaseRepository[APIKey]):
    """
    Repository for API Key model operations.
    
    Provides API key-specific database operations and queries.
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, APIKey)
    
    async def get_by_key_hash(self, key_hash: str) -> Optional[APIKey]:
        """
        Get API key by hash.
        
        Args:
            key_hash: Hashed API key value
            
        Returns:
            APIKey instance or None if not found
        """
        result = await self.session.execute(
            select(APIKey)
            .options(selectinload(APIKey.user))
            .where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()


# Repository factory for dependency injection
class RepositoryFactory:
    """
    Factory class for creating repository instances.
    
    Provides a centralized way to create repositories with proper session management.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    @property
    def users(self) -> UserRepository:
        """Get user repository."""
        return UserRepository(self.session)
    
    @property
    def api_keys(self) -> APIKeyRepository:
        """Get API key repository."""
        return APIKeyRepository(self.session)