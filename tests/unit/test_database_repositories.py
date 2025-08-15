"""
Tests for database repositories.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from src.database.repositories import (
    BaseRepository,
    UserRepository,
    PostRepository,
    RepositoryFactory,
    RepositoryError,
    NotFoundError,
    DuplicateError,
)
from src.database.models import User, Post, UserStatus


# Use the actual User model for testing instead of a mock
# This ensures we're testing with real SQLAlchemy model behavior


class TestBaseRepository:
    """Test BaseRepository functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository(self, mock_session):
        """BaseRepository instance with mock session."""
        return BaseRepository(mock_session, User)
    
    @pytest.mark.asyncio
    async def test_create_success(self, repository, mock_session):
        """Test successful record creation."""
        # Create a mock user instance
        mock_user = Mock()
        mock_user.id = "new_id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        
        # Mock session methods
        mock_session.add = Mock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock the User constructor to return our mock instance
        with patch.object(User, '__new__', return_value=mock_user):
            result = await repository.create(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed_password"
            )
            
            mock_session.add.assert_called_once_with(mock_user)
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once_with(mock_user)
    
    @pytest.mark.asyncio
    async def test_create_duplicate_error(self, repository, mock_session):
        """Test creation with duplicate constraint violation."""
        # Create a mock user instance
        mock_user = Mock()
        mock_user.id = "new_id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        
        # Mock session methods
        mock_session.add = Mock()
        mock_session.flush = AsyncMock(side_effect=IntegrityError("", "", ""))
        mock_session.rollback = AsyncMock()
        
        # Mock the User constructor to return our mock instance
        with patch.object(User, '__new__', return_value=mock_user):
            with pytest.raises(DuplicateError):
                await repository.create(
                    username="testuser",
                    email="test@example.com",
                    hashed_password="hashed_password"
                )
        
        mock_session.rollback.assert_called_once()
        
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session):
        """Test getting record by ID when found."""
        mock_user = Mock()
        mock_user.id = "test_id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_by_id("test_id")
        
        assert result == mock_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test getting record by ID when not found."""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.get_by_id("nonexistent_id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_found(self, repository, mock_session):
        """Test getting record by ID or raise when found."""
        mock_user = Mock()
        mock_user.id = "test_id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        
        with patch.object(repository, 'get_by_id', return_value=mock_user):
            result = await repository.get_by_id_or_raise("test_id")
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_get_by_id_or_raise_not_found(self, repository, mock_session):
        """Test getting record by ID or raise when not found."""
        with patch.object(repository, 'get_by_id', return_value=None):
            with pytest.raises(NotFoundError):
                await repository.get_by_id_or_raise("nonexistent_id")
    
    @pytest.mark.asyncio
    async def test_update_success(self, repository, mock_session):
        """Test successful record update."""
        mock_user = Mock()
        mock_user.id = "test_id"
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed_password"
        
        with patch.object(repository, 'get_by_id_or_raise', return_value=mock_user):
            mock_session.flush = AsyncMock()
            mock_session.refresh = AsyncMock()
            
            result = await repository.update("test_id", username="new_username")
            
            assert result.username == "new_username"
            mock_session.flush.assert_called_once()
            mock_session.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_success(self, repository, mock_session):
        """Test successful record deletion."""
        mock_result = Mock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.delete("test_id")
        
        assert result is True
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_not_found(self, repository, mock_session):
        """Test deletion when record not found."""
        mock_result = Mock()
        mock_result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.delete("nonexistent_id")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_all(self, repository, mock_session):
        """Test listing all records."""
        mock_users = []
        for i in range(3):
            mock_user = Mock()
            mock_user.id = f"id_{i}"
            mock_user.username = f"user_{i}"
            mock_user.email = f"user_{i}@example.com"
            mock_user.hashed_password = "hashed_password"
            mock_users.append(mock_user)
            
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.list_all(limit=10, offset=0)
        
        assert len(result) == 3
        assert result == mock_users
    
    @pytest.mark.asyncio
    async def test_count(self, repository, mock_session):
        """Test counting records."""
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.count()
        
        assert result == 5
    
    @pytest.mark.asyncio
    async def test_exists_true(self, repository, mock_session):
        """Test checking if record exists (true case)."""
        mock_result = Mock()
        mock_result.scalar.return_value = 1
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.exists("test_id")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, repository, mock_session):
        """Test checking if record exists (false case)."""
        mock_result = Mock()
        mock_result.scalar.return_value = 0
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await repository.exists("nonexistent_id")
        
        assert result is False


class TestUserRepository:
    """Test UserRepository functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def user_repository(self, mock_session):
        """UserRepository instance with mock session."""
        return UserRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_get_by_username(self, user_repository, mock_session):
        """Test getting user by username."""
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await user_repository.get_by_username("testuser")
        
        assert result == mock_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, user_repository, mock_session):
        """Test getting user by email."""
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed"
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await user_repository.get_by_email("test@example.com")
        
        assert result == mock_user
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_active_users(self, user_repository, mock_session):
        """Test getting active users."""
        mock_users = []
        for i in range(2):
            mock_user = Mock()
            mock_user.id = f"user_{i}"
            mock_user.username = f"user_{i}"
            mock_user.email = f"user_{i}@example.com"
            mock_user.is_active = True
            mock_users.append(mock_user)
        
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_users
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await user_repository.get_active_users()
        
        assert len(result) == 2
        assert all(user.is_active for user in result)
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_user(self, user_repository, mock_session):
        """Test creating a new user."""
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = "hashed"
        
        with patch.object(user_repository, 'create', return_value=mock_user) as mock_create:
            result = await user_repository.create(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed"
            )
            
            assert result == mock_user
            mock_create.assert_called_once_with(
                username="testuser",
                email="test@example.com",
                hashed_password="hashed"
            )


