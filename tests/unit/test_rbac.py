"""
Tests for Role-Based Access Control (RBAC) system.

This module tests the RBAC system including roles, permissions,
and access control decorators.
"""

import os
import pytest
from unittest.mock import Mock
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient

# Skip configuration validation and initialization for tests
os.environ["SKIP_CONFIG_VALIDATION"] = "1"
os.environ["SKIP_CONFIG_INIT"] = "1"

from src.auth.rbac import (
    Permission,
    Role,
    RBACManager,
    rbac_manager,
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    get_current_user,
    get_user_roles,
)


class TestPermissionEnum:
    """Test Permission enumeration."""
    
    def test_permission_values(self):
        """Test that permissions have correct string values."""
        assert Permission.USER_READ == "user:read"
        assert Permission.USER_WRITE == "user:write"
        assert Permission.CONTENT_READ == "content:read"
        assert Permission.SYSTEM_ADMIN == "system:admin"
        assert Permission.ALL == "*"
    
    def test_permission_membership(self):
        """Test permission enum membership."""
        assert "user:read" in Permission
        assert "invalid:permission" not in Permission


class TestRoleEnum:
    """Test Role enumeration."""
    
    def test_role_values(self):
        """Test that roles have correct string values."""
        assert Role.GUEST == "guest"
        assert Role.USER == "user"
        assert Role.ADMIN == "admin"
        assert Role.SUPER_ADMIN == "super_admin"
    
    def test_role_membership(self):
        """Test role enum membership."""
        assert "user" in Role
        assert "invalid_role" not in Role


