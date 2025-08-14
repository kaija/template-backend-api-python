"""
Tests for controller architecture.
"""

import pytest
from datetime import datetime

# Set test environment before importing
import os
os.environ["API_ENV"] = "test"
os.environ["SKIP_CONFIG_INIT"] = "1"
os.environ["SKIP_CONFIG_VALIDATION"] = "1"

from src.controllers.base import BaseController, HealthController
from src.controllers.users import UserController
from src.schemas.users import UserCreate, UserUpdate


class TestBaseController:
    """Test base controller functionality."""
    
    def test_base_controller_initialization(self):
        """Test base controller initialization."""
        controller = BaseController()
        assert controller.logger is not None
        assert controller.logger.name == "BaseController"
    
    def test_create_response(self):
        """Test response creation."""
        controller = BaseController()
        
        response = controller._create_response(
            data={"test": "data"},
            message="Test message",
            status_code=200
        )
        
        assert response["success"] is True
        assert response["message"] == "Test message"
        assert response["data"] == {"test": "data"}
        assert "timestamp" in response
    
    def test_create_error_response(self):
        """Test error response creation."""
        controller = BaseController()
        
        response = controller._create_response(
            message="Error occurred",
            status_code=400
        )
        
        assert response["success"] is False
        assert response["message"] == "Error occurred"
        assert "timestamp" in response


class TestHealthController:
    """Test health controller functionality."""
    
    @pytest.fixture
    def health_controller(self):
        """Create health controller instance."""
        return HealthController()
    
    @pytest.mark.asyncio
    async def test_health_check(self, health_controller):
        """Test health check endpoint."""
        result = await health_controller.health_check()
        
        assert result["success"] is True
        assert result["message"] == "Application is healthy"
        assert "data" in result
        assert result["data"]["status"] == "healthy"
        assert "version" in result["data"]
        assert "environment" in result["data"]
    
    @pytest.mark.asyncio
    async def test_readiness_check(self, health_controller):
        """Test readiness check endpoint."""
        result = await health_controller.readiness_check()
        
        assert result["success"] is True
        assert "data" in result
        assert result["data"]["status"] in ["ready", "not_ready"]
        assert "checks" in result["data"]
        assert "database" in result["data"]["checks"]
        assert "redis" in result["data"]["checks"]
        assert "external_services" in result["data"]["checks"]


