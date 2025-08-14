"""
Common Pydantic schemas used across the application.

This module provides commonly used schemas that don't belong
to a specific domain but are used throughout the API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import Field, field_validator

from src.schemas.base import BaseSchema, SuccessResponse, ErrorResponse


class SortOrder(str, Enum):
    """Enumeration for sort order options."""
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseSchema):
    """Schema for sorting parameters."""
    
    sort_by: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Field to sort by",
        json_schema_extra={"example": "created_at"}
    )
    sort_order: SortOrder = Field(
        default=SortOrder.ASC,
        description="Sort order (asc or desc)",
        json_schema_extra={"example": "asc"}
    )
    
    @field_validator('sort_by')
    @classmethod
    def validate_sort_by(cls, v: Optional[str]) -> Optional[str]:
        """Validate sort field name."""
        if v is None:
            return v
        
        # Only allow alphanumeric characters, underscores, and dots
        if not v.replace('_', '').replace('.', '').isalnum():
            raise ValueError("Sort field can only contain letters, numbers, underscores, and dots")
        
        return v


class BulkOperation(BaseSchema):
    """Schema for bulk operation requests."""
    
    ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of resource IDs to operate on (max 100)",
        json_schema_extra={"example": ["id1", "id2", "id3"]}
    )
    
    @field_validator('ids')
    @classmethod
    def validate_ids(cls, v: List[str]) -> List[str]:
        """Validate list of IDs."""
        if not v:
            raise ValueError("At least one ID is required")
        
        if len(v) > 100:
            raise ValueError("Cannot operate on more than 100 items at once")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate IDs are not allowed")
        
        # Validate each ID
        for id_val in v:
            if not id_val or id_val.isspace():
                raise ValueError("IDs cannot be empty or whitespace")
        
        return v


class BulkOperationResult(BaseSchema):
    """Schema for bulk operation results."""
    
    total: int = Field(
        ...,
        ge=0,
        description="Total number of items processed",
        json_schema_extra={"example": 10}
    )
    successful: int = Field(
        ...,
        ge=0,
        description="Number of items processed successfully",
        json_schema_extra={"example": 8}
    )
    failed: int = Field(
        ...,
        ge=0,
        description="Number of items that failed to process",
        json_schema_extra={"example": 2}
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Details of failed operations",
        json_schema_extra={
            "example": [
                {"id": "id9", "error": "Resource not found"},
                {"id": "id10", "error": "Validation failed"}
            ]
        }
    )


class HealthCheckResponse(SuccessResponse):
    """Schema for health check responses."""
    
    data: Dict[str, Any] = Field(
        ...,
        description="Health check data"
    )


class ReadinessCheckResponse(BaseSchema):
    """Schema for readiness check responses."""
    
    success: bool = Field(
        ...,
        description="Overall readiness status"
    )
    message: str = Field(
        ...,
        description="Readiness message"
    )
    data: Dict[str, Any] = Field(
        ...,
        description="Readiness check data including service checks"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of the check"
    )


class APIInfo(BaseSchema):
    """Schema for API information responses."""
    
    name: str = Field(
        ...,
        description="API name",
        json_schema_extra={"example": "Production API Framework"}
    )
    version: str = Field(
        ...,
        description="API version",
        json_schema_extra={"example": "1.0.0"}
    )
    environment: str = Field(
        ...,
        description="Current environment",
        json_schema_extra={"example": "production"}
    )
    docs_url: Optional[str] = Field(
        default=None,
        description="URL to API documentation",
        json_schema_extra={"example": "/docs"}
    )
    health_url: str = Field(
        ...,
        description="URL to health check endpoint",
        json_schema_extra={"example": "/healthz"}
    )
    readiness_url: str = Field(
        ...,
        description="URL to readiness check endpoint",
        json_schema_extra={"example": "/readyz"}
    )


class SearchParams(BaseSchema):
    """Schema for search parameters."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Search query",
        json_schema_extra={"example": "search term"}
    )
    fields: Optional[List[str]] = Field(
        default=None,
        max_length=10,
        description="Fields to search in (optional)",
        json_schema_extra={"example": ["name", "description"]}
    )
    exact_match: bool = Field(
        default=False,
        description="Whether to perform exact match search",
        json_schema_extra={"example": False}
    )
    case_sensitive: bool = Field(
        default=False,
        description="Whether search should be case sensitive",
        json_schema_extra={"example": False}
    )
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        v = v.strip()
        
        if not v:
            raise ValueError("Search query cannot be empty")
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '(', ')', '{', '}']
        if any(char in v for char in dangerous_chars):
            raise ValueError("Search query contains invalid characters")
        
        return v
    
    @field_validator('fields')
    @classmethod
    def validate_fields(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate search fields."""
        if v is None:
            return v
        
        if not v:
            raise ValueError("Fields list cannot be empty if provided")
        
        # Validate field names
        for field in v:
            if not field or field.isspace():
                raise ValueError("Field names cannot be empty")
            
            if not field.replace('_', '').replace('.', '').isalnum():
                raise ValueError("Field names can only contain letters, numbers, underscores, and dots")
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("Duplicate field names are not allowed")
        
        return v


class DateRangeParams(BaseSchema):
    """Schema for date range filtering parameters."""
    
    start_date: Optional[datetime] = Field(
        default=None,
        description="Start date for filtering",
        json_schema_extra={"example": "2024-01-01T00:00:00Z"}
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="End date for filtering",
        json_schema_extra={"example": "2024-12-31T23:59:59Z"}
    )
    
    def model_post_init(self, __context) -> None:
        """Validate date range after model initialization."""
        if (self.start_date is not None and 
            self.end_date is not None and 
            self.start_date >= self.end_date):
            raise ValueError("start_date must be before end_date")


class FileUploadInfo(BaseSchema):
    """Schema for file upload information."""
    
    filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Original filename",
        json_schema_extra={"example": "document.pdf"}
    )
    content_type: str = Field(
        ...,
        description="MIME type of the file",
        json_schema_extra={"example": "application/pdf"}
    )
    size: int = Field(
        ...,
        ge=0,
        description="File size in bytes",
        json_schema_extra={"example": 1024000}
    )
    upload_url: Optional[str] = Field(
        default=None,
        description="URL where the file was uploaded",
        json_schema_extra={"example": "/uploads/document.pdf"}
    )
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename."""
        v = v.strip()
        
        if not v:
            raise ValueError("Filename cannot be empty")
        
        # Check for dangerous characters
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in v for char in dangerous_chars):
            raise ValueError("Filename contains invalid characters")
        
        return v
    
    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type."""
        if not v or '/' not in v:
            raise ValueError("Invalid content type format")
        
        return v.lower()


class StatusUpdate(BaseSchema):
    """Schema for status update operations."""
    
    status: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="New status value",
        json_schema_extra={"example": "active"}
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for status change",
        json_schema_extra={"example": "User requested activation"}
    )
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status value."""
        v = v.strip().lower()
        
        if not v:
            raise ValueError("Status cannot be empty")
        
        # Only allow alphanumeric characters and underscores
        if not v.replace('_', '').isalnum():
            raise ValueError("Status can only contain letters, numbers, and underscores")
        
        return v