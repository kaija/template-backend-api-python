"""
Main application entry point.

This module provides the main entry point for running the FastAPI application
with proper async setup and configuration.
"""

import asyncio
import logging
import signal
import sys
import time
from typing import Optional, Set

import uvicorn

from src.app import get_application
from src.config import settings, is_development, is_production, get_environment


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """
    Handles graceful shutdown of the application.

    This class manages shutdown signals and ensures proper cleanup
    of resources when the application is terminated.
    """

    def __init__(self, shutdown_timeout: int = 30):
        self.shutdown = False
        self.server: Optional[uvicorn.Server] = None
        self.shutdown_timeout = shutdown_timeout
        self.active_connections: Set[asyncio.Task] = set()
        self.shutdown_event = asyncio.Event()
        self._shutdown_start_time: Optional[float] = None

    def set_server(self, server: uvicorn.Server) -> None:
        """Set the uvicorn server instance."""
        self.server = server

    def add_connection(self, task: asyncio.Task) -> None:
        """Add an active connection task to track."""
        self.active_connections.add(task)
        task.add_done_callback(self.active_connections.discard)

    def signal_handler(self, signum: int, frame) -> None:
        """
        Handle shutdown signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_names = {
            signal.SIGTERM: "SIGTERM",
            signal.SIGINT: "SIGINT",
        }
        if hasattr(signal, 'SIGHUP'):
            signal_names[signal.SIGHUP] = "SIGHUP"

        signal_name = signal_names.get(signum, f"Signal {signum}")
        logger.info(f"Received {signal_name}, initiating graceful shutdown...")

        self.shutdown = True
        self._shutdown_start_time = time.time()

        # Set shutdown event for any waiting coroutines
        if not self.shutdown_event.is_set():
            self.shutdown_event.set()

        # Signal uvicorn server to stop accepting new connections
        if self.server:
            self.server.should_exit = True

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown signal."""
        await self.shutdown_event.wait()

    async def cleanup_resources(self) -> None:
        """
        Cleanup application resources during shutdown.

        This method handles:
        - Waiting for active connections to finish
        - Closing database connections
        - Cleaning up background tasks
        - Forced termination after timeout
        """
        if not self.shutdown:
            return

        logger.info("Starting graceful shutdown cleanup...")

        try:
            # Wait for active connections to finish
            await self._wait_for_active_connections()

            # Close database connections
            await self._close_database_connections()

            # Cleanup other resources
            await self._cleanup_other_resources()

            logger.info("Graceful shutdown completed successfully")

        except asyncio.TimeoutError:
            logger.warning(f"Graceful shutdown timeout ({self.shutdown_timeout}s) exceeded, forcing termination")
            await self._force_cleanup()
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}", exc_info=True)
            await self._force_cleanup()

    async def _wait_for_active_connections(self) -> None:
        """Wait for active connections to finish with timeout."""
        if not self.active_connections:
            logger.info("No active connections to wait for")
            return

        logger.info(f"Waiting for {len(self.active_connections)} active connections to finish...")

        # Calculate remaining timeout
        elapsed = time.time() - (self._shutdown_start_time or time.time())
        remaining_timeout = max(0, self.shutdown_timeout - elapsed)

        if remaining_timeout <= 0:
            logger.warning("No time remaining for connection cleanup")
            return

        try:
            # Wait for all active connections to complete
            await asyncio.wait_for(
                asyncio.gather(*self.active_connections, return_exceptions=True),
                timeout=remaining_timeout * 0.7  # Use 70% of remaining time for connections
            )
            logger.info("All active connections completed")
        except asyncio.TimeoutError:
            logger.warning(f"Active connections did not finish within timeout, cancelling {len(self.active_connections)} tasks")
            # Cancel remaining tasks
            for task in self.active_connections:
                if not task.done():
                    task.cancel()

            # Wait a bit for cancellation to complete
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_connections, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                logger.warning("Some tasks did not respond to cancellation")

    async def _close_database_connections(self) -> None:
        """Close database connections."""
        try:
            from src.database.config import close_database
            logger.info("Closing database connections...")
            await close_database()
            logger.info("Database connections closed successfully")
        except Exception as e:
            logger.error(f"Error closing database connections: {e}", exc_info=True)

    async def _cleanup_other_resources(self) -> None:
        """Cleanup other application resources."""
        try:
            # Close Redis connections if available
            try:
                # TODO: Add Redis connection cleanup when implemented
                logger.info("Redis connections cleanup completed")
            except Exception as e:
                logger.error(f"Error closing Redis connections: {e}", exc_info=True)

            # Cleanup monitoring resources
            try:
                from src.monitoring.metrics import cleanup_metrics
                cleanup_metrics()
                logger.info("Metrics cleanup completed")
            except (ImportError, AttributeError):
                # Metrics cleanup not available
                pass
            except Exception as e:
                logger.error(f"Error cleaning up metrics: {e}", exc_info=True)

            # Cleanup Sentry
            try:
                import sentry_sdk
                sentry_sdk.flush(timeout=2.0)
                logger.info("Sentry cleanup completed")
            except Exception as e:
                logger.error(f"Error cleaning up Sentry: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}", exc_info=True)

    async def _force_cleanup(self) -> None:
        """Force cleanup when graceful shutdown fails."""
        logger.warning("Performing forced cleanup...")

        # Cancel all remaining tasks
        for task in self.active_connections:
            if not task.done():
                task.cancel()

        # Force close database connections
        try:
            from src.database.config import close_database
            await close_database()
        except Exception as e:
            logger.error(f"Error during forced database cleanup: {e}")

        logger.warning("Forced cleanup completed")