class TestRBACManager:
    """Test RBAC manager functionality."""
    
    def test_get_role_permissions(self):
        """Test getting permissions for a role."""
        manager = RBACManager()
        
        # Test guest permissions
        guest_perms = manager.get_role_permissions(Role.GUEST)
        assert Permission.CONTENT_READ in guest_perms
        assert Permission.USER_WRITE not in guest_perms
        
        # Test user permissions (should inherit from guest)
        user_perms = manager.get_role_permissions(Role.USER)
        assert Permission.CONTENT_READ in user_perms  # Inherited
        assert Permission.USER_READ in user_perms     # Own permission
        
        # Test admin permissions
        admin_perms = manager.get_role_permissions(Role.ADMIN)
        assert Permission.USER_READ in admin_perms
        assert Permission.USER_WRITE in admin_perms
        assert Permission.SYSTEM_READ in admin_perms
        
        # Test super admin permissions
        super_admin_perms = manager.get_role_permissions(Role.SUPER_ADMIN)
        assert Permission.ALL in super_admin_perms
    
    def test_get_role_permissions_string(self):
        """Test getting permissions for a role using string."""
        manager = RBACManager()
        
        user_perms = manager.get_role_permissions("user")
        assert Permission.USER_READ in user_perms
        
        # Test unknown role
        unknown_perms = manager.get_role_permissions("unknown_role")
        assert len(unknown_perms) == 0
    
    def test_has_permission(self):
        """Test permission checking."""
        manager = RBACManager()
        
        # Test user with user role
        user_roles = [Role.USER]
        assert manager.has_permission(user_roles, Permission.USER_READ) is True
        assert manager.has_permission(user_roles, Permission.USER_DELETE) is False
        
        # Test admin with admin role
        admin_roles = [Role.ADMIN]
        assert manager.has_permission(admin_roles, Permission.USER_READ) is True
        assert manager.has_permission(admin_roles, Permission.USER_WRITE) is True
        assert manager.has_permission(admin_roles, Permission.SYSTEM_READ) is True
        
        # Test super admin with wildcard permission
        super_admin_roles = [Role.SUPER_ADMIN]
        assert manager.has_permission(super_admin_roles, Permission.USER_READ) is True
        assert manager.has_permission(super_admin_roles, Permission.SYSTEM_ADMIN) is True
        # Super admin should have wildcard permission for any permission
        assert manager.has_permission(super_admin_roles, Permission.ALL) is True
    
    def test_has_permission_multiple_roles(self):
        """Test permission checking with multiple roles."""
        manager = RBACManager()
        
        # User with both user and moderator roles
        user_roles = [Role.USER, Role.MODERATOR]
        assert manager.has_permission(user_roles, Permission.USER_READ) is True
        assert manager.has_permission(user_roles, Permission.CONTENT_DELETE) is True
    
    def test_has_any_permission(self):
        """Test checking for any of multiple permissions."""
        manager = RBACManager()
        
        user_roles = [Role.USER]
        permissions = [Permission.USER_READ, Permission.SYSTEM_ADMIN]
        
        # User has USER_READ but not SYSTEM_ADMIN
        assert manager.has_any_permission(user_roles, permissions) is True
        
        # User doesn't have any of these permissions
        admin_permissions = [Permission.SYSTEM_ADMIN, Permission.USER_DELETE]
        assert manager.has_any_permission(user_roles, admin_permissions) is False
    
    def test_has_all_permissions(self):
        """Test checking for all of multiple permissions."""
        manager = RBACManager()
        
        admin_roles = [Role.ADMIN]
        user_permissions = [Permission.USER_READ, Permission.USER_WRITE]
        
        # Admin has both permissions
        assert manager.has_all_permissions(admin_roles, user_permissions) is True
        
        # Admin has all system permissions now
        system_permissions = [Permission.SYSTEM_READ, Permission.SYSTEM_ADMIN]
        assert manager.has_all_permissions(admin_roles, system_permissions) is True
        
        # Admin doesn't have audit write permission
        audit_permissions = [Permission.AUDIT_READ, Permission.AUDIT_WRITE]
        assert manager.has_all_permissions(admin_roles, audit_permissions) is False
    
    def test_get_user_permissions(self):
        """Test getting all permissions for a user."""
        manager = RBACManager()
        
        # User with multiple roles
        user_roles = [Role.USER, Role.MODERATOR]
        all_permissions = manager.get_user_permissions(user_roles)
        
        # Should have permissions from both roles
        assert Permission.USER_READ in all_permissions
        assert Permission.CONTENT_DELETE in all_permissions
        assert Permission.CONTENT_READ in all_permissions
    
    def test_permission_inheritance(self):
        """Test that role inheritance works correctly."""
        manager = RBACManager()
        
        # User should inherit guest permissions
        user_perms = manager.get_role_permissions(Role.USER)
        guest_perms = manager.get_role_permissions(Role.GUEST)
        
        for perm in guest_perms:
            assert perm in user_perms
        
        # Admin should inherit user permissions
        admin_perms = manager.get_role_permissions(Role.ADMIN)
        
        for perm in user_perms:
            if perm != Permission.ALL:  # Skip wildcard
                assert perm in admin_perms


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_get_current_user(self):
        """Test getting current user from request."""
        # Mock request with user
        request = Mock()
        request.state.user = {"user_id": "123", "username": "testuser"}
        
        user = get_current_user(request)
        assert user is not None
        assert user["user_id"] == "123"
        
        # Mock request without user
        request.state.user = None
        user = get_current_user(request)
        assert user is None
    
    def test_get_user_roles(self):
        """Test extracting user roles."""
        # User with roles
        user = {"roles": ["user", "moderator"]}
        roles = get_user_roles(user)
        assert roles == ["user", "moderator"]
        
        # User without roles (should default to user)
        user = {"user_id": "123"}
        roles = get_user_roles(user)
        assert roles == ["user"]
        
        # No user (should default to guest)
        roles = get_user_roles(None)
        assert roles == ["guest"]


class TestPermissionDecorators:
    """Test permission decorators."""
    
    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test successful permission check."""
        @require_permission(Permission.USER_READ, raise_exception=False)
        async def test_endpoint(request: Request):
            return {"message": "success"}
        
        # Mock request with authenticated user
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "123",
            "username": "testuser",
            "roles": ["user"]
        }
        request.url.path = "/test"
        request.method = "GET"
        request.state.correlation_id = "test-123"
        
        result = await test_endpoint(request)
        assert result == {"message": "success"}
    
    @pytest.mark.asyncio
    async def test_require_permission_failure(self):
        """Test failed permission check."""
        @require_permission(Permission.SYSTEM_ADMIN, raise_exception=False)
        async def test_endpoint(request: Request):
            return {"message": "success"}
        
        # Mock request with user lacking permission
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "123",
            "username": "testuser",
            "roles": ["user"]
        }
        request.url.path = "/test"
        request.method = "GET"
        request.state.correlation_id = "test-123"
        
        result = await test_endpoint(request)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_require_permission_exception(self):
        """Test permission check with exception."""
        @require_permission(Permission.SYSTEM_ADMIN, raise_exception=True)
        async def test_endpoint(request: Request):
            return {"message": "success"}
        
        # Mock request with user lacking permission
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "123",
            "username": "testuser",
            "roles": ["user"]
        }
        request.url.path = "/test"
        request.method = "GET"
        request.state.correlation_id = "test-123"
        
        with pytest.raises(HTTPException) as exc_info:
            await test_endpoint(request)
        
        assert exc_info.value.status_code == 403
        assert "Permission denied" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_require_any_permission_success(self):
        """Test successful any permission check."""
        @require_any_permission([Permission.USER_READ, Permission.SYSTEM_ADMIN], raise_exception=False)
        async def test_endpoint(request: Request):
            return {"message": "success"}
        
        # Mock request with user having one of the permissions
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "123",
            "username": "testuser",
            "roles": ["user"]
        }
        request.url.path = "/test"
        request.method = "GET"
        request.state.correlation_id = "test-123"
        
        result = await test_endpoint(request)
        assert result == {"message": "success"}
    
    @pytest.mark.asyncio
    async def test_require_all_permissions_success(self):
        """Test successful all permissions check."""
        @require_all_permissions([Permission.USER_READ, Permission.CONTENT_READ], raise_exception=False)
        async def test_endpoint(request: Request):
            return {"message": "success"}
        
        # Mock request with user having all permissions
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "123",
            "username": "testuser",
            "roles": ["user"]
        }
        request.url.path = "/test"
        request.method = "GET"
        request.state.correlation_id = "test-123"
        
        result = await test_endpoint(request)
        assert result == {"message": "success"}
    
    @pytest.mark.asyncio
    async def test_require_role_success(self):
        """Test successful role check."""
        @require_role(Role.USER, raise_exception=False)
        async def test_endpoint(request: Request):
            return {"message": "success"}
        
        # Mock request with user having the role
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "123",
            "username": "testuser",
            "roles": ["user"]
        }
        request.url.path = "/test"
        request.method = "GET"
        request.state.correlation_id = "test-123"
        
        result = await test_endpoint(request)
        assert result == {"message": "success"}
    
    @pytest.mark.asyncio
    async def test_require_role_failure(self):
        """Test failed role check."""
        @require_role(Role.ADMIN, raise_exception=False)
        async def test_endpoint(request: Request):
            return {"message": "success"}
        
        # Mock request with user lacking the role
        request = Mock(spec=Request)
        request.state.user = {
            "user_id": "123",
            "username": "testuser",
            "roles": ["user"]
        }
        request.url.path = "/test"
        request.method = "GET"
        request.state.correlation_id = "test-123"
        
        result = await test_endpoint(request)
        assert result is None


class TestIntegration:
    """Integration tests for RBAC system."""
    
    def test_rbac_with_fastapi(self):
        """Test RBAC integration with FastAPI."""
        app = FastAPI()
        
        @app.get("/user-endpoint")
        @require_permission(Permission.USER_READ)
        async def user_endpoint(request: Request):
            return {"message": "user endpoint"}
        
        @app.get("/admin-endpoint")
        @require_permission(Permission.SYSTEM_ADMIN)
        async def admin_endpoint(request: Request):
            return {"message": "admin endpoint"}
        
        # Mock middleware to set user in request state
        @app.middleware("http")
        async def mock_auth_middleware(request: Request, call_next):
            # Mock different users based on path
            if "admin" in request.url.path:
                request.state.user = {
                    "user_id": "admin_1",
                    "username": "admin",
                    "roles": ["admin"]
                }
            else:
                request.state.user = {
                    "user_id": "user_1", 
                    "username": "user",
                    "roles": ["user"]
                }
            request.state.correlation_id = "test-123"
            return await call_next(request)
        
        client = TestClient(app)
        
        # User endpoint should work for both user and admin
        response = client.get("/user-endpoint")
        assert response.status_code == 200
        
        # Admin endpoint should only work for admin
        response = client.get("/admin-endpoint")
        assert response.status_code == 200