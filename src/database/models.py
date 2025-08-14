"""
Database models for the application.

This module defines all SQLAlchemy models with proper relationships,
constraints, and indexes.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, 
    String, Text, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum as PyEnum

from .base import Base, SoftDeleteMixin, AuditMixin


class UserStatus(PyEnum):
    """User account status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class UserRole(PyEnum):
    """User role enumeration."""
    GUEST = "guest"
    USER = "user"
    PREMIUM_USER = "premium_user"
    MODERATOR = "moderator"
    EDITOR = "editor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"
    API_USER = "api_user"
    API_SERVICE = "api_service"
    SYSTEM = "system"


class APIKeyStatus(PyEnum):
    """API key status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    REVOKED = "revoked"
    EXPIRED = "expired"


class User(Base, SoftDeleteMixin, AuditMixin):
    """
    User model for authentication and authorization.
    
    Represents a user account with authentication credentials,
    profile information, and role-based permissions.
    """
    
    # Authentication fields
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username for login"
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
        comment="Bcrypt hashed password"
    )
    
    # Profile fields
    full_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User's full name"
    )
    
    first_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="User's first name"
    )
    
    last_name: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="User's last name"
    )
    
    # Status and role fields
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus),
        default=UserStatus.PENDING,
        nullable=False,
        index=True,
        comment="User account status"
    )
    
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
        index=True,
        comment="User role for permissions"
    )
    
    # Account management fields
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Email verification status"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Account active status"
    )
    
    # Authentication tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last successful login timestamp"
    )
    
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of consecutive failed login attempts"
    )
    
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Account lock expiration timestamp"
    )
    
    # Email verification
    email_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email verification token"
    )
    
    email_verification_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Email verification token expiration"
    )
    
    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Password reset token"
    )
    
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Password reset token expiration"
    )
    
    # Relationships
    api_keys: Mapped[List["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def is_account_locked(self) -> bool:
        """Check if account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until
    
    def can_login(self) -> bool:
        """Check if user can login."""
        return (
            self.is_active and
            not self.is_deleted and
            self.status == UserStatus.ACTIVE and
            not self.is_account_locked()
        )
    
    def increment_failed_login(self, max_attempts: int = 5, lockout_duration: int = 3600) -> None:
        """Increment failed login attempts and lock account if needed."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
    
    def reset_failed_login(self) -> None:
        """Reset failed login attempts after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()
    
    def set_password_reset_token(self, token: str, expires_in: int = 3600) -> None:
        """Set password reset token with expiration."""
        self.password_reset_token = token
        self.password_reset_expires = datetime.utcnow() + timedelta(seconds=expires_in)
    
    def clear_password_reset_token(self) -> None:
        """Clear password reset token."""
        self.password_reset_token = None
        self.password_reset_expires = None
    
    def set_email_verification_token(self, token: str, expires_in: int = 86400) -> None:
        """Set email verification token with expiration."""
        self.email_verification_token = token
        self.email_verification_expires = datetime.utcnow() + timedelta(seconds=expires_in)
    
    def verify_email(self) -> None:
        """Mark email as verified and clear verification token."""
        self.is_verified = True
        self.email_verification_token = None
        self.email_verification_expires = None
        if self.status == UserStatus.PENDING:
            self.status = UserStatus.ACTIVE
    
    def to_dict(self, exclude: Optional[set] = None, include_relationships: bool = False) -> dict:
        """Convert to dictionary, excluding sensitive fields by default."""
        default_exclude = {
            'hashed_password', 'password_reset_token', 'email_verification_token'
        }
        if exclude:
            default_exclude.update(exclude)
        return super().to_dict(exclude=default_exclude, include_relationships=include_relationships)


class APIKey(Base, SoftDeleteMixin, AuditMixin):
    """
    API key model for API authentication.
    
    Represents API keys used for programmatic access to the API.
    """
    
    # API key fields
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable name for the API key"
    )
    
    key_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Hashed API key value"
    )
    
    key_prefix: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="First few characters of the key for identification"
    )
    
    # Status and permissions
    status: Mapped[APIKeyStatus] = mapped_column(
        Enum(APIKeyStatus),
        default=APIKeyStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="API key status"
    )
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last time this key was used"
    )
    
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total number of times this key has been used"
    )
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="API key expiration timestamp"
    )
    
    # User relationship
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="ID of the user who owns this API key"
    )
    
    user: Mapped[User] = relationship(
        "User",
        back_populates="api_keys",
        lazy="selectin"
    )
    
    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if API key is active and usable."""
        return (
            self.status == APIKeyStatus.ACTIVE and
            not self.is_deleted and
            not self.is_expired()
        )
    
    def record_usage(self, ip_address: Optional[str] = None) -> None:
        """Record API key usage."""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1
    
    def revoke(self) -> None:
        """Revoke the API key."""
        self.status = APIKeyStatus.REVOKED
    
    def set_expiration(self, expires_in_days: int) -> None:
        """Set API key expiration."""
        self.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
    
    def to_dict(self, exclude: Optional[set] = None, include_relationships: bool = False) -> dict:
        """Convert to dictionary, excluding sensitive fields by default."""
        default_exclude = {'key_hash'}
        if exclude:
            default_exclude.update(exclude)
        return super().to_dict(exclude=default_exclude, include_relationships=include_relationships)


class UserSession(Base):
    """
    User session model for tracking active sessions.
    
    Useful for session management and security monitoring.
    """
    
    # Session fields
    session_token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique session token"
    )
    
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey('user.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="ID of the user who owns this session"
    )
    
    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address of the session"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="User agent string"
    )
    
    # Session lifecycle
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Session expiration timestamp"
    )
    
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Last activity timestamp"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Session active status"
    )
    
    # Relationships
    user: Mapped[User] = relationship(
        "User",
        lazy="selectin"
    )
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if session is valid and active."""
        return self.is_active and not self.is_expired()
    
    def extend_session(self, extend_by_hours: int = 24) -> None:
        """Extend session expiration."""
        self.expires_at = datetime.utcnow() + timedelta(hours=extend_by_hours)
        self.last_activity_at = datetime.utcnow()
    
    def invalidate(self) -> None:
        """Invalidate the session."""
        self.is_active = False