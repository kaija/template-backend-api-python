"""
Simple tests for custom exception classes.

This module tests the custom exception classes without requiring
the full configuration system.
"""

import os
import pytest
from unittest.mock import Mock, patch

# Skip configuration validation and initialization for tests
os.environ["SKIP_CONFIG_VALIDATION"] = "1"
os.environ["SKIP_CONFIG_INIT"] = "1"

from src.schemas.base import ErrorDetail


class TestErrorDetail:
    """Test ErrorDetail schema."""
    
    def test_error_detail_creation(self):
        """Test ErrorDetail creation."""
        detail = ErrorDetail(
            field="email",
            message="Invalid format",
            code="INVALID_FORMAT"
        )
        
        assert detail.field == "email"
        assert detail.message == "Invalid format"
        assert detail.code == "INVALID_FORMAT"
    
    def test_error_detail_optional_fields(self):
        """Test ErrorDetail with optional fields."""
        detail = ErrorDetail(message="Required field missing")
        
        assert detail.field is None
        assert detail.message == "Required field missing"
        assert detail.code is None


# Mock the configuration functions to avoid import issues
@patch('src.exceptions.is_development')
@patch('src.exceptions.is_production')
class TestCustomExceptionsSimple:
    """Test custom exception classes with mocked configuration."""
    
    def test_api_exception_basic(self, mock_is_prod, mock_is_dev):
        """Test basic APIException functionality."""
        from src.exceptions import APIException
        
        exc = APIException(
            status_code=400,
            message="Test error",
            error_code="TEST_ERROR"
        )
        
        assert exc.status_code == 400
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == []
    
    def test_api_exception_with_details(self, mock_is_prod, mock_is_dev):
        """Test APIException with error details."""
        from src.exceptions import APIException
        
        details = [
            ErrorDetail(field="email", message="Invalid format", code="INVALID_FORMAT")
        ]
        
        exc = APIException(
            status_code=400,
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            details=details
        )
        
        assert exc.details == details
    
    def test_validation_exception(self, mock_is_prod, mock_is_dev):
        """Test ValidationException."""
        from src.exceptions import ValidationException
        
        exc = ValidationException(message="Custom validation error")
        
        assert exc.status_code == 400
        assert exc.message == "Custom validation error"
        assert exc.error_code == "VALIDATION_ERROR"
    
    def test_authentication_exception(self, mock_is_prod, mock_is_dev):
        """Test AuthenticationException."""
        from src.exceptions import AuthenticationException
        
        exc = AuthenticationException()
        
        assert exc.status_code == 401
        assert exc.message == "Authentication failed"
        assert exc.error_code == "AUTHENTICATION_FAILED"
        assert exc.headers == {"WWW-Authenticate": "Bearer"}
    
    def test_authorization_exception(self, mock_is_prod, mock_is_dev):
        """Test AuthorizationException."""
        from src.exceptions import AuthorizationException
        
        exc = AuthorizationException()
        
        assert exc.status_code == 403
        assert exc.message == "Access denied"
        assert exc.error_code == "ACCESS_DENIED"
    
    def test_not_found_exception(self, mock_is_prod, mock_is_dev):
        """Test NotFoundException."""
        from src.exceptions import NotFoundException
        
        exc = NotFoundException(message="User not found")
        
        assert exc.status_code == 404
        assert exc.message == "User not found"
        assert exc.error_code == "RESOURCE_NOT_FOUND"
    
    def test_conflict_exception(self, mock_is_prod, mock_is_dev):
        """Test ConflictException."""
        from src.exceptions import ConflictException
        
        exc = ConflictException(message="Email already exists")
        
        assert exc.status_code == 409
        assert exc.message == "Email already exists"
        assert exc.error_code == "RESOURCE_CONFLICT"
    
    def test_rate_limit_exception(self, mock_is_prod, mock_is_dev):
        """Test RateLimitException."""
        from src.exceptions import RateLimitException
        
        exc = RateLimitException(retry_after=60)
        
        assert exc.status_code == 429
        assert exc.message == "Rate limit exceeded"
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.headers == {"Retry-After": "60"}
    
    def test_internal_server_exception(self, mock_is_prod, mock_is_dev):
        """Test InternalServerException."""
        from src.exceptions import InternalServerException
        
        exc = InternalServerException()
        
        assert exc.status_code == 500
        assert exc.message == "Internal server error"
        assert exc.error_code == "INTERNAL_SERVER_ERROR"
    
    def test_bad_request_exception(self, mock_is_prod, mock_is_dev):
        """Test BadRequestException."""
        from src.exceptions import BadRequestException
        
        exc = BadRequestException(message="Invalid input")
        
        assert exc.status_code == 400
        assert exc.message == "Invalid input"
        assert exc.error_code == "BAD_REQUEST"
    
    def test_unprocessable_entity_exception(self, mock_is_prod, mock_is_dev):
        """Test UnprocessableEntityException."""
        from src.exceptions import UnprocessableEntityException
        
        exc = UnprocessableEntityException(message="Cannot process request")
        
        assert exc.status_code == 422
        assert exc.message == "Cannot process request"
        assert exc.error_code == "UNPROCESSABLE_ENTITY"
    
    def test_service_unavailable_exception(self, mock_is_prod, mock_is_dev):
        """Test ServiceUnavailableException."""
        from src.exceptions import ServiceUnavailableException
        
        exc = ServiceUnavailableException(retry_after=30)
        
        assert exc.status_code == 503
        assert exc.message == "Service temporarily unavailable"
        assert exc.error_code == "SERVICE_UNAVAILABLE"
        assert exc.headers == {"Retry-After": "30"}
    
    def test_database_exception(self, mock_is_prod, mock_is_dev):
        """Test DatabaseException."""
        from src.exceptions import DatabaseException
        
        exc = DatabaseException(message="Connection failed")
        
        assert exc.status_code == 500
        assert exc.message == "Connection failed"
        assert exc.error_code == "DATABASE_ERROR"
    
    def test_external_service_exception(self, mock_is_prod, mock_is_dev):
        """Test ExternalServiceException."""
        from src.exceptions import ExternalServiceException
        
        exc = ExternalServiceException(
            message="Service timeout",
            service_name="PaymentService"
        )
        
        assert exc.status_code == 502
        assert exc.message == "PaymentService: Service timeout"
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"


