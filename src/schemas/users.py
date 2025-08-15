"""
Example User Pydantic schemas for request/response validation.

This module demonstrates Pydantic models for user-related API requests
and responses. These serve as examples that can be adapted for your
specific domain models and validation requirements.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import EmailStr, Field, field_validator, ConfigDict
import re

from src.schemas.base import (
    BaseSchema,
    IdentifierMixin,
    TimestampMixin,
    PaginatedResponse,
    create_string_field,
    create_optional_string_field,
    validate_non_empty_string
)


class UserBase(BaseSchema):
    """Base user schema demonstrating common validation patterns."""

    username: str = create_string_field(
        description="Username (3-50 characters, alphanumeric, underscore, hyphen only)",
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        example="johndoe"
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address",
        json_schema_extra={"example": "john.doe@example.com"}
    )
    full_name: Optional[str] = create_optional_string_field(
        description="Full name (optional, max 100 characters)",
        min_length=1,
        max_length=100,
        example="John Doe"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format and content."""
        v = validate_non_empty_string(v)

        # Check for reserved usernames
        reserved_usernames = {
            'admin', 'administrator', 'root', 'system', 'api', 'www',
            'mail', 'email', 'support', 'help', 'info', 'contact',
            'test', 'demo', 'guest', 'anonymous', 'null', 'undefined'
        }

        if v.lower() in reserved_usernames:
            raise ValueError(f"Username '{v}' is reserved and cannot be used")

        # Check for consecutive special characters
        if '--' in v or '__' in v or '-_' in v or '_-' in v:
            raise ValueError("Username cannot contain consecutive special characters")

        # Cannot start or end with special characters
        if v.startswith(('-', '_')) or v.endswith(('-', '_')):
            raise ValueError("Username cannot start or end with special characters")

        return v

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate full name format."""
        if v is None:
            return v

        v = validate_non_empty_string(v)

        # Check for valid characters (letters, spaces, common punctuation)
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError("Full name can only contain letters, spaces, hyphens, apostrophes, and periods")

        # Check for reasonable format (not all spaces or special chars)
        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Full name must contain at least one letter")

        # Normalize spaces
        v = ' '.join(v.split())

        return v


class UserCreate(UserBase):
    """Example schema for creating a new user with password validation patterns."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 characters, must meet security requirements)",
        json_schema_extra={"example": "SecurePassword123!"}
    )
    confirm_password: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Password confirmation (must match password)",
        json_schema_extra={"example": "SecurePassword123!"}
    )

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength and security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")

        # Check for at least one lowercase letter
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")

        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")

        # Check for at least one digit
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")

        # Check for at least one special character
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            raise ValueError("Password must contain at least one special character")

        # Check for common weak passwords
        weak_passwords = {
            'password', 'password123', '12345678', 'qwerty123',
            'admin123', 'letmein', 'welcome123', 'changeme',
            'password123!', 'admin123!', 'welcome123!'  # Add some that meet basic requirements
        }

        if v.lower() in weak_passwords:
            raise ValueError("Password is too common and not secure")

        # Check for repeated characters (more than 3 in a row)
        if re.search(r"(.)\1{3,}", v):
            raise ValueError("Password cannot contain more than 3 consecutive identical characters")

        return v

    def model_post_init(self, __context) -> None:
        """Validate password confirmation after model initialization."""
        if self.confirm_password is not None and self.password != self.confirm_password:
            raise ValueError("Password and confirmation password do not match")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "password": "SecurePassword123!",
                "confirm_password": "SecurePassword123!"
            }
        }
    )


class UserUpdate(BaseSchema):
    """Example schema for updating users, demonstrating partial validation patterns."""

    username: Optional[str] = create_optional_string_field(
        description="Username (3-50 characters, alphanumeric, underscore, hyphen only)",
        min_length=3,
        max_length=50,
        pattern="^[a-zA-Z0-9_-]+$",
        example="johndoe_updated"
    )
    email: Optional[EmailStr] = Field(
        default=None,
        description="Valid email address",
        json_schema_extra={"example": "john.updated@example.com"}
    )
    full_name: Optional[str] = create_optional_string_field(
        description="Full name (optional, max 100 characters)",
        min_length=1,
        max_length=100,
        example="John Updated Doe"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether the user account is active",
        json_schema_extra={"example": True}
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate username if provided."""
        if v is None:
            return v
        return UserBase.validate_username(v)

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate full name if provided."""
        if v is None:
            return v
        return UserBase.validate_full_name(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "johndoe_updated",
                "email": "john.updated@example.com",
                "full_name": "John Updated Doe",
                "is_active": True
            }
        }
    )


