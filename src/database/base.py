"""
Base model class and common database utilities.

This module provides the base model class with common fields
and utilities for all database models.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import expression


class Base(DeclarativeBase):
    """
    Base class for all database models.
    
    Provides common fields and utilities that all models should have.
    """
    
    # Abstract base - no table will be created for this class
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\\1_\\2', cls.__name__)
        return re.sub('([a-z0-9])([A-Z])', r'\\1_\\2', name).lower()
    
    # Primary key - use UUID for better distribution and security
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        comment="Primary key UUID"
    )
    
    # Timestamps - automatically managed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )
    
    def to_dict(
        self, 
        exclude: Optional[set] = None,
        include_relationships: bool = False
    ) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.
        
        Args:
            exclude: Set of field names to exclude
            include_relationships: Whether to include relationship data
            
        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or set()
        result = {}
        
        # Include column attributes
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        
        # Include relationships if requested
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                if relationship.key not in exclude:
                    value = getattr(self, relationship.key)
                    if value is not None:
                        if hasattr(value, '__iter__') and not isinstance(value, (str, bytes)):
                            # Collection relationship
                            result[relationship.key] = [
                                item.to_dict(exclude=exclude) if hasattr(item, 'to_dict') else str(item)
                                for item in value
                            ]
                        else:
                            # Single relationship
                            result[relationship.key] = (
                                value.to_dict(exclude=exclude) if hasattr(value, 'to_dict') else str(value)
                            )
        
        return result
    
    def update_from_dict(
        self, 
        data: Dict[str, Any], 
        exclude: Optional[set] = None
    ) -> None:
        """
        Update model instance from dictionary.
        
        Args:
            data: Dictionary with field values
            exclude: Set of field names to exclude from update
        """
        exclude = exclude or {'id', 'created_at', 'updated_at'}
        
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.__repr__()


class TimestampMixin:
    """
    Mixin for models that need timestamp fields.
    
    Use this for models that don't inherit from Base but need timestamps.
    """
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Record last update timestamp"
    )


class SoftDeleteMixin:
    """
    Mixin for models that support soft deletion.
    
    Soft deleted records are marked as deleted but not physically removed.
    """
    
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Soft deletion timestamp"
    )
    
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Soft deletion flag"
    )
    
    def soft_delete(self) -> None:
        """Mark record as soft deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """
    Mixin for models that need audit trail fields.
    
    Tracks who created and last modified the record.
    """
    
    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="ID of user who created the record"
    )
    
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        comment="ID of user who last updated the record"
    )
    
    def set_created_by(self, user_id: str) -> None:
        """Set the creator of the record."""
        self.created_by = user_id
    
    def set_updated_by(self, user_id: str) -> None:
        """Set the last updater of the record."""
        self.updated_by = user_id


class VersionMixin:
    """
    Mixin for models that need optimistic locking.
    
    Uses a version field to prevent concurrent modification conflicts.
    """
    
    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False,
        comment="Version number for optimistic locking"
    )
    
    def increment_version(self) -> None:
        """Increment the version number."""
        self.version += 1