class TestErrorConversionFunctions:
    """Test error conversion utility functions."""
    
    @patch('src.exceptions.is_development')
    @patch('src.exceptions.is_production')
    def test_convert_pydantic_error_to_details(self, mock_is_prod, mock_is_dev):
        """Test conversion of Pydantic validation errors."""
        from pydantic import BaseModel, ValidationError, Field
        from src.exceptions import convert_pydantic_error_to_details
        
        class TestModel(BaseModel):
            email: str = Field(..., min_length=1)
            age: int = Field(..., ge=0)
        
        try:
            TestModel(email="", age=-1)
        except ValidationError as e:
            details = convert_pydantic_error_to_details(e)
            
            assert len(details) == 2
            
            # Check email error
            email_error = next((d for d in details if d.field == "email"), None)
            assert email_error is not None
            assert "at least 1 character" in email_error.message.lower() or "ensure this value has at least 1 character" in email_error.message.lower()
            
            # Check age error
            age_error = next((d for d in details if d.field == "age"), None)
            assert age_error is not None
            assert "greater than or equal to 0" in age_error.message.lower()
    
    @patch('src.exceptions.is_development')
    @patch('src.exceptions.is_production')
    def test_convert_fastapi_validation_error_to_details(self, mock_is_prod, mock_is_dev):
        """Test conversion of FastAPI validation errors."""
        from fastapi.exceptions import RequestValidationError
        from src.exceptions import convert_fastapi_validation_error_to_details
        
        # Create a mock validation error
        error_data = [
            {
                "loc": ("body", "email"),
                "msg": "field required",
                "type": "value_error.missing"
            },
            {
                "loc": ("query", "limit"),
                "msg": "ensure this value is greater than 0",
                "type": "value_error.number.not_gt"
            }
        ]
        
        exc = RequestValidationError(error_data)
        details = convert_fastapi_validation_error_to_details(exc)
        
        assert len(details) == 2
        
        # Check email error
        email_error = next((d for d in details if d.field == "email"), None)
        assert email_error is not None
        assert email_error.message == "field required"
        assert email_error.code == "value_error.missing"
        
        # Check limit error
        limit_error = next((d for d in details if d.field == "limit"), None)
        assert limit_error is not None
        assert limit_error.message == "ensure this value is greater than 0"
        assert limit_error.code == "value_error.number.not_gt"