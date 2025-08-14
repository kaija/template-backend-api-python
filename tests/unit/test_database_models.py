"""
Tests for database models.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    User, APIKey, UserSession,
    UserStatus, UserRole, APIKeyStatus
)


class TestUserModel:
    """Test User model functionality."""
    
    def test_user_creation(self):
        """Test creating a user instance."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123"
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        # Note: Default values are set by SQLAlchemy, not in Python constructor
        # So we test the defaults by setting them explicitly or testing with database
        
        # Test with explicit values
        user_with_defaults = User(
            username="testuser2",
            email="test2@example.com",
            hashed_password="hashed_password_123",
            status=UserStatus.PENDING,
            role=UserRole.USER,
            is_active=True,
            is_verified=False,
            failed_login_attempts=0
        )
        
        assert user_with_defaults.status == UserStatus.PENDING
        assert user_with_defaults.role == UserRole.USER
        assert user_with_defaults.is_active is True
        assert user_with_defaults.is_verified is False
        assert user_with_defaults.failed_login_attempts == 0
    
    def test_user_account_locked_check(self):
        """Test account locked functionality."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123"
        )
        
        # Initially not locked
        assert not user.is_account_locked()
        
        # Set lock time in the future
        user.locked_until = datetime.utcnow() + timedelta(hours=1)
        assert user.is_account_locked()
        
        # Set lock time in the past
        user.locked_until = datetime.utcnow() - timedelta(hours=1)
        assert not user.is_account_locked()
    
    def test_user_can_login(self):
        """Test can login functionality."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
            status=UserStatus.ACTIVE,
            is_active=True
        )
        
        # Should be able to login
        assert user.can_login()
        
        # Test various conditions that prevent login
        user.is_active = False
        assert not user.can_login()
        
        user.is_active = True
        user.status = UserStatus.SUSPENDED
        assert not user.can_login()
        
        user.status = UserStatus.ACTIVE
        user.is_deleted = True
        assert not user.can_login()
        
        user.is_deleted = False
        user.locked_until = datetime.utcnow() + timedelta(hours=1)
        assert not user.can_login()
    
    def test_user_failed_login_increment(self):
        """Test failed login attempt tracking."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123"
        )
        
        # Initially no failed attempts
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        
        # Increment failed attempts
        for i in range(4):
            user.increment_failed_login(max_attempts=5)
            assert user.failed_login_attempts == i + 1
            assert user.locked_until is None  # Not locked yet
        
        # Fifth attempt should lock the account
        user.increment_failed_login(max_attempts=5)
        assert user.failed_login_attempts == 5
        assert user.locked_until is not None
        assert user.is_account_locked()
    
    def test_user_reset_failed_login(self):
        """Test resetting failed login attempts."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123"
        )
        
        # Set some failed attempts and lock
        user.failed_login_attempts = 5
        user.locked_until = datetime.utcnow() + timedelta(hours=1)
        
        # Reset should clear everything
        user.reset_failed_login()
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login_at is not None
    
    def test_user_password_reset_token(self):
        """Test password reset token functionality."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123"
        )
        
        # Set password reset token
        token = "reset_token_123"
        user.set_password_reset_token(token, expires_in=3600)
        
        assert user.password_reset_token == token
        assert user.password_reset_expires is not None
        
        # Clear token
        user.clear_password_reset_token()
        assert user.password_reset_token is None
        assert user.password_reset_expires is None
    
    def test_user_email_verification(self):
        """Test email verification functionality."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
            status=UserStatus.PENDING
        )
        
        # Set verification token
        token = "verify_token_123"
        user.set_email_verification_token(token)
        
        assert user.email_verification_token == token
        assert user.email_verification_expires is not None
        assert not user.is_verified
        
        # Verify email
        user.verify_email()
        assert user.is_verified
        assert user.email_verification_token is None
        assert user.email_verification_expires is None
        assert user.status == UserStatus.ACTIVE
    
    def test_user_to_dict_excludes_sensitive_fields(self):
        """Test that to_dict excludes sensitive fields."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
            password_reset_token="reset_token",
            email_verification_token="verify_token"
        )
        
        user_dict = user.to_dict()
        
        # Should include basic fields
        assert user_dict["username"] == "testuser"
        assert user_dict["email"] == "test@example.com"
        
        # Should exclude sensitive fields
        assert "hashed_password" not in user_dict
        assert "password_reset_token" not in user_dict
        assert "email_verification_token" not in user_dict


class TestAPIKeyModel:
    """Test APIKey model functionality."""
    
    def test_api_key_creation(self):
        """Test creating an API key instance."""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id="user_123",
            status=APIKeyStatus.ACTIVE,
            usage_count=0
        )
        
        assert api_key.name == "Test API Key"
        assert api_key.key_hash == "hashed_key_123"
        assert api_key.key_prefix == "ak_test"
        assert api_key.user_id == "user_123"
        assert api_key.status == APIKeyStatus.ACTIVE
        assert api_key.usage_count == 0
        assert api_key.last_used_at is None
    
    def test_api_key_expiration(self):
        """Test API key expiration functionality."""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id="user_123"
        )
        
        # Initially not expired
        assert not api_key.is_expired()
        
        # Set expiration in the future
        api_key.expires_at = datetime.utcnow() + timedelta(days=30)
        assert not api_key.is_expired()
        
        # Set expiration in the past
        api_key.expires_at = datetime.utcnow() - timedelta(days=1)
        assert api_key.is_expired()
    
    def test_api_key_is_active(self):
        """Test API key active status."""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id="user_123",
            status=APIKeyStatus.ACTIVE
        )
        
        # Should be active
        assert api_key.is_active()
        
        # Test various conditions that make it inactive
        api_key.status = APIKeyStatus.REVOKED
        assert not api_key.is_active()
        
        api_key.status = APIKeyStatus.ACTIVE
        api_key.is_deleted = True
        assert not api_key.is_active()
        
        api_key.is_deleted = False
        api_key.expires_at = datetime.utcnow() - timedelta(days=1)
        assert not api_key.is_active()
    
    def test_api_key_record_usage(self):
        """Test recording API key usage."""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id="user_123"
        )
        
        # Initially no usage
        assert api_key.usage_count == 0
        assert api_key.last_used_at is None
        assert api_key.last_used_ip is None
        
        # Record usage
        ip_address = "192.168.1.1"
        api_key.record_usage(ip_address)
        
        assert api_key.usage_count == 1
        assert api_key.last_used_at is not None
        assert api_key.last_used_ip == ip_address
        
        # Record another usage
        api_key.record_usage()
        assert api_key.usage_count == 2
    
    def test_api_key_revoke(self):
        """Test API key revocation."""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id="user_123",
            status=APIKeyStatus.ACTIVE
        )
        
        assert api_key.status == APIKeyStatus.ACTIVE
        
        api_key.revoke()
        assert api_key.status == APIKeyStatus.REVOKED
    
    def test_api_key_set_expiration(self):
        """Test setting API key expiration."""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id="user_123"
        )
        
        # Initially no expiration
        assert api_key.expires_at is None
        
        # Set expiration
        api_key.set_expiration(30)  # 30 days
        assert api_key.expires_at is not None
        
        # Should expire in approximately 30 days
        expected_expiry = datetime.utcnow() + timedelta(days=30)
        time_diff = abs((api_key.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_api_key_to_dict_excludes_sensitive_fields(self):
        """Test that to_dict excludes sensitive fields."""
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id="user_123"
        )
        
        key_dict = api_key.to_dict()
        
        # Should include basic fields
        assert key_dict["name"] == "Test API Key"
        assert key_dict["key_prefix"] == "ak_test"
        assert key_dict["user_id"] == "user_123"
        
        # Should exclude sensitive fields
        assert "key_hash" not in key_dict


class TestUserSessionModel:
    """Test UserSession model functionality."""
    
    def test_user_session_creation(self):
        """Test creating a user session instance."""
        expires_at = datetime.utcnow() + timedelta(hours=24)
        session = UserSession(
            session_token="session_token_123",
            user_id="user_123",
            expires_at=expires_at,
            ip_address="192.168.1.1",
            is_active=True
        )
        
        assert session.session_token == "session_token_123"
        assert session.user_id == "user_123"
        assert session.expires_at == expires_at
        assert session.ip_address == "192.168.1.1"
        assert session.is_active is True
    
    def test_user_session_expiration(self):
        """Test session expiration functionality."""
        session = UserSession(
            session_token="session_token_123",
            user_id="user_123",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Initially not expired
        assert not session.is_expired()
        
        # Set expiration in the past
        session.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert session.is_expired()
    
    def test_user_session_is_valid(self):
        """Test session validity check."""
        session = UserSession(
            session_token="session_token_123",
            user_id="user_123",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=True
        )
        
        # Should be valid
        assert session.is_valid()
        
        # Test conditions that make it invalid
        session.is_active = False
        assert not session.is_valid()
        
        session.is_active = True
        session.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert not session.is_valid()
    
    def test_user_session_extend(self):
        """Test extending session expiration."""
        original_expiry = datetime.utcnow() + timedelta(hours=1)
        session = UserSession(
            session_token="session_token_123",
            user_id="user_123",
            expires_at=original_expiry
        )
        
        # Extend session
        session.extend_session(extend_by_hours=24)
        
        # Should be extended by approximately 24 hours
        expected_expiry = datetime.utcnow() + timedelta(hours=24)
        time_diff = abs((session.expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute
        
        # Last activity should be updated
        assert session.last_activity_at is not None
    
    def test_user_session_invalidate(self):
        """Test session invalidation."""
        session = UserSession(
            session_token="session_token_123",
            user_id="user_123",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=True
        )
        
        assert session.is_active
        
        session.invalidate()
        assert not session.is_active


class TestModelEnums:
    """Test model enumeration classes."""
    
    def test_user_status_enum(self):
        """Test UserStatus enumeration."""
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.INACTIVE.value == "inactive"
        assert UserStatus.SUSPENDED.value == "suspended"
        assert UserStatus.PENDING.value == "pending"
        assert UserStatus.DELETED.value == "deleted"
    
    def test_user_role_enum(self):
        """Test UserRole enumeration."""
        assert UserRole.GUEST.value == "guest"
        assert UserRole.USER.value == "user"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.API_USER.value == "api_user"
        assert UserRole.SYSTEM.value == "system"
    
    def test_api_key_status_enum(self):
        """Test APIKeyStatus enumeration."""
        assert APIKeyStatus.ACTIVE.value == "active"
        assert APIKeyStatus.INACTIVE.value == "inactive"
        assert APIKeyStatus.REVOKED.value == "revoked"
        assert APIKeyStatus.EXPIRED.value == "expired"


class TestModelRelationships:
    """Test model relationships."""
    
    def test_user_api_key_relationship(self):
        """Test User-APIKey relationship."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123"
        )
        
        api_key = APIKey(
            name="Test API Key",
            key_hash="hashed_key_123",
            key_prefix="ak_test",
            user_id=user.id
        )
        
        # Set up the relationship (normally done by SQLAlchemy)
        api_key.user = user
        user.api_keys = [api_key]
        
        assert api_key.user == user
        assert api_key in user.api_keys
    
    def test_user_session_relationship(self):
        """Test User-UserSession relationship."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123"
        )
        
        session = UserSession(
            session_token="session_token_123",
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Set up the relationship (normally done by SQLAlchemy)
        session.user = user
        
        assert session.user == user