"""
Generic test data factories for creating test objects.

This module provides example factory classes using factory_boy that demonstrate
common patterns for creating test data. These can be adapted for your specific
domain models and testing needs.
"""

import factory
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import uuid4

# Import models (these would be actual model classes in a real implementation)
# For now, we'll create mock model classes for demonstration


class MockUser:
    """Mock User model for testing."""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid4()))
        self.username = kwargs.get('username', 'testuser')
        self.email = kwargs.get('email', 'test@example.com')
        self.first_name = kwargs.get('first_name', 'Test')
        self.last_name = kwargs.get('last_name', 'User')
        self.is_active = kwargs.get('is_active', True)
        self.is_verified = kwargs.get('is_verified', True)
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))
        self.roles = kwargs.get('roles', ['user'])
        self.permissions = kwargs.get('permissions', ['read'])


class MockPost:
    """Mock Post model for testing."""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid4()))
        self.title = kwargs.get('title', 'Test Post')
        self.content = kwargs.get('content', 'Test content')
        self.author_id = kwargs.get('author_id', str(uuid4()))
        self.is_published = kwargs.get('is_published', False)
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))


class MockComment:
    """Mock Comment model for testing."""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id', str(uuid4()))
        self.content = kwargs.get('content', 'Test comment')
        self.post_id = kwargs.get('post_id', str(uuid4()))
        self.author_id = kwargs.get('author_id', str(uuid4()))
        self.is_approved = kwargs.get('is_approved', True)
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = kwargs.get('updated_at', datetime.now(timezone.utc))


# Factory classes
class UserFactory(factory.Factory):
    """
    Factory for creating User test objects.
    
    This factory creates User objects with realistic test data
    that can be used across different test scenarios.
    """
    
    class Meta:
        model = MockUser
    
    # Basic fields
    id = factory.LazyFunction(lambda: str(uuid4()))
    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    
    # Status fields
    is_active = True
    is_verified = True
    
    # Timestamps
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    
    # Authorization
    roles = factory.LazyFunction(lambda: ['user'])
    permissions = factory.LazyFunction(lambda: ['read'])


class AdminUserFactory(UserFactory):
    """
    Factory for creating Admin User test objects.
    
    Extends UserFactory to create users with admin privileges.
    """
    
    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    roles = factory.LazyFunction(lambda: ['admin', 'user'])
    permissions = factory.LazyFunction(lambda: ['read', 'write', 'admin', 'delete'])


class InactiveUserFactory(UserFactory):
    """
    Factory for creating inactive User test objects.
    
    Extends UserFactory to create inactive users for testing
    authentication and authorization scenarios.
    """
    
    is_active = False
    is_verified = False


class PostFactory(factory.Factory):
    """
    Factory for creating Post test objects.
    
    This factory creates Post objects with realistic test data
    including relationships to User objects.
    """
    
    class Meta:
        model = MockPost
    
    # Basic fields
    id = factory.LazyFunction(lambda: str(uuid4()))
    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=500)
    
    # Relationships
    author_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Status
    is_published = False
    
    # Timestamps
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class PublishedPostFactory(PostFactory):
    """
    Factory for creating published Post test objects.
    
    Extends PostFactory to create published posts.
    """
    
    is_published = True


class CommentFactory(factory.Factory):
    """
    Factory for creating Comment test objects.
    
    This factory creates Comment objects with relationships
    to Post and User objects.
    """
    
    class Meta:
        model = MockComment
    
    # Basic fields
    id = factory.LazyFunction(lambda: str(uuid4()))
    content = factory.Faker('text', max_nb_chars=200)
    
    # Relationships
    post_id = factory.LazyFunction(lambda: str(uuid4()))
    author_id = factory.LazyFunction(lambda: str(uuid4()))
    
    # Status
    is_approved = True
    
    # Timestamps
    created_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = factory.LazyFunction(lambda: datetime.now(timezone.utc))


class UnapprovedCommentFactory(CommentFactory):
    """
    Factory for creating unapproved Comment test objects.
    
    Extends CommentFactory to create unapproved comments.
    """
    
    is_approved = False


# Request/Response factories for API testing
class APIRequestFactory(factory.DictFactory):
    """
    Factory for creating API request data.
    
    This factory creates dictionary objects that represent
    API request payloads for testing endpoints.
    """
    
    # Common request fields
    request_id = factory.LazyFunction(lambda: str(uuid4()))
    timestamp = factory.LazyFunction(lambda: datetime.now(timezone.utc).isoformat())


class UserCreateRequestFactory(APIRequestFactory):
    """
    Factory for creating user creation request data.
    """
    
    username = factory.Sequence(lambda n: f"newuser{n}")
    email = factory.Sequence(lambda n: f"newuser{n}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    password = factory.Faker('password', length=12)


class UserUpdateRequestFactory(APIRequestFactory):
    """
    Factory for creating user update request data.
    """
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')


class PostCreateRequestFactory(APIRequestFactory):
    """
    Factory for creating post creation request data.
    """
    
    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=1000)
    is_published = False


class PostUpdateRequestFactory(APIRequestFactory):
    """
    Factory for creating post update request data.
    """
    
    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('text', max_nb_chars=1000)


class CommentCreateRequestFactory(APIRequestFactory):
    """
    Factory for creating comment creation request data.
    """
    
    content = factory.Faker('text', max_nb_chars=300)
    post_id = factory.LazyFunction(lambda: str(uuid4()))


