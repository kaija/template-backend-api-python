"""
Authentication and authorization module.

This module provides comprehensive authentication and authorization
functionality including JWT tokens, API keys, OAuth2, and RBAC.
"""

from .rbac import (
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

__all__ = [
    # RBAC classes and enums
    "Permission",
    "Role", 
    "RBACManager",
    "rbac_manager",
    
    # Decorators
    "require_permission",
    "require_any_permission", 
    "require_all_permissions",
    "require_role",
    
    # Utility functions
    "get_current_user",
    "get_user_roles",
]