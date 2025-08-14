"""
Base Pydantic schemas for request/response validation.

This module provides base schema classes with common functionality
and validation patterns that can be inherited by specific schemas.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


# Type variable for generic schemas
T = TypeVar('T')


class BaseSchema(BaseModel):
    """
    Base schema class with common configuration.

    This class provides common configuration and functionality
    that all schemas should inherit.
    """

    model_config = ConfigDict(
        # Enable validation of assignment
        validate_assignment=True,
        # Use enum values instead of names
        use_enum_values=True,
        # Validate default values
        validate_default=True,
        # Allow population by field name and alias
        populate_by_name=True,
        # Convert string representations to appropriate types
        str_strip_whitespace=True,
        # Forbid extra fields by default (can be overridden)
        extra='forbid',
        # Enable serialization of complex types
        arbitrary_types_allowed=False,
    )


class TimestampMixin(BaseModel):
    """
    Mixin for schemas that include timestamp fields.

    Provides created_at and updated_at fields with proper validation.
    """

    created_at: datetime = Field(
        ...,
        description="Timestamp when the resource was created",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"}
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when the resource was last updated",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"}
    )

    @field_validator('created_at', 'updated_at')
    @classmethod
    def validate_timestamps(cls, v: datetime) -> datetime:
        """Validate timestamp fields."""
        if v.tzinfo is None:
            # Assume UTC if no timezone info
            v = v.replace(tzinfo=datetime.now().astimezone().tzinfo)
        return v


class IdentifierMixin(BaseModel):
    """
    Mixin for schemas that include an ID field.

    Provides a standardized ID field with validation.
    """

    id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique identifier for the resource",
        json_schema_extra={"example": "resource_123"}
    )

    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate ID field."""
        if not v or v.isspace():
            raise ValueError("ID cannot be empty or whitespace")
        return v.strip()


class PaginationParams(BaseSchema):
    """
    Schema for pagination parameters.

    Provides standardized pagination with validation.
    """

    skip: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip",
        json_schema_extra={"example": 0}
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of items to return (1-100)",
        json_schema_extra={"example": 10}
    )


class PaginationMeta(BaseSchema):
    """
    Schema for pagination metadata.

    Provides standardized pagination information in responses.
    """

    total: int = Field(
        ...,
        ge=0,
        description="Total number of items available",
        json_schema_extra={"example": 100}
    )
    skip: int = Field(
        ...,
        ge=0,
        description="Number of items skipped",
        json_schema_extra={"example": 0}
    )
    limit: int = Field(
        ...,
        ge=1,
        description="Maximum number of items per page",
        json_schema_extra={"example": 10}
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
        json_schema_extra={"example": 1}
    )
    pages: int = Field(
        ...,
        ge=1,
        description="Total number of pages",
        json_schema_extra={"example": 10}
    )
    has_next: bool = Field(
        ...,
        description="Whether there are more items available",
        json_schema_extra={"example": True}
    )
    has_prev: bool = Field(
        ...,
        description="Whether there are previous items available",
        json_schema_extra={"example": False}
    )


class PaginatedResponse(BaseSchema, Generic[T]):
    """
    Generic schema for paginated responses.

    Provides a standardized structure for paginated API responses.
    """

    items: List[T] = Field(
        ...,
        description="List of items for the current page"
    )
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata"
    )


class SuccessResponse(BaseSchema):
    """
    Schema for successful API responses.

    Provides a standardized structure for success responses.
    """

    success: bool = Field(
        default=True,
        description="Indicates if the request was successful"
    )
    message: str = Field(
        ...,
        description="Human-readable success message",
        json_schema_extra={"example": "Operation completed successfully"}
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Response data (optional)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the response"
    )


