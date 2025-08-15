"""
Database module for SQLAlchemy ORM integration.

This module provides database configuration, models, and utilities
for the application's data layer.
"""

from .config import (
    get_database_url,
    create_engine,
    create_session_factory,
    get_session,
    init_database,
    close_database,
    check_database_health,
    get_database_info,
)
from .base import Base
from .models import User, Post, UserStatus
from .repositories import UserRepository, PostRepository, RepositoryFactory

__all__ = [
    # Database configuration
    "get_database_url",
    "create_engine",
    "create_session_factory",
    "get_session",
    "init_database",
    "close_database",
    "check_database_health",
    "get_database_info",

    # Base model
    "Base",

    # Models
    "User",
    "Post",
    "UserStatus",

    # Repositories
    "UserRepository",
    "PostRepository",
    "RepositoryFactory",
]
