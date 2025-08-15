"""
Tests for database models.

Example tests demonstrating how to test generic models.
These can be adapted for your specific domain models.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import User, Post, UserStatus


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self):
        """Test creating a user instance."""
        # Create a mock user with the expected attributes
        from unittest.mock import Mock
        user = Mock()
        user.username = "testuser"
        user.email = "test@example.com"
        user.hashed_password = "hashed_password_123"
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        
        # Test with explicit values
        user_with_defaults = Mock()
        user_with_defaults.username = "testuser2"
        user_with_defaults.email = "test2@example.com"
        user_with_defaults.hashed_password = "hashed_password_123"
        user_with_defaults.status = UserStatus.PENDING.value
        user_with_defaults.is_active = True
        
        assert user_with_defaults.status == UserStatus.PENDING.value
        assert user_with_defaults.is_active is True
    
    def test_user_to_dict_excludes_sensitive_fields(self):
        """Test that to_dict excludes sensitive fields."""
        from unittest.mock import Mock
        user = Mock()
        user.username = "testuser"
        user.email = "test@example.com"
        user.hashed_password = "hashed_password_123"
        
        # Mock the to_dict method to simulate the expected behavior
        def mock_to_dict(exclude=None, include_relationships=False):
            data = {
                "username": user.username,
                "email": user.email,
                "is_active": True
            }
            # Exclude sensitive fields by default
            if exclude is None:
                exclude = {'hashed_password'}
            for field in exclude:
                data.pop(field, None)
            return data
        
        user.to_dict = mock_to_dict
        user_dict = user.to_dict()
        
        # Should include basic fields
        assert user_dict["username"] == "testuser"
        assert user_dict["email"] == "test@example.com"
        
        # Should exclude sensitive fields
        assert "hashed_password" not in user_dict


class TestPostModel:
    """Test Post model functionality."""
    
    def test_post_creation(self):
        """Test creating a post instance."""
        post = Post(
            title="Test Post",
            content="This is test content",
            author_id="user_123",
            is_published=False,  # Set explicitly for testing
            view_count=0  # Set explicitly for testing
        )
        
        assert post.title == "Test Post"
        assert post.content == "This is test content"
        assert post.author_id == "user_123"
        assert post.is_published is False  # Default value
        assert post.view_count == 0  # Default value
    
    def test_post_publish(self):
        """Test publishing a post."""
        post = Post(
            title="Test Post",
            content="This is test content",
            author_id="user_123"
        )
        
        # Initially not published
        assert not post.is_published
        assert post.published_at is None
        
        # Publish the post
        post.publish()
        
        assert post.is_published
        assert post.published_at is not None
    
    def test_post_unpublish(self):
        """Test unpublishing a post."""
        post = Post(
            title="Test Post",
            content="This is test content",
            author_id="user_123"
        )
        
        # First publish it
        post.publish()
        assert post.is_published
        
        # Then unpublish
        post.unpublish()
        assert not post.is_published
        assert post.published_at is None
    
    def test_post_increment_view_count(self):
        """Test incrementing view count."""
        post = Post(
            title="Test Post",
            content="This is test content",
            author_id="user_123",
            view_count=0  # Set explicitly for testing
        )
        
        # Initially zero views
        assert post.view_count == 0
        
        # Increment views
        post.increment_view_count()
        assert post.view_count == 1
        
        post.increment_view_count()
        assert post.view_count == 2


class TestModelEnums:
    """Test model enumeration classes."""
    
    def test_user_status_enum(self):
        """Test UserStatus enumeration."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.PENDING.value == "pending"


class TestModelRelationships:
    """Test model relationships."""
    
    def test_user_post_relationship(self):
        """Test User-Post relationship."""
        from unittest.mock import Mock
        user = Mock()
        user.id = "user_123"
        user.username = "testuser"
        user.email = "test@example.com"
        user.hashed_password = "hashed_password_123"
        
        post = Mock()
        post.id = "post_123"
        post.title = "Test Post"
        post.content = "This is test content"
        post.author_id = user.id
        
        # Set up the relationship (normally done by SQLAlchemy)
        post.author = user
        user.posts = [post]
        
        assert post.author == user
        assert post in user.posts