class User(UserBase, IdentifierMixin, TimestampMixin):
    """Example response schema demonstrating how to combine mixins."""

    is_active: bool = Field(
        default=True,
        description="Whether the user account is active",
        json_schema_extra={"example": True}
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the user's last login",
        json_schema_extra={"example": "2024-01-15T14:30:00Z"}
    )
    login_count: int = Field(
        default=0,
        ge=0,
        description="Number of times the user has logged in",
        json_schema_extra={"example": 42}
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "user_123",
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "is_active": True,
                "last_login": "2024-01-15T14:30:00Z",
                "login_count": 42,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    )


class UserList(PaginatedResponse[User]):
    """Example paginated response schema."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "user_123",
                        "username": "johndoe",
                        "email": "john.doe@example.com",
                        "full_name": "John Doe",
                        "is_active": True,
                        "last_login": "2024-01-15T14:30:00Z",
                        "login_count": 42,
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "pagination": {
                    "total": 100,
                    "skip": 0,
                    "limit": 10,
                    "page": 1,
                    "pages": 10,
                    "has_next": True,
                    "has_prev": False
                }
            }
        }
    )


class UserFilters(BaseSchema):
    """Example filtering schema demonstrating query parameter validation."""

    is_active: Optional[bool] = Field(
        default=None,
        description="Filter by active status",
        json_schema_extra={"example": True}
    )
    search: Optional[str] = create_optional_string_field(
        description="Search in username, email, or full name",
        min_length=1,
        max_length=100,
        example="john"
    )
    created_after: Optional[datetime] = Field(
        default=None,
        description="Filter users created after this date",
        json_schema_extra={"example": "2024-01-01T00:00:00Z"}
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Filter users created before this date",
        json_schema_extra={"example": "2024-12-31T23:59:59Z"}
    )
    has_logged_in: Optional[bool] = Field(
        default=None,
        description="Filter by whether user has ever logged in",
        json_schema_extra={"example": True}
    )

    @field_validator('search')
    @classmethod
    def validate_search(cls, v: Optional[str]) -> Optional[str]:
        """Validate search term."""
        if v is None:
            return v

        v = validate_non_empty_string(v)

        # Remove potentially dangerous characters for search
        if any(char in v for char in ['<', '>', '"', "'", '&', ';']):
            raise ValueError("Search term contains invalid characters")

        return v

    def model_post_init(self, __context) -> None:
        """Validate date range after model initialization."""
        if (self.created_after is not None and
            self.created_before is not None and
            self.created_after >= self.created_before):
            raise ValueError("created_after must be before created_before")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_active": True,
                "search": "john",
                "created_after": "2024-01-01T00:00:00Z",
                "created_before": "2024-12-31T23:59:59Z",
                "has_logged_in": True
            }
        }
    )


class UserPasswordChange(BaseSchema):
    """Example schema for password change operations."""

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Current password for verification",
        json_schema_extra={"example": "OldPassword123!"}
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (must meet security requirements)",
        json_schema_extra={"example": "NewSecurePassword123!"}
    )
    confirm_new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Confirmation of new password",
        json_schema_extra={"example": "NewSecurePassword123!"}
    )

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password using the same rules as UserCreate."""
        return UserCreate.validate_password(v)

    def model_post_init(self, __context) -> None:
        """Validate password confirmation and ensure passwords are different."""
        if self.new_password != self.confirm_new_password:
            raise ValueError("New password and confirmation do not match")

        if self.current_password == self.new_password:
            raise ValueError("New password must be different from current password")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "OldPassword123!",
                "new_password": "NewSecurePassword123!",
                "confirm_new_password": "NewSecurePassword123!"
            }
        }
    )


class UserSummary(BaseSchema):
    """Example minimal response schema for summary information."""

    id: str = Field(
        ...,
        description="Unique user identifier",
        json_schema_extra={"example": "user_123"}
    )
    username: str = Field(
        ...,
        description="Username",
        json_schema_extra={"example": "johndoe"}
    )
    full_name: Optional[str] = Field(
        default=None,
        description="Full name",
        json_schema_extra={"example": "John Doe"}
    )
    is_active: bool = Field(
        ...,
        description="Whether the user account is active",
        json_schema_extra={"example": True}
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "user_123",
                "username": "johndoe",
                "full_name": "John Doe",
                "is_active": True
            }
        }
    )