class ErrorDetail(BaseSchema):
    """
    Schema for error details.

    Provides detailed information about validation or other errors.
    """

    field: Optional[str] = Field(
        default=None,
        description="Field name that caused the error (for validation errors)",
        json_schema_extra={"example": "email"}
    )
    message: str = Field(
        ...,
        description="Error message",
        json_schema_extra={"example": "This field is required"}
    )
    code: Optional[str] = Field(
        default=None,
        description="Error code for programmatic handling",
        json_schema_extra={"example": "FIELD_REQUIRED"}
    )


class ErrorResponse(BaseSchema):
    """
    Schema for error API responses.

    Provides a standardized structure for error responses.
    """

    success: bool = Field(
        default=False,
        description="Indicates if the request was successful"
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
        json_schema_extra={"example": "Validation failed"}
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Error code for programmatic handling",
        json_schema_extra={"example": "VALIDATION_ERROR"}
    )
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Detailed error information"
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="Request correlation ID for tracking",
        json_schema_extra={"example": "abc123-def456-ghi789"}
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the error",
        json_schema_extra={"example": "2024-01-15T10:30:00Z"}
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class HealthStatus(BaseSchema):
    """
    Schema for health check responses.

    Provides standardized health status information.
    """

    status: str = Field(
        ...,
        description="Health status",
        json_schema_extra={"example": "healthy"}
    )
    version: str = Field(
        ...,
        description="Application version",
        json_schema_extra={"example": "1.0.0"}
    )
    environment: str = Field(
        ...,
        description="Current environment",
        json_schema_extra={"example": "production"}
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the health check"
    )


class ServiceCheck(BaseSchema):
    """
    Schema for individual service health checks.

    Provides detailed information about service dependencies.
    """

    status: str = Field(
        ...,
        description="Service status",
        json_schema_extra={"example": "healthy"}
    )
    response_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Response time in milliseconds",
        json_schema_extra={"example": 5.2}
    )
    details: Optional[str] = Field(
        default=None,
        description="Additional details about the service check",
        json_schema_extra={"example": "Database connection successful"}
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the service is unhealthy",
        json_schema_extra={"example": "Connection timeout"}
    )


class ReadinessStatus(BaseSchema):
    """
    Schema for readiness check responses.

    Provides detailed readiness information including dependency checks.
    """

    status: str = Field(
        ...,
        description="Overall readiness status",
        json_schema_extra={"example": "ready"}
    )
    version: str = Field(
        ...,
        description="Application version",
        json_schema_extra={"example": "1.0.0"}
    )
    environment: str = Field(
        ...,
        description="Current environment",
        json_schema_extra={"example": "production"}
    )
    checks: Dict[str, ServiceCheck] = Field(
        ...,
        description="Individual service checks"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the readiness check"
    )


class CamelCaseSchema(BaseSchema):
    """
    Base schema that converts field names to camelCase for JSON serialization.

    Useful for APIs that need to follow camelCase naming conventions.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# Common field validators
def validate_non_empty_string(v: str) -> str:
    """Validate that a string is not empty or whitespace."""
    if not v or v.isspace():
        raise ValueError("Field cannot be empty or whitespace")
    return v.strip()


def validate_positive_number(v: float) -> float:
    """Validate that a number is positive."""
    if v <= 0:
        raise ValueError("Value must be positive")
    return v


def validate_non_negative_number(v: float) -> float:
    """Validate that a number is non-negative."""
    if v < 0:
        raise ValueError("Value must be non-negative")
    return v


# Common field definitions
def create_string_field(
    description: str,
    min_length: int = 1,
    max_length: int = 255,
    pattern: Optional[str] = None,
    example: Optional[str] = None
) -> Field:
    """Create a standardized string field with validation."""
    return Field(
        ...,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        description=description,
        json_schema_extra={"example": example} if example else None
    )


def create_optional_string_field(
    description: str,
    min_length: int = 1,
    max_length: int = 255,
    pattern: Optional[str] = None,
    example: Optional[str] = None
) -> Field:
    """Create a standardized optional string field with validation."""
    return Field(
        default=None,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        description=description,
        json_schema_extra={"example": example} if example else None
    )
