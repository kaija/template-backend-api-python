"""
Tests for graceful shutdown functionality.

This module tests the graceful shutdown handling including signal processing,
connection cleanup, and resource management.
"""

import asyncio
import signal
import time
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.main import GracefulShutdown


class TestGracefulShutdown:
    """Test cases for GracefulShutdown class."""
    
    def test_init(self):
        """Test GracefulShutdown initialization."""
        shutdown_handler = GracefulShutdown(shutdown_timeout=60)
        
        assert shutdown_handler.shutdown is False
        assert shutdown_handler.server is None
        assert shutdown_handler.shutdown_timeout == 60
        assert len(shutdown_handler.active_connections) == 0
        assert not shutdown_handler.shutdown_event.is_set()
    
    def test_init_default_timeout(self):
        """Test GracefulShutdown initialization with default timeout."""
        shutdown_handler = GracefulShutdown()
        
        assert shutdown_handler.shutdown_timeout == 30
    
    def test_set_server(self):
        """Test setting server instance."""
        shutdown_handler = GracefulShutdown()
        mock_server = Mock()
        
        shutdown_handler.set_server(mock_server)
        
        assert shutdown_handler.server is mock_server
    
    def test_add_connection(self):
        """Test adding connection task."""
        shutdown_handler = GracefulShutdown()
        mock_task = Mock()
        mock_task.add_done_callback = Mock()
        
        shutdown_handler.add_connection(mock_task)
        
        assert mock_task in shutdown_handler.active_connections
        mock_task.add_done_callback.assert_called_once()
    
    def test_signal_handler_sigterm(self):
        """Test signal handler for SIGTERM."""
        shutdown_handler = GracefulShutdown()
        mock_server = Mock()
        shutdown_handler.set_server(mock_server)
        
        # Mock time.time to control shutdown start time
        with patch('src.main.time.time', return_value=1234567890):
            shutdown_handler.signal_handler(signal.SIGTERM, None)
        
        assert shutdown_handler.shutdown is True
        assert shutdown_handler.shutdown_event.is_set()
        assert mock_server.should_exit is True
        assert shutdown_handler._shutdown_start_time == 1234567890
    
    def test_signal_handler_sigint(self):
        """Test signal handler for SIGINT."""
        shutdown_handler = GracefulShutdown()
        mock_server = Mock()
        shutdown_handler.set_server(mock_server)
        
        shutdown_handler.signal_handler(signal.SIGINT, None)
        
        assert shutdown_handler.shutdown is True
        assert shutdown_handler.shutdown_event.is_set()
        assert mock_server.should_exit is True
    
    def test_signal_handler_no_server(self):
        """Test signal handler when no server is set."""
        shutdown_handler = GracefulShutdown()
        
        shutdown_handler.signal_handler(signal.SIGTERM, None)
        
        assert shutdown_handler.shutdown is True
        assert shutdown_handler.shutdown_event.is_set()
    
    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self):
        """Test waiting for shutdown signal."""
        shutdown_handler = GracefulShutdown()
        
        # Start waiting for shutdown
        wait_task = asyncio.create_task(shutdown_handler.wait_for_shutdown())
        
        # Give it a moment to start waiting
        await asyncio.sleep(0.01)
        
        # Signal shutdown
        shutdown_handler.signal_handler(signal.SIGTERM, None)
        
        # Wait should complete
        await wait_task
        
        assert shutdown_handler.shutdown is True
    
    @pytest.mark.asyncio
    async def test_cleanup_resources_no_shutdown(self):
        """Test cleanup when shutdown flag is not set."""
        shutdown_handler = GracefulShutdown()
        
        # Should return early if not in shutdown mode
        await shutdown_handler.cleanup_resources()
        
        # No assertions needed - just verify it doesn't raise
    
    @pytest.mark.asyncio
    async def test_cleanup_resources_success(self):
        """Test successful resource cleanup."""
        shutdown_handler = GracefulShutdown()
        shutdown_handler.shutdown = True
        
        with patch.object(shutdown_handler, '_wait_for_active_connections', new_callable=AsyncMock) as mock_wait, \
             patch.object(shutdown_handler, '_close_database_connections', new_callable=AsyncMock) as mock_db, \
             patch.object(shutdown_handler, '_cleanup_other_resources', new_callable=AsyncMock) as mock_other:
            
            await shutdown_handler.cleanup_resources()
            
            mock_wait.assert_called_once()
            mock_db.assert_called_once()
            mock_other.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cleanup_resources_timeout(self):
        """Test resource cleanup with timeout."""
        shutdown_handler = GracefulShutdown(shutdown_timeout=0.1)  # Very short timeout
        shutdown_handler.shutdown = True
        
        async def slow_wait():
            await asyncio.sleep(1)  # Longer than timeout
        
        with patch.object(shutdown_handler, '_wait_for_active_connections', side_effect=asyncio.TimeoutError), \
             patch.object(shutdown_handler, '_force_cleanup', new_callable=AsyncMock) as mock_force:
            
            await shutdown_handler.cleanup_resources()
            
            mock_force.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_wait_for_active_connections_no_connections(self):
        """Test waiting for connections when none are active."""
        shutdown_handler = GracefulShutdown()
        
        # Should complete immediately
        await shutdown_handler._wait_for_active_connections()
        
        # No assertions needed - just verify it doesn't hang
    
    @pytest.mark.asyncio
    async def test_wait_for_active_connections_with_tasks(self):
        """Test waiting for active connections to complete."""
        shutdown_handler = GracefulShutdown(shutdown_timeout=30)
        shutdown_handler._shutdown_start_time = time.time()
        
        # Create mock tasks that complete quickly
        async def quick_task():
            await asyncio.sleep(0.01)
        
        task1 = asyncio.create_task(quick_task())
        task2 = asyncio.create_task(quick_task())
        
        shutdown_handler.active_connections.add(task1)
        shutdown_handler.active_connections.add(task2)
        
        await shutdown_handler._wait_for_active_connections()
        
        # Tasks should be completed
        assert task1.done()
        assert task2.done()
    
    @pytest.mark.asyncio
    async def test_wait_for_active_connections_timeout(self):
        """Test waiting for connections with timeout."""
        shutdown_handler = GracefulShutdown(shutdown_timeout=0.2)
        shutdown_handler._shutdown_start_time = time.time() - 0.1  # Half timeout already elapsed
        
        # Create mock task that takes too long
        async def slow_task():
            try:
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                pass
        
        task = asyncio.create_task(slow_task())
        shutdown_handler.active_connections.add(task)
        
        await shutdown_handler._wait_for_active_connections()
        
        # Task should be cancelled
        assert task.cancelled() or task.done()
        
        # Clean up
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_close_database_connections(self):
        """Test closing database connections."""
        shutdown_handler = GracefulShutdown()
        
        with patch('src.database.config.close_database', new_callable=AsyncMock) as mock_close:
            await shutdown_handler._close_database_connections()
            mock_close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_database_connections_error(self):
        """Test handling error when closing database connections."""
        shutdown_handler = GracefulShutdown()
        
        with patch('src.database.config.close_database', new_callable=AsyncMock, side_effect=Exception("DB error")):
            # Should not raise exception
            await shutdown_handler._close_database_connections()
    
    @pytest.mark.asyncio
    async def test_cleanup_other_resources(self):
        """Test cleanup of other resources."""
        shutdown_handler = GracefulShutdown()
        
        with patch('src.monitoring.metrics.cleanup_metrics') as mock_metrics, \
             patch('sentry_sdk.flush') as mock_sentry:
            
            await shutdown_handler._cleanup_other_resources()
            
            mock_metrics.assert_called_once()
            mock_sentry.assert_called_once_with(timeout=2.0)
    
    @pytest.mark.asyncio
    async def test_cleanup_other_resources_import_error(self):
        """Test cleanup when imports fail."""
        shutdown_handler = GracefulShutdown()
        
        with patch('src.monitoring.metrics.cleanup_metrics', side_effect=ImportError("Module not found")):
            # Should not raise exception
            await shutdown_handler._cleanup_other_resources()
    
    @pytest.mark.asyncio
    async def test_force_cleanup(self):
        """Test forced cleanup."""
        shutdown_handler = GracefulShutdown()
        
        # Create mock tasks
        task1 = Mock()
        task1.done.return_value = False
        task1.cancel = Mock()
        task2 = Mock()
        task2.done.return_value = True
        
        shutdown_handler.active_connections.add(task1)
        shutdown_handler.active_connections.add(task2)
        
        with patch('src.database.config.close_database', new_callable=AsyncMock) as mock_close:
            await shutdown_handler._force_cleanup()
            
            # Only non-done task should be cancelled
            task1.cancel.assert_called_once()
            
            mock_close.assert_called_once()