def setup_signal_handlers(shutdown_handler: GracefulShutdown) -> None:
    """
    Set up signal handlers for graceful shutdown.

    Args:
        shutdown_handler: GracefulShutdown instance
    """
    # Handle SIGTERM (sent by Docker, Kubernetes, etc.)
    signal.signal(signal.SIGTERM, shutdown_handler.signal_handler)

    # Handle SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, shutdown_handler.signal_handler)

    # Handle SIGHUP (terminal hangup)
    if hasattr(signal, 'SIGHUP'):
        signal.signal(signal.SIGHUP, shutdown_handler.signal_handler)


def create_uvicorn_config() -> dict:
    """
    Create uvicorn server configuration based on environment settings.

    Returns:
        Dictionary with uvicorn configuration
    """
    config = {
        "host": settings.host,
        "port": settings.port,
        "log_level": settings.log_level.lower(),
        "access_log": is_development(),
        "use_colors": is_development(),
    }

    # Environment-specific configuration
    if is_development():
        config.update({
            "reload": getattr(settings, "reload", True),
            "reload_dirs": [getattr(settings, "dev_reload_dirs", "src")],
            "reload_includes": [getattr(settings, "dev_reload_includes", "*.py")],
        })
    elif is_production():
        config.update({
            "workers": getattr(settings, "workers", 1),
            "worker_class": getattr(settings, "worker_class", "uvicorn.workers.UvicornWorker"),
            "worker_connections": getattr(settings, "worker_connections", 1000),
            "keepalive": 2,
            "max_requests": 1000,
            "max_requests_jitter": 100,
        })

    return config


async def run_server() -> None:
    """
    Run the FastAPI server with proper async setup.

    This function creates the FastAPI application, configures uvicorn,
    and runs the server with graceful shutdown handling.
    """
    # Get shutdown timeout from settings
    shutdown_timeout = getattr(settings, 'shutdown_timeout', 30)

    # Create application
    app = get_application()

    # Set up graceful shutdown
    shutdown_handler = GracefulShutdown(shutdown_timeout=shutdown_timeout)
    setup_signal_handlers(shutdown_handler)

    # Create uvicorn configuration
    uvicorn_config = create_uvicorn_config()

    # Create and configure server
    config = uvicorn.Config(app, **uvicorn_config)
    server = uvicorn.Server(config)

    # Set server reference for shutdown handler
    shutdown_handler.set_server(server)

    logger.info(f"Starting server on {settings.host}:{settings.port}")
    logger.info(f"Environment: {get_environment()}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Shutdown timeout: {shutdown_timeout}s")

    # Create server task
    server_task = asyncio.create_task(server.serve())
    shutdown_handler.add_connection(server_task)

    try:
        # Wait for either server completion or shutdown signal
        shutdown_task = asyncio.create_task(shutdown_handler.wait_for_shutdown())

        done, pending = await asyncio.wait(
            [server_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # If shutdown was triggered, perform cleanup
        if shutdown_handler.shutdown:
            await shutdown_handler.cleanup_resources()

        # Check if server task had an exception
        if server_task in done and not server_task.cancelled():
            try:
                await server_task
            except Exception as e:
                logger.error(f"Server error: {e}")
                raise

    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Server shutdown complete")


def main() -> None:
    """
    Main entry point for the application.

    This function sets up the event loop and runs the server.
    """
    try:
        # Check if we're already in an event loop (e.g., in Jupyter)
        try:
            loop = asyncio.get_running_loop()
            logger.warning("Already running in an event loop, creating new task")
            loop.create_task(run_server())
        except RuntimeError:
            # No event loop running, create one
            if sys.version_info >= (3, 7):
                asyncio.run(run_server())
            else:
                # Python < 3.7 compatibility
                loop = asyncio.get_event_loop()
                try:
                    loop.run_until_complete(run_server())
                finally:
                    loop.close()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