class TestUserController:
    """Test user controller functionality."""
    
    @pytest.fixture
    def user_controller(self):
        """Create user controller instance."""
        return UserController()
    
    @pytest.fixture
    def sample_user_data(self):
        """Create sample user data."""
        return UserCreate(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            password="testpassword123"
        )
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_controller, sample_user_data):
        """Test user creation."""
        user = await user_controller.create(sample_user_data)
        
        assert user.username == sample_user_data.username
        assert user.email == sample_user_data.email
        assert user.full_name == sample_user_data.full_name
        assert user.is_active is True
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None
    
    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, user_controller, sample_user_data):
        """Test creating duplicate user raises error."""
        # Create first user
        await user_controller.create(sample_user_data)
        
        # Try to create duplicate
        with pytest.raises(Exception):  # Should raise ValueError wrapped in HTTPException
            await user_controller.create(sample_user_data)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id(self, user_controller, sample_user_data):
        """Test getting user by ID."""
        # Create user
        created_user = await user_controller.create(sample_user_data)
        
        # Get user by ID
        retrieved_user = await user_controller.get_by_id(created_user.id)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.username == created_user.username
        assert retrieved_user.email == created_user.email
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, user_controller):
        """Test getting nonexistent user returns None."""
        user = await user_controller.get_by_id("nonexistent_id")
        assert user is None
    
    @pytest.mark.asyncio
    async def test_get_all_users(self, user_controller, sample_user_data):
        """Test getting all users with pagination."""
        # Create multiple users
        for i in range(5):
            user_data = UserCreate(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                full_name=f"Test User {i}",
                password="testpassword123"
            )
            await user_controller.create(user_data)
        
        # Get all users
        result = await user_controller.get_all(skip=0, limit=10)
        
        assert "items" in result
        assert "pagination" in result
        assert len(result["items"]) == 5
        assert result["pagination"]["total"] == 5
        assert result["pagination"]["skip"] == 0
        assert result["pagination"]["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_get_all_users_with_pagination(self, user_controller):
        """Test pagination functionality."""
        # Create multiple users
        for i in range(15):
            user_data = UserCreate(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                full_name=f"Test User {i}",
                password="testpassword123"
            )
            await user_controller.create(user_data)
        
        # Get first page
        result = await user_controller.get_all(skip=0, limit=10)
        assert len(result["items"]) == 10
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False
        
        # Get second page
        result = await user_controller.get_all(skip=10, limit=10)
        assert len(result["items"]) == 5
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_prev"] is True
    
    @pytest.mark.asyncio
    async def test_update_user(self, user_controller, sample_user_data):
        """Test user update."""
        # Create user
        created_user = await user_controller.create(sample_user_data)
        
        # Update user
        update_data = UserUpdate(
            full_name="Updated Test User",
            is_active=False
        )
        updated_user = await user_controller.update(created_user.id, update_data)
        
        assert updated_user is not None
        assert updated_user.full_name == "Updated Test User"
        assert updated_user.is_active is False
        assert updated_user.username == created_user.username  # Unchanged
        assert updated_user.email == created_user.email  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_user(self, user_controller):
        """Test updating nonexistent user returns None."""
        update_data = UserUpdate(full_name="Updated Name")
        result = await user_controller.update("nonexistent_id", update_data)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_user(self, user_controller, sample_user_data):
        """Test user deletion."""
        # Create user
        created_user = await user_controller.create(sample_user_data)
        
        # Delete user
        deleted = await user_controller.delete(created_user.id)
        assert deleted is True
        
        # Verify user is deleted
        retrieved_user = await user_controller.get_by_id(created_user.id)
        assert retrieved_user is None
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, user_controller):
        """Test deleting nonexistent user returns False."""
        deleted = await user_controller.delete("nonexistent_id")
        assert deleted is False
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_controller, sample_user_data):
        """Test getting user by email."""
        # Create user
        created_user = await user_controller.create(sample_user_data)
        
        # Get user by email
        retrieved_user = await user_controller.get_by_email(sample_user_data.email)
        
        assert retrieved_user is not None
        assert retrieved_user.id == created_user.id
        assert retrieved_user.email == sample_user_data.email
    
    @pytest.mark.asyncio
    async def test_activate_deactivate_user(self, user_controller, sample_user_data):
        """Test user activation and deactivation."""
        # Create user
        created_user = await user_controller.create(sample_user_data)
        assert created_user.is_active is True
        
        # Deactivate user
        deactivated_user = await user_controller.deactivate_user(created_user.id)
        assert deactivated_user is not None
        assert deactivated_user.is_active is False
        
        # Activate user
        activated_user = await user_controller.activate_user(created_user.id)
        assert activated_user is not None
        assert activated_user.is_active is True
    
    @pytest.mark.asyncio
    async def test_search_users(self, user_controller):
        """Test user search functionality."""
        # Create users with different names
        users_data = [
            UserCreate(username="john_doe", email="john@example.com", full_name="John Doe", password="pass123"),
            UserCreate(username="jane_smith", email="jane@example.com", full_name="Jane Smith", password="pass123"),
            UserCreate(username="bob_johnson", email="bob@example.com", full_name="Bob Johnson", password="pass123"),
        ]
        
        for user_data in users_data:
            await user_controller.create(user_data)
        
        # Search for "john"
        result = await user_controller.get_all(filters={"search": "john"})
        assert len(result["items"]) == 2  # john_doe and bob_johnson
        
        # Search for "jane"
        result = await user_controller.get_all(filters={"search": "jane"})
        assert len(result["items"]) == 1
        assert result["items"][0].username == "jane_smith"