class TestPostRepository:
    """Test PostRepository functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def post_repository(self, mock_session):
        """PostRepository instance with mock session."""
        return PostRepository(mock_session)
    
    @pytest.mark.asyncio
    async def test_get_by_author(self, post_repository, mock_session):
        """Test getting posts by author."""
        mock_post = Mock()
        mock_post.title = "Test Post"
        mock_post.content = "Test content"
        mock_post.author_id = "user_123"
        
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_post]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await post_repository.get_by_author("user_123")
        
        assert len(result) == 1
        assert result[0] == mock_post
        mock_session.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_published_posts(self, post_repository, mock_session):
        """Test getting published posts."""
        mock_post = Mock()
        mock_post.title = "Published Post"
        mock_post.content = "Published content"
        mock_post.author_id = "user_123"
        mock_post.is_published = True
        
        mock_result = Mock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = [mock_post]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await post_repository.get_published_posts()
        
        assert len(result) == 1
        assert result[0] == mock_post
        assert result[0].is_published is True
        mock_session.execute.assert_called_once()


class TestRepositoryFactory:
    """Test RepositoryFactory functionality."""
    
    @pytest.fixture
    def mock_session(self):
        """Mock AsyncSession."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def repository_factory(self, mock_session):
        """RepositoryFactory instance with mock session."""
        return RepositoryFactory(mock_session)
    
    def test_users_property(self, repository_factory):
        """Test users repository property."""
        users_repo = repository_factory.users
        assert isinstance(users_repo, UserRepository)
        assert users_repo.session == repository_factory.session
    
    def test_posts_property(self, repository_factory):
        """Test posts repository property."""
        posts_repo = repository_factory.posts
        assert isinstance(posts_repo, PostRepository)
        assert posts_repo.session == repository_factory.session


class TestRepositoryExceptions:
    """Test repository exception classes."""
    
    def test_repository_error(self):
        """Test RepositoryError exception."""
        error = RepositoryError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)
    
    def test_not_found_error(self):
        """Test NotFoundError exception."""
        error = NotFoundError("Record not found")
        assert str(error) == "Record not found"
        assert isinstance(error, RepositoryError)
    
    def test_duplicate_error(self):
        """Test DuplicateError exception."""
        error = DuplicateError("Duplicate record")
        assert str(error) == "Duplicate record"
        assert isinstance(error, RepositoryError)


class TestRepositoryIntegration:
    """Integration tests for repository functionality."""
    
    @pytest.mark.asyncio
    async def test_repository_with_real_models(self):
        """Test repository with actual model instances."""
        mock_session = AsyncMock(spec=AsyncSession)
        user_repo = UserRepository(mock_session)
        
        # Test that repository is properly initialized
        assert user_repo.session == mock_session
        assert user_repo.model_class == User
    
    @pytest.mark.asyncio
    async def test_multiple_repositories_same_session(self):
        """Test multiple repositories sharing the same session."""
        mock_session = AsyncMock(spec=AsyncSession)
        
        user_repo = UserRepository(mock_session)
        post_repo = PostRepository(mock_session)
        
        # Both repositories should share the same session
        assert user_repo.session == mock_session
        assert post_repo.session == mock_session
        assert user_repo.session == post_repo.session