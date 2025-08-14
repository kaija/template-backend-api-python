"""
Connection tracking middleware for graceful shutdown.

This middleware tracks active HTTP connections to ensure proper
graceful shutdown handling.
"""

import asyncio
import logging
from typing import Callable, Set, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class ConnectionTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track active HTTP connections.

    This middleware helps with graceful shutdown by tracking active
    requests and allowing the shutdown handler to wait for them to complete.
    """

    def __init__(self, app, shutdown_handler: Optional[object] = None):
        """
        Initialize connection tracking middleware.

        Args:
            app: ASGI application
            shutdown_handler: GracefulShutdown instance for tracking connections
        """
        super().__init__(app)
        self.shutdown_handler = shutdown_handler
        self.active_requests: Set[asyncio.Task] = set()

    def set_shutdown_handler(self, shutdown_handler: object) -> None:
        """
        Set the shutdown handler after middleware initialization.

        Args:
            shutdown_handler: GracefulShutdown instance
        """
        self.shutdown_handler = shutdown_handler

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process HTTP request and track connection.

        Args:
            request: HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Get current task
        current_task = asyncio.current_task()

        # Add to active requests
        if current_task:
            self.active_requests.add(current_task)

            # Also add to shutdown handler if available
            if self.shutdown_handler and hasattr(self.shutdown_handler, 'add_connection'):
                self.shutdown_handler.add_connection(current_task)

        try:
            # Process request
            response = await call_next(request)
            return response

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            raise

        finally:
            # Remove from active requests
            if current_task:
                self.active_requests.discard(current_task)

    def get_active_request_count(self) -> int:
        """
        Get the number of active requests.

        Returns:
            Number of active requests
        """
        # Clean up completed tasks
        self.active_requests = {task for task in self.active_requests if not task.done()}
        return len(self.active_requests)

    async def wait_for_requests(self, timeout: float = 30.0) -> bool:
        """
        Wait for all active requests to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if all requests completed, False if timeout occurred
        """
        if not self.active_requests:
            return True

        logger.info(f"Waiting for {len(self.active_requests)} active requests to complete...")

        try:
            await asyncio.wait_for(
                asyncio.gather(*self.active_requests, return_exceptions=True),
                timeout=timeout
            )
            logger.info("All active requests completed")
            return True

        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for requests to complete, {len(self.active_requests)} requests still active")
            return False

        except Exception as e:
            logger.error(f"Error waiting for requests: {e}", exc_info=True)
            return False
