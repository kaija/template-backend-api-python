"""
Role-Based Access Control (RBAC) system.

This module provides a comprehensive RBAC system with roles, permissions,
and decorators for protecting endpoints.
"""

import logging
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Union
from fastapi import HTTPException, Request, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """
    System permissions enumeration.

    This enum defines all available permissions in the system.
    """
    # User management permissions
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"

    # Content management permissions
    CONTENT_READ = "content:read"
    CONTENT_WRITE = "content:write"
    CONTENT_DELETE = "content:delete"
    CONTENT_PUBLISH = "content:publish"

    # System administration permissions
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"

    # API access permissions
    API_READ = "api:read"
    API_WRITE = "api:write"
    API_ADMIN = "api:admin"

    # Audit and monitoring permissions
    AUDIT_READ = "audit:read"
    AUDIT_WRITE = "audit:write"

    # Special permissions
    ALL = "*"  # Wildcard permission (super admin)


class Role(str, Enum):
    """
    System roles enumeration.

    This enum defines all available roles in the system.
    """
    # Basic user roles
    GUEST = "guest"
    USER = "user"
    PREMIUM_USER = "premium_user"

    # Staff roles
    MODERATOR = "moderator"
    EDITOR = "editor"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

    # API roles
    API_USER = "api_user"
    API_SERVICE = "api_service"

    # System roles
    SYSTEM = "system"


class RolePermissions(BaseModel):
    """
    Role permissions mapping.

    This class defines which permissions are granted to each role.
    """
    role: Role
    permissions: Set[Permission]
    description: str
    inherits_from: Optional[List[Role]] = None


# Default role-permission mappings
DEFAULT_ROLE_PERMISSIONS: Dict[Role, RolePermissions] = {
    Role.GUEST: RolePermissions(
        role=Role.GUEST,
        permissions={Permission.CONTENT_READ},
        description="Guest user with read-only access to public content"
    ),

    Role.USER: RolePermissions(
        role=Role.USER,
        permissions={
            Permission.USER_READ,
            Permission.CONTENT_READ,
            Permission.CONTENT_WRITE,
            Permission.API_READ,
        },
        description="Regular user with basic read/write permissions",
        inherits_from=[Role.GUEST]
    ),

    Role.PREMIUM_USER: RolePermissions(
        role=Role.PREMIUM_USER,
        permissions={
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.CONTENT_READ,
            Permission.CONTENT_WRITE,
            Permission.API_READ,
            Permission.API_WRITE,
        },
        description="Premium user with enhanced permissions",
        inherits_from=[Role.USER]
    ),

    Role.MODERATOR: RolePermissions(
        role=Role.MODERATOR,
        permissions={
            Permission.USER_READ,
            Permission.CONTENT_READ,
            Permission.CONTENT_WRITE,
            Permission.CONTENT_DELETE,
            Permission.API_READ,
        },
        description="Moderator with content management permissions",
        inherits_from=[Role.USER]
    ),

    Role.EDITOR: RolePermissions(
        role=Role.EDITOR,
        permissions={
            Permission.USER_READ,
            Permission.CONTENT_READ,
            Permission.CONTENT_WRITE,
            Permission.CONTENT_DELETE,
            Permission.CONTENT_PUBLISH,
            Permission.API_READ,
            Permission.API_WRITE,
        },
        description="Editor with content publishing permissions",
        inherits_from=[Role.MODERATOR]
    ),

    Role.ADMIN: RolePermissions(
        role=Role.ADMIN,
        permissions={
            Permission.USER_READ,
            Permission.USER_WRITE,
            Permission.USER_DELETE,
            Permission.CONTENT_READ,
            Permission.CONTENT_WRITE,
            Permission.CONTENT_DELETE,
            Permission.CONTENT_PUBLISH,
            Permission.SYSTEM_READ,
            Permission.SYSTEM_WRITE,
            Permission.SYSTEM_ADMIN,
            Permission.API_READ,
            Permission.API_WRITE,
            Permission.AUDIT_READ,
        },
        description="Administrator with user and system management permissions",
        inherits_from=[Role.EDITOR]
    ),

    Role.SUPER_ADMIN: RolePermissions(
        role=Role.SUPER_ADMIN,
        permissions={Permission.ALL},
        description="Super administrator with all permissions",
        inherits_from=[Role.ADMIN]
    ),

    Role.API_USER: RolePermissions(
        role=Role.API_USER,
        permissions={
            Permission.API_READ,
            Permission.CONTENT_READ,
        },
        description="API user with read access"
    ),

    Role.API_SERVICE: RolePermissions(
        role=Role.API_SERVICE,
        permissions={
            Permission.API_READ,
            Permission.API_WRITE,
            Permission.CONTENT_READ,
            Permission.CONTENT_WRITE,
        },
        description="API service with read/write access"
    ),

    Role.SYSTEM: RolePermissions(
        role=Role.SYSTEM,
        permissions={Permission.ALL},
        description="System role with all permissions"
    ),
}


class RBACManager:
    """
    Role-Based Access Control manager.

    This class manages roles, permissions, and access control logic.
    """

    def __init__(self, role_permissions: Optional[Dict[Role, RolePermissions]] = None):
        """
        Initialize RBAC manager.

        Args:
            role_permissions: Custom role-permission mappings
        """
        self.role_permissions = role_permissions or DEFAULT_ROLE_PERMISSIONS
        self._permission_cache: Dict[Role, Set[Permission]] = {}
        self._build_permission_cache()

    def _build_permission_cache(self) -> None:
        """Build permission cache with inheritance resolution."""
        self._permission_cache.clear()

        # Process roles in dependency order
        processed_roles: Set[Role] = set()

        def process_role(role: Role) -> Set[Permission]:
            if role in processed_roles:
                return self._permission_cache.get(role, set())

            role_perms = self.role_permissions.get(role)
            if not role_perms:
                return set()

            permissions = set(role_perms.permissions)

            # Add inherited permissions
            if role_perms.inherits_from:
                for parent_role in role_perms.inherits_from:
                    parent_permissions = process_role(parent_role)
                    permissions.update(parent_permissions)

            self._permission_cache[role] = permissions
            processed_roles.add(role)
            return permissions

        # Process all roles
        for role in self.role_permissions.keys():
            process_role(role)

    def get_role_permissions(self, role: Union[Role, str]) -> Set[Permission]:
        """
        Get all permissions for a role (including inherited).

        Args:
            role: Role to get permissions for

        Returns:
            Set of permissions for the role
        """
        if isinstance(role, str):
            try:
                role = Role(role)
            except ValueError:
                logger.warning(f"Unknown role: {role}")
                return set()

        return self._permission_cache.get(role, set())

    def has_permission(
        self,
        user_roles: List[Union[Role, str]],
        required_permission: Union[Permission, str]
    ) -> bool:
        """
        Check if user has a specific permission.

        Args:
            user_roles: List of user roles
            required_permission: Required permission

        Returns:
            True if user has the permission
        """
        if isinstance(required_permission, str):
            try:
                required_permission = Permission(required_permission)
            except ValueError:
                logger.warning(f"Unknown permission: {required_permission}")
                return False

        # Check each user role
        for role in user_roles:
            role_permissions = self.get_role_permissions(role)

            # Check for wildcard permission (super admin)
            if Permission.ALL in role_permissions:
                return True

            # Check for specific permission
            if required_permission in role_permissions:
                return True

        return False

    def has_any_permission(
        self,
        user_roles: List[Union[Role, str]],
        required_permissions: List[Union[Permission, str]]
    ) -> bool:
        """
        Check if user has any of the specified permissions.

        Args:
            user_roles: List of user roles
            required_permissions: List of required permissions

        Returns:
            True if user has any of the permissions
        """
        for permission in required_permissions:
            if self.has_permission(user_roles, permission):
                return True
        return False

    def has_all_permissions(
        self,
        user_roles: List[Union[Role, str]],
        required_permissions: List[Union[Permission, str]]
    ) -> bool:
        """
        Check if user has all of the specified permissions.

        Args:
            user_roles: List of user roles
            required_permissions: List of required permissions

        Returns:
            True if user has all permissions
        """
        for permission in required_permissions:
            if not self.has_permission(user_roles, permission):
                return False
        return True

    def get_user_permissions(self, user_roles: List[Union[Role, str]]) -> Set[Permission]:
        """
        Get all permissions for a user based on their roles.

        Args:
            user_roles: List of user roles

        Returns:
            Set of all user permissions
        """
        all_permissions: Set[Permission] = set()

        for role in user_roles:
            role_permissions = self.get_role_permissions(role)
            all_permissions.update(role_permissions)

        return all_permissions


# Global RBAC manager instance
rbac_manager = RBACManager()


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """
    Get current user from request state.

    Args:
        request: FastAPI request object

    Returns:
        User information if authenticated
    """
    return getattr(request.state, "user", None)


def get_user_roles(user: Optional[Dict[str, Any]]) -> List[str]:
    """
    Extract user roles from user information.

    Args:
        user: User information dictionary

    Returns:
        List of user roles
    """
    if not user:
        return [Role.GUEST]

    roles = user.get("roles", [])
    if not roles:
        return [Role.USER]  # Default role for authenticated users

    return roles


def require_permission(
    permission: Union[Permission, str],
    raise_exception: bool = True
) -> Callable:
    """
    Decorator to require a specific permission for an endpoint.

    Args:
        permission: Required permission
        raise_exception: Whether to raise exception on access denied

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # Try to find request in kwargs
                request = kwargs.get("request")

            if not request:
                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Request object not found"
                    )
                return None

            # Get current user
            user = get_current_user(request)
            user_roles = get_user_roles(user)

            # Check permission
            if not rbac_manager.has_permission(user_roles, permission):
                logger.warning(
                    f"Access denied: User {user.get('username', 'anonymous') if user else 'anonymous'} "
                    f"lacks permission {permission}",
                    extra={
                        "event_type": "access_denied",
                        "user_id": user.get("user_id") if user else None,
                        "username": user.get("username") if user else None,
                        "required_permission": str(permission),
                        "user_roles": user_roles,
                        "path": request.url.path,
                        "method": request.method,
                        "correlation_id": getattr(request.state, "correlation_id", None),
                    }
                )

                # Log audit event for denied authorization
                try:
                    from src.audit.audit_logger import log_authorization_event, AuditEventType
                    log_authorization_event(
                        event_type=AuditEventType.ACCESS_DENIED,
                        username=user.get("username") if user else None,
                        user_id=user.get("user_id") if user else None,
                        user_roles=user_roles,
                        resource=request.url.path,
                        action=str(permission),
                        correlation_id=getattr(request.state, "correlation_id", None),
                        outcome="failure",
                        details={
                            "required_permission": str(permission),
                            "method": request.method,
                        }
                    )
                except ImportError:
                    # Audit logging not available
                    pass

                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission} required"
                    )
                return None

            # Log successful authorization
            logger.info(
                f"Access granted: User {user.get('username', 'anonymous') if user else 'anonymous'} "
                f"has permission {permission}",
                extra={
                    "event_type": "access_granted",
                    "user_id": user.get("user_id") if user else None,
                    "username": user.get("username") if user else None,
                    "required_permission": str(permission),
                    "user_roles": user_roles,
                    "path": request.url.path,
                    "method": request.method,
                    "correlation_id": getattr(request.state, "correlation_id", None),
                }
            )

            # Log audit event for successful authorization
            try:
                from src.audit.audit_logger import log_authorization_event, AuditEventType
                log_authorization_event(
                    event_type=AuditEventType.ACCESS_GRANTED,
                    username=user.get("username") if user else None,
                    user_id=user.get("user_id") if user else None,
                    user_roles=user_roles,
                    resource=request.url.path,
                    action=str(permission),
                    correlation_id=getattr(request.state, "correlation_id", None),
                    outcome="success",
                    details={
                        "required_permission": str(permission),
                        "method": request.method,
                    }
                )
            except ImportError:
                # Audit logging not available
                pass

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_any_permission(
    permissions: List[Union[Permission, str]],
    raise_exception: bool = True
) -> Callable:
    """
    Decorator to require any of the specified permissions for an endpoint.

    Args:
        permissions: List of required permissions (user needs any one)
        raise_exception: Whether to raise exception on access denied

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Request object not found"
                    )
                return None

            # Get current user
            user = get_current_user(request)
            user_roles = get_user_roles(user)

            # Check permissions
            if not rbac_manager.has_any_permission(user_roles, permissions):
                logger.warning(
                    f"Access denied: User {user.get('username', 'anonymous') if user else 'anonymous'} "
                    f"lacks any of permissions {permissions}",
                    extra={
                        "event_type": "access_denied",
                        "user_id": user.get("user_id") if user else None,
                        "username": user.get("username") if user else None,
                        "required_permissions": [str(p) for p in permissions],
                        "user_roles": user_roles,
                        "path": request.url.path,
                        "method": request.method,
                        "correlation_id": getattr(request.state, "correlation_id", None),
                    }
                )

                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: One of {permissions} required"
                    )
                return None

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_all_permissions(
    permissions: List[Union[Permission, str]],
    raise_exception: bool = True
) -> Callable:
    """
    Decorator to require all of the specified permissions for an endpoint.

    Args:
        permissions: List of required permissions (user needs all)
        raise_exception: Whether to raise exception on access denied

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Request object not found"
                    )
                return None

            # Get current user
            user = get_current_user(request)
            user_roles = get_user_roles(user)

            # Check permissions
            if not rbac_manager.has_all_permissions(user_roles, permissions):
                logger.warning(
                    f"Access denied: User {user.get('username', 'anonymous') if user else 'anonymous'} "
                    f"lacks all permissions {permissions}",
                    extra={
                        "event_type": "access_denied",
                        "user_id": user.get("user_id") if user else None,
                        "username": user.get("username") if user else None,
                        "required_permissions": [str(p) for p in permissions],
                        "user_roles": user_roles,
                        "path": request.url.path,
                        "method": request.method,
                        "correlation_id": getattr(request.state, "correlation_id", None),
                    }
                )

                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: All of {permissions} required"
                    )
                return None

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_role(
    role: Union[Role, str],
    raise_exception: bool = True
) -> Callable:
    """
    Decorator to require a specific role for an endpoint.

    Args:
        role: Required role
        raise_exception: Whether to raise exception on access denied

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find request object in arguments
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                request = kwargs.get("request")

            if not request:
                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Request object not found"
                    )
                return None

            # Get current user
            user = get_current_user(request)
            user_roles = get_user_roles(user)

            # Check role
            required_role = role.value if hasattr(role, 'value') else str(role)
            if required_role not in user_roles:
                logger.warning(
                    f"Access denied: User {user.get('username', 'anonymous') if user else 'anonymous'} "
                    f"lacks role {required_role}",
                    extra={
                        "event_type": "access_denied",
                        "user_id": user.get("user_id") if user else None,
                        "username": user.get("username") if user else None,
                        "required_role": required_role,
                        "user_roles": user_roles,
                        "path": request.url.path,
                        "method": request.method,
                        "correlation_id": getattr(request.state, "correlation_id", None),
                    }
                )

                if raise_exception:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Role denied: {required_role} required"
                    )
                return None

            return await func(*args, **kwargs)

        return wrapper
    return decorator
