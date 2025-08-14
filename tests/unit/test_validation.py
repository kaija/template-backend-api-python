"""
Tests for Pydantic validation system.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

# Set test environment before importing
import os
os.environ["API_ENV"] = "test"
os.environ["SKIP_CONFIG_INIT"] = "1"
os.environ["SKIP_CONFIG_VALIDATION"] = "1"

from src.schemas.base import (
    BaseSchema,
    PaginationParams,
    PaginationMeta,
    SuccessResponse,
    ErrorResponse,
    ErrorDetail
)
from src.schemas.users import (
    UserCreate,
    UserUpdate,
    User,
    UserFilters,
    UserPasswordChange
)
from src.schemas.common import (
    SortParams,
    BulkOperation,
    SearchParams,
    DateRangeParams
)
from src.exceptions import (
    ValidationException,
    convert_pydantic_error_to_details
)


class TestBaseSchemas:
    """Test base schema functionality."""
    
    def test_pagination_params_valid(self):
        """Test valid pagination parameters."""
        params = PaginationParams(skip=10, limit=20)
        assert params.skip == 10
        assert params.limit == 20
    
    def test_pagination_params_defaults(self):
        """Test pagination parameter defaults."""
        params = PaginationParams()
        assert params.skip == 0
        assert params.limit == 10
    
    def test_pagination_params_invalid_skip(self):
        """Test invalid skip parameter."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(skip=-1)
        
        assert "greater than or equal to 0" in str(exc_info.value)
    
    def test_pagination_params_invalid_limit(self):
        """Test invalid limit parameter."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(limit=0)
        
        assert "greater than or equal to 1" in str(exc_info.value)
    
    def test_pagination_params_limit_too_high(self):
        """Test limit parameter too high."""
        with pytest.raises(ValidationError) as exc_info:
            PaginationParams(limit=101)
        
        assert "less than or equal to 100" in str(exc_info.value)
    
    def test_success_response(self):
        """Test success response schema."""
        response = SuccessResponse(
            message="Operation successful",
            data={"result": "test"}
        )
        
        assert response.success is True
        assert response.message == "Operation successful"
        assert response.data == {"result": "test"}
        assert isinstance(response.timestamp, datetime)
    
    def test_error_response(self):
        """Test error response schema."""
        details = [
            ErrorDetail(field="username", message="Required field", code="REQUIRED")
        ]
        
        response = ErrorResponse(
            message="Validation failed",
            error_code="VALIDATION_ERROR",
            details=details
        )
        
        assert response.success is False
        assert response.message == "Validation failed"
        assert response.error_code == "VALIDATION_ERROR"
        assert len(response.details) == 1
        assert response.details[0].field == "username"


class TestUserSchemas:
    """Test user schema validation."""
    
    def test_user_create_valid(self):
        """Test valid user creation."""
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="SecurePassword123!",
            confirm_password="SecurePassword123!"
        )
        
        assert user_data.username == "testuser"
        assert user_data.email == "test@example.com"
        assert user_data.full_name == "Test User"
        assert user_data.password == "SecurePassword123!"
    
    def test_user_create_invalid_username_reserved(self):
        """Test user creation with reserved username."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="admin",
                email="test@example.com",
                password="SecurePassword123!",
                confirm_password="SecurePassword123!"
            )
        
        assert "reserved" in str(exc_info.value).lower()
    
    def test_user_create_invalid_username_consecutive_chars(self):
        """Test user creation with consecutive special characters."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="test--user",
                email="test@example.com",
                password="SecurePassword123!",
                confirm_password="SecurePassword123!"
            )
        
        assert "consecutive" in str(exc_info.value).lower()
    
    def test_user_create_invalid_username_start_end(self):
        """Test user creation with username starting/ending with special chars."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="-testuser",
                email="test@example.com",
                password="SecurePassword123!",
                confirm_password="SecurePassword123!"
            )
        
        assert "start or end" in str(exc_info.value).lower()
    
    def test_user_create_invalid_password_weak(self):
        """Test user creation with weak password."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="password123",
                confirm_password="password123"
            )
        
        assert "uppercase" in str(exc_info.value).lower()
    
    def test_user_create_invalid_password_common(self):
        """Test user creation with common password."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="Password123!",  # Meets all requirements but is common
                confirm_password="Password123!"
            )
        
        assert "common" in str(exc_info.value).lower()
    
    def test_user_create_password_mismatch(self):
        """Test user creation with password mismatch."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="SecurePassword123!",
                confirm_password="DifferentPassword123!"
            )
        
        assert "do not match" in str(exc_info.value).lower()
    
    def test_user_create_invalid_full_name(self):
        """Test user creation with invalid full name."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                full_name="Test123User",
                password="SecurePassword123!",
                confirm_password="SecurePassword123!"
            )
        
        assert "letters, spaces" in str(exc_info.value).lower()
    
    def test_user_update_partial(self):
        """Test partial user update."""
        update_data = UserUpdate(
            full_name="Updated Name",
            is_active=False
        )
        
        assert update_data.username is None
        assert update_data.email is None
        assert update_data.full_name == "Updated Name"
        assert update_data.is_active is False
    
    def test_user_filters_valid(self):
        """Test valid user filters."""
        filters = UserFilters(
            is_active=True,
            search="john",
            created_after=datetime(2024, 1, 1),
            created_before=datetime(2024, 12, 31)
        )
        
        assert filters.is_active is True
        assert filters.search == "john"
        assert filters.created_after.year == 2024
        assert filters.created_before.year == 2024
    
    def test_user_filters_invalid_date_range(self):
        """Test user filters with invalid date range."""
        with pytest.raises(ValidationError) as exc_info:
            UserFilters(
                created_after=datetime(2024, 12, 31),
                created_before=datetime(2024, 1, 1)
            )
        
        assert "before" in str(exc_info.value).lower()
    
    def test_user_filters_invalid_search(self):
        """Test user filters with invalid search term."""
        with pytest.raises(ValidationError) as exc_info:
            UserFilters(search="<script>alert('xss')</script>")
        
        assert "invalid characters" in str(exc_info.value).lower()
    
    def test_user_password_change_valid(self):
        """Test valid password change."""
        password_change = UserPasswordChange(
            current_password="OldPassword123!",
            new_password="NewSecurePassword123!",
            confirm_new_password="NewSecurePassword123!"
        )
        
        assert password_change.current_password == "OldPassword123!"
        assert password_change.new_password == "NewSecurePassword123!"
    
    def test_user_password_change_same_password(self):
        """Test password change with same password."""
        with pytest.raises(ValidationError) as exc_info:
            UserPasswordChange(
                current_password="SamePassword123!",
                new_password="SamePassword123!",
                confirm_new_password="SamePassword123!"
            )
        
        assert "different" in str(exc_info.value).lower()
    
    def test_user_password_change_mismatch(self):
        """Test password change with confirmation mismatch."""
        with pytest.raises(ValidationError) as exc_info:
            UserPasswordChange(
                current_password="OldPassword123!",
                new_password="NewPassword123!",
                confirm_new_password="DifferentPassword123!"
            )
        
        assert "do not match" in str(exc_info.value).lower()