# Authentication factories
class JWTTokenFactory(factory.DictFactory):
    """
    Factory for creating JWT token data.
    """
    
    user_id = factory.LazyFunction(lambda: str(uuid4()))
    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    roles = factory.LazyFunction(lambda: ['user'])
    permissions = factory.LazyFunction(lambda: ['read'])
    exp = factory.LazyFunction(lambda: int((datetime.now(timezone.utc).timestamp() + 3600)))
    iat = factory.LazyFunction(lambda: int(datetime.now(timezone.utc).timestamp()))


class AdminJWTTokenFactory(JWTTokenFactory):
    """
    Factory for creating admin JWT token data.
    """
    
    roles = factory.LazyFunction(lambda: ['admin', 'user'])
    permissions = factory.LazyFunction(lambda: ['read', 'write', 'admin', 'delete'])


# Error response factories
class ErrorResponseFactory(factory.DictFactory):
    """
    Factory for creating error response data.
    """
    
    error = factory.SubFactory(factory.DictFactory, 
        code="GENERIC_ERROR",
        message="An error occurred",
        details=factory.LazyFunction(list),
        trace_id=factory.LazyFunction(lambda: str(uuid4()))
    )


class ValidationErrorResponseFactory(ErrorResponseFactory):
    """
    Factory for creating validation error response data.
    """
    
    error = factory.SubFactory(factory.DictFactory,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=factory.LazyFunction(lambda: [
            {"field": "email", "message": "Invalid email format"}
        ]),
        trace_id=factory.LazyFunction(lambda: str(uuid4()))
    )


class AuthenticationErrorResponseFactory(ErrorResponseFactory):
    """
    Factory for creating authentication error response data.
    """
    
    error = factory.SubFactory(factory.DictFactory,
        code="AUTHENTICATION_ERROR",
        message="Authentication required",
        details=factory.LazyFunction(list),
        trace_id=factory.LazyFunction(lambda: str(uuid4()))
    )


class AuthorizationErrorResponseFactory(ErrorResponseFactory):
    """
    Factory for creating authorization error response data.
    """
    
    error = factory.SubFactory(factory.DictFactory,
        code="AUTHORIZATION_ERROR",
        message="Insufficient permissions",
        details=factory.LazyFunction(list),
        trace_id=factory.LazyFunction(lambda: str(uuid4()))
    )


# Utility functions for creating test data
def create_user_with_posts(num_posts: int = 3, published: bool = False) -> Dict[str, Any]:
    """
    Create a user with associated posts.
    
    Args:
        num_posts: Number of posts to create
        published: Whether posts should be published
        
    Returns:
        Dictionary with user and posts data
    """
    user = UserFactory()
    
    post_factory = PublishedPostFactory if published else PostFactory
    posts = [post_factory(author_id=user.id) for _ in range(num_posts)]
    
    return {
        "user": user,
        "posts": posts
    }


def create_post_with_comments(num_comments: int = 5, approved: bool = True) -> Dict[str, Any]:
    """
    Create a post with associated comments.
    
    Args:
        num_comments: Number of comments to create
        approved: Whether comments should be approved
        
    Returns:
        Dictionary with post and comments data
    """
    post = PostFactory()
    
    comment_factory = CommentFactory if approved else UnapprovedCommentFactory
    comments = [comment_factory(post_id=post.id) for _ in range(num_comments)]
    
    return {
        "post": post,
        "comments": comments
    }


def create_complete_test_scenario() -> Dict[str, Any]:
    """
    Create a complete test scenario with users, posts, and comments.
    
    Returns:
        Dictionary with complete test data scenario
    """
    # Create users
    admin = AdminUserFactory()
    active_user = UserFactory()
    inactive_user = InactiveUserFactory()
    
    # Create posts
    published_post = PublishedPostFactory(author_id=active_user.id)
    draft_post = PostFactory(author_id=active_user.id)
    
    # Create comments
    approved_comment = CommentFactory(
        post_id=published_post.id,
        author_id=active_user.id
    )
    unapproved_comment = UnapprovedCommentFactory(
        post_id=published_post.id,
        author_id=inactive_user.id
    )
    
    return {
        "users": {
            "admin": admin,
            "active": active_user,
            "inactive": inactive_user
        },
        "posts": {
            "published": published_post,
            "draft": draft_post
        },
        "comments": {
            "approved": approved_comment,
            "unapproved": unapproved_comment
        }
    }


# Batch creation utilities
def create_users(count: int = 10, **kwargs) -> list:
    """
    Create multiple users for testing.
    
    Args:
        count: Number of users to create
        **kwargs: Additional attributes for users
        
    Returns:
        List of user objects
    """
    return [UserFactory(**kwargs) for _ in range(count)]


def create_posts(count: int = 10, author_id: Optional[str] = None, **kwargs) -> list:
    """
    Create multiple posts for testing.
    
    Args:
        count: Number of posts to create
        author_id: Author ID for all posts
        **kwargs: Additional attributes for posts
        
    Returns:
        List of post objects
    """
    if author_id:
        kwargs['author_id'] = author_id
    
    return [PostFactory(**kwargs) for _ in range(count)]


def create_comments(count: int = 10, post_id: Optional[str] = None, **kwargs) -> list:
    """
    Create multiple comments for testing.
    
    Args:
        count: Number of comments to create
        post_id: Post ID for all comments
        **kwargs: Additional attributes for comments
        
    Returns:
        List of comment objects
    """
    if post_id:
        kwargs['post_id'] = post_id
    
    return [CommentFactory(**kwargs) for _ in range(count)]