class TestConnectionTrackingMiddleware:
    """Test cases for ConnectionTrackingMiddleware."""
    
    @pytest.mark.asyncio
    async def test_middleware_tracks_connections(self):
        """Test that middleware tracks active connections."""
        from src.middleware.connection_tracking import ConnectionTrackingMiddleware
        
        app = Mock()
        middleware = ConnectionTrackingMiddleware(app)
        
        request = Mock()
        
        async def mock_call_next(req):
            # Simulate some processing time
            await asyncio.sleep(0.01)
            return Mock()
        
        # Mock current task
        with patch('asyncio.current_task') as mock_current_task:
            mock_task = Mock()
            mock_current_task.return_value = mock_task
            
            response = await middleware.dispatch(request, mock_call_next)
            
            # Task should have been added and removed
            assert mock_task not in middleware.active_requests
    
    @pytest.mark.asyncio
    async def test_middleware_handles_exception(self):
        """Test that middleware handles exceptions properly."""
        from src.middleware.connection_tracking import ConnectionTrackingMiddleware
        
        app = Mock()
        middleware = ConnectionTrackingMiddleware(app)
        
        request = Mock()
        
        async def mock_call_next(req):
            raise ValueError("Test error")
        
        with patch('asyncio.current_task') as mock_current_task:
            mock_task = Mock()
            mock_current_task.return_value = mock_task
            
            with pytest.raises(ValueError):
                await middleware.dispatch(request, mock_call_next)
            
            # Task should still be cleaned up
            assert mock_task not in middleware.active_requests
    
    def test_get_active_request_count(self):
        """Test getting active request count."""
        from src.middleware.connection_tracking import ConnectionTrackingMiddleware
        
        app = Mock()
        middleware = ConnectionTrackingMiddleware(app)
        
        # Add mock tasks
        done_task = Mock()
        done_task.done.return_value = True
        
        active_task = Mock()
        active_task.done.return_value = False
        
        middleware.active_requests.add(done_task)
        middleware.active_requests.add(active_task)
        
        count = middleware.get_active_request_count()
        
        # Should only count active tasks
        assert count == 1
        assert active_task in middleware.active_requests
        assert done_task not in middleware.active_requests
    
    @pytest.mark.asyncio
    async def test_wait_for_requests_no_active(self):
        """Test waiting for requests when none are active."""
        from src.middleware.connection_tracking import ConnectionTrackingMiddleware
        
        app = Mock()
        middleware = ConnectionTrackingMiddleware(app)
        
        result = await middleware.wait_for_requests(timeout=1.0)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_wait_for_requests_timeout(self):
        """Test waiting for requests with timeout."""
        from src.middleware.connection_tracking import ConnectionTrackingMiddleware
        
        app = Mock()
        middleware = ConnectionTrackingMiddleware(app)
        
        # Add a slow task
        async def slow_task():
            await asyncio.sleep(2)
        
        task = asyncio.create_task(slow_task())
        middleware.active_requests.add(task)
        
        result = await middleware.wait_for_requests(timeout=0.1)
        
        assert result is False
        
        # Clean up
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass