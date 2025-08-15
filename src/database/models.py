"""
Generic database models for the framework.

This module provides example models that demonstrate common patterns
and relationships. These serve as templates for building domain-specific models.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum as PyEnum

from .base import Base, SoftDeleteMixin, AuditMixin


class UserStatus(PyEnum):
    """Example user status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class User(Base, SoftDeleteMixin, AuditMixin):
    """
    Example User model demonstrating common patterns.

    This serves as a template for user-related entities in your application.
    Extend or modify this model based on your specific requirements.
    """

    # Basic user fields
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username"
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address"
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password"
    )

    # Profile information
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User's full name"
    )

    # Status fields
    status: Mapped[UserStatus] = mapped_column(
        String(20),  # Using String instead of Enum for simplicity
        default=UserStatus.PENDING.value,
        nullable=False,
        index=True,
        comment="User account status"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Account active status"
    )

    # Relationships - example of one-to-many relationship
    posts: Mapped[List["Post"]] = relationship(
        "Post",
        back_populates="author",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    def to_dict(self, exclude: Optional[set] = None, include_relationships: bool = False) -> dict:
        """Convert to dictionary, excluding sensitive fields by default."""
        default_exclude = {'hashed_password'}
        if exclude:
            default_exclude.update(exclude)
        return super().to_dict(exclude=default_exclude, include_relationships=include_relationships)


class Post(Base, SoftDeleteMixin, AuditMixin):
    """
    Example Post model demonstrating relationships and common patterns.

    This serves as a template for content-related entities in your application.
    Shows how to implement many-to-one relationships with the User model.
    """

    # Content fields
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Post title"
    )

    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Post content"
    )

    # Status and metadata
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Publication status"
    )

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Publication timestamp"
    )

    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of views"
    )

    # Foreign key relationship
    author_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="ID of the user who authored this post"
    )

    # Relationship back to User
    author: Mapped[User] = relationship(
        "User",
        back_populates="posts",
        lazy="selectin"
    )

    def publish(self) -> None:
        """Publish the post."""
        self.is_published = True
        self.published_at = datetime.now(timezone.utc)

    def unpublish(self) -> None:
        """Unpublish the post."""
        self.is_published = False
        self.published_at = None

    def increment_view_count(self) -> None:
        """Increment the view count."""
        self.view_count += 1