class TestCommonSchemas:
    """Test common schema validation."""
    
    def test_sort_params_valid(self):
        """Test valid sort parameters."""
        params = SortParams(sort_by="created_at", sort_order="desc")
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"
    
    def test_sort_params_invalid_field(self):
        """Test sort parameters with invalid field."""
        with pytest.raises(ValidationError) as exc_info:
            SortParams(sort_by="invalid-field!")
        
        assert "letters, numbers" in str(exc_info.value).lower()
    
    def test_bulk_operation_valid(self):
        """Test valid bulk operation."""
        operation = BulkOperation(ids=["id1", "id2", "id3"])
        assert len(operation.ids) == 3
        assert "id1" in operation.ids
    
    def test_bulk_operation_empty_ids(self):
        """Test bulk operation with empty IDs."""
        with pytest.raises(ValidationError) as exc_info:
            BulkOperation(ids=[])
        
        error_msg = str(exc_info.value).lower()
        assert "at least" in error_msg and ("one" in error_msg or "1" in error_msg)
    
    def test_bulk_operation_too_many_ids(self):
        """Test bulk operation with too many IDs."""
        ids = [f"id{i}" for i in range(101)]
        
        with pytest.raises(ValidationError) as exc_info:
            BulkOperation(ids=ids)
        
        assert "100" in str(exc_info.value)
    
    def test_bulk_operation_duplicate_ids(self):
        """Test bulk operation with duplicate IDs."""
        with pytest.raises(ValidationError) as exc_info:
            BulkOperation(ids=["id1", "id2", "id1"])
        
        assert "duplicate" in str(exc_info.value).lower()
    
    def test_search_params_valid(self):
        """Test valid search parameters."""
        params = SearchParams(
            query="test search",
            fields=["name", "description"],
            exact_match=True
        )
        
        assert params.query == "test search"
        assert params.fields == ["name", "description"]
        assert params.exact_match is True
    
    def test_search_params_invalid_query(self):
        """Test search parameters with invalid query."""
        with pytest.raises(ValidationError) as exc_info:
            SearchParams(query="<script>alert('xss')</script>")
        
        assert "invalid characters" in str(exc_info.value).lower()
    
    def test_search_params_invalid_fields(self):
        """Test search parameters with invalid fields."""
        with pytest.raises(ValidationError) as exc_info:
            SearchParams(query="test", fields=["valid_field", "invalid-field!"])
        
        assert "letters, numbers" in str(exc_info.value).lower()
    
    def test_date_range_params_valid(self):
        """Test valid date range parameters."""
        params = DateRangeParams(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31)
        )
        
        assert params.start_date.year == 2024
        assert params.end_date.year == 2024
    
    def test_date_range_params_invalid_range(self):
        """Test date range parameters with invalid range."""
        with pytest.raises(ValidationError) as exc_info:
            DateRangeParams(
                start_date=datetime(2024, 12, 31),
                end_date=datetime(2024, 1, 1)
            )
        
        assert "before" in str(exc_info.value).lower()


class TestExceptionHandling:
    """Test exception handling functionality."""
    
    def test_validation_exception(self):
        """Test validation exception creation."""
        details = [
            ErrorDetail(field="username", message="Required field", code="REQUIRED")
        ]
        
        exc = ValidationException(
            message="Validation failed",
            details=details
        )
        
        assert exc.status_code == 400
        assert exc.message == "Validation failed"
        assert exc.error_code == "VALIDATION_ERROR"
        assert len(exc.details) == 1
    
    def test_convert_pydantic_error_to_details(self):
        """Test conversion of Pydantic errors to ErrorDetail list."""
        try:
            UserCreate(
                username="",  # Invalid
                email="invalid-email",  # Invalid
                password="weak"  # Invalid
            )
        except ValidationError as e:
            details = convert_pydantic_error_to_details(e)
            
            assert len(details) > 0
            assert all(isinstance(detail, ErrorDetail) for detail in details)
            
            # Check that we have details for the expected fields
            field_names = [detail.field for detail in details]
            assert any("username" in field for field in field_names)
            assert any("email" in field for field in field_names)
            assert any("password" in field for field in field_names)


class TestSchemaInheritance:
    """Test schema inheritance patterns."""
    
    def test_user_inherits_mixins(self):
        """Test that User schema properly inherits from mixins."""
        user = User(
            id="user_123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Check IdentifierMixin fields
        assert hasattr(user, 'id')
        assert user.id == "user_123"
        
        # Check TimestampMixin fields
        assert hasattr(user, 'created_at')
        assert hasattr(user, 'updated_at')
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
        
        # Check UserBase fields
        assert hasattr(user, 'username')
        assert hasattr(user, 'email')
        assert hasattr(user, 'full_name')
    
    def test_base_schema_configuration(self):
        """Test base schema configuration is applied."""
        # Test that extra fields are forbidden by default
        with pytest.raises(ValidationError) as exc_info:
            class TestSchema(BaseSchema):
                name: str
            
            TestSchema(name="test", extra_field="not allowed")
        
        assert "extra" in str(exc_info.value).lower()
    
    def test_string_field_helpers(self):
        """Test string field helper functions."""
        from src.schemas.base import create_string_field, create_optional_string_field
        
        # Test required string field
        required_field = create_string_field(
            description="Test field",
            min_length=3,
            max_length=10,
            example="test"
        )
        
        assert required_field.description == "Test field"
        assert required_field.json_schema_extra == {"example": "test"}
        
        # Test optional string field
        optional_field = create_optional_string_field(
            description="Optional field",
            example="optional"
        )
        
        assert optional_field.default is None
        assert optional_field.description == "Optional field"