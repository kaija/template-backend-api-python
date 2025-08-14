"""
Prometheus metrics for application monitoring.

This module defines and manages Prometheus metrics for comprehensive
application monitoring including HTTP requests, database operations,
external API calls, and custom business metrics.
"""

import time
from typing import Dict, Optional

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Create a custom registry for our metrics
REGISTRY = CollectorRegistry()

# Application info metric
app_info = Info(
    "app_info",
    "Application information",
    registry=REGISTRY
)

# Set application info
app_info.info({
    "name": getattr(settings, "app_name", "production-api-framework"),
    "version": getattr(settings, "version", "0.1.0"),
    "environment": getattr(settings, "env", "development"),
})

# HTTP request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0),
    registry=REGISTRY
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=(64, 256, 1024, 4096, 16384, 65536, 262144, 1048576),
    registry=REGISTRY
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=(64, 256, 1024, 4096, 16384, 65536, 262144, 1048576),
    registry=REGISTRY
)

# Authentication metrics
auth_attempts_total = Counter(
    "auth_attempts_total",
    "Total number of authentication attempts",
    ["method", "outcome"],
    registry=REGISTRY
)

auth_tokens_active = Gauge(
    "auth_tokens_active",
    "Number of active authentication tokens",
    registry=REGISTRY
)

# Database metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections",
    registry=REGISTRY
)

db_connections_total = Counter(
    "db_connections_total",
    "Total number of database connections created",
    registry=REGISTRY
)

db_queries_total = Counter(
    "db_queries_total",
    "Total number of database queries",
    ["operation", "table", "status"],
    registry=REGISTRY
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY
)

# External API metrics
external_api_requests_total = Counter(
    "external_api_requests_total",
    "Total number of external API requests",
    ["service", "method", "status_code"],
    registry=REGISTRY
)

external_api_request_duration_seconds = Histogram(
    "external_api_request_duration_seconds",
    "External API request duration in seconds",
    ["service", "method"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY
)

# Cache metrics
cache_operations_total = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    ["operation", "outcome"],
    registry=REGISTRY
)

cache_hit_ratio = Gauge(
    "cache_hit_ratio",
    "Cache hit ratio (0-1)",
    registry=REGISTRY
)

# Business metrics
active_users = Gauge(
    "active_users",
    "Number of active users",
    registry=REGISTRY
)

business_operations_total = Counter(
    "business_operations_total",
    "Total number of business operations",
    ["operation", "outcome"],
    registry=REGISTRY
)

# Error metrics
errors_total = Counter(
    "errors_total",
    "Total number of errors",
    ["error_type", "component"],
    registry=REGISTRY
)

# Resource usage metrics
memory_usage_bytes = Gauge(
    "memory_usage_bytes",
    "Memory usage in bytes",
    registry=REGISTRY
)

cpu_usage_percent = Gauge(
    "cpu_usage_percent",
    "CPU usage percentage",
    registry=REGISTRY
)


class MetricsCollector:
    """
    Metrics collector for tracking application metrics.

    This class provides methods for tracking various application metrics
    and updating Prometheus counters, histograms, and gauges.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.logger = get_logger(__name__)
        self._cache_stats = {"hits": 0, "misses": 0}

    def track_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
    ) -> None:
        """
        Track HTTP request metrics.

        Args:
            method: HTTP method
            endpoint: Request endpoint
            status_code: Response status code
            duration_seconds: Request duration in seconds
            request_size: Request size in bytes
            response_size: Response size in bytes
        """
        try:
            # Track request count
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()

            # Track request duration
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration_seconds)

            # Track request size
            if request_size is not None:
                http_request_size_bytes.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(request_size)

            # Track response size
            if response_size is not None:
                http_response_size_bytes.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(response_size)

        except Exception as e:
            self.logger.error(f"Error tracking HTTP request metrics: {e}")

    def track_auth_attempt(self, method: str, outcome: str) -> None:
        """
        Track authentication attempt.

        Args:
            method: Authentication method (jwt, api_key, oauth2)
            outcome: Authentication outcome (success, failure)
        """
        try:
            auth_attempts_total.labels(method=method, outcome=outcome).inc()
        except Exception as e:
            self.logger.error(f"Error tracking auth attempt metrics: {e}")

    def update_active_tokens(self, count: int) -> None:
        """
        Update active tokens count.

        Args:
            count: Number of active tokens
        """
        try:
            auth_tokens_active.set(count)
        except Exception as e:
            self.logger.error(f"Error updating active tokens metrics: {e}")

    def track_db_query(
        self,
        operation: str,
        table: str,
        duration_seconds: float,
        status: str = "success"
    ) -> None:
        """
        Track database query metrics.

        Args:
            operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
            table: Table name
            duration_seconds: Query duration in seconds
            status: Query status (success, error)
        """
        try:
            db_queries_total.labels(
                operation=operation,
                table=table,
                status=status
            ).inc()

            db_query_duration_seconds.labels(
                operation=operation,
                table=table
            ).observe(duration_seconds)

        except Exception as e:
            self.logger.error(f"Error tracking database query metrics: {e}")

    def update_db_connections(self, active_count: int, total_created: Optional[int] = None) -> None:
        """
        Update database connection metrics.

        Args:
            active_count: Number of active connections
            total_created: Total connections created (optional)
        """
        try:
            db_connections_active.set(active_count)

            if total_created is not None:
                # This would typically be called once with the total
                db_connections_total._value._value = total_created

        except Exception as e:
            self.logger.error(f"Error updating database connection metrics: {e}")

    def track_external_api_request(
        self,
        service: str,
        method: str,
        status_code: int,
        duration_seconds: float
    ) -> None:
        """
        Track external API request metrics.

        Args:
            service: External service name
            method: HTTP method
            status_code: Response status code
            duration_seconds: Request duration in seconds
        """
        try:
            external_api_requests_total.labels(
                service=service,
                method=method,
                status_code=status_code
            ).inc()

            external_api_request_duration_seconds.labels(
                service=service,
                method=method
            ).observe(duration_seconds)

        except Exception as e:
            self.logger.error(f"Error tracking external API request metrics: {e}")

    def track_cache_operation(self, operation: str, outcome: str) -> None:
        """
        Track cache operation metrics.

        Args:
            operation: Cache operation (get, set, delete)
            outcome: Operation outcome (hit, miss, success, error)
        """
        try:
            cache_operations_total.labels(
                operation=operation,
                outcome=outcome
            ).inc()

            # Update cache hit ratio
            if operation == "get":
                if outcome == "hit":
                    self._cache_stats["hits"] += 1
                elif outcome == "miss":
                    self._cache_stats["misses"] += 1

                total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
                if total_requests > 0:
                    hit_ratio = self._cache_stats["hits"] / total_requests
                    cache_hit_ratio.set(hit_ratio)

        except Exception as e:
            self.logger.error(f"Error tracking cache operation metrics: {e}")

    def update_active_users(self, count: int) -> None:
        """
        Update active users count.

        Args:
            count: Number of active users
        """
        try:
            active_users.set(count)
        except Exception as e:
            self.logger.error(f"Error updating active users metrics: {e}")

    def track_business_operation(self, operation: str, outcome: str) -> None:
        """
        Track business operation metrics.

        Args:
            operation: Business operation name
            outcome: Operation outcome (success, failure)
        """
        try:
            business_operations_total.labels(
                operation=operation,
                outcome=outcome
            ).inc()
        except Exception as e:
            self.logger.error(f"Error tracking business operation metrics: {e}")

    def track_error(self, error_type: str, component: str) -> None:
        """
        Track error metrics.

        Args:
            error_type: Type of error (validation, authentication, database, etc.)
            component: Component where error occurred
        """
        try:
            errors_total.labels(
                error_type=error_type,
                component=component
            ).inc()
        except Exception as e:
            self.logger.error(f"Error tracking error metrics: {e}")

    def update_resource_usage(self, memory_bytes: Optional[int] = None, cpu_percent: Optional[float] = None) -> None:
        """
        Update resource usage metrics.

        Args:
            memory_bytes: Memory usage in bytes
            cpu_percent: CPU usage percentage
        """
        try:
            if memory_bytes is not None:
                memory_usage_bytes.set(memory_bytes)

            if cpu_percent is not None:
                cpu_usage_percent.set(cpu_percent)

        except Exception as e:
            self.logger.error(f"Error updating resource usage metrics: {e}")


# Global metrics collector instance
metrics_collector = MetricsCollector()


def get_metrics_data() -> str:
    """
    Get Prometheus metrics data in text format.

    Returns:
        Prometheus metrics data as string
    """
    return generate_latest(REGISTRY).decode("utf-8")


def get_metrics_content_type() -> str:
    """
    Get Prometheus metrics content type.

    Returns:
        Content type for Prometheus metrics
    """
    return CONTENT_TYPE_LATEST


class MetricsTimer:
    """
    Context manager for timing operations and updating metrics.

    Usage:
        with MetricsTimer() as timer:
            # Do some operation
            pass

        # Timer automatically tracks duration
        metrics_collector.track_db_query("SELECT", "users", timer.duration)
    """

    def __init__(self):
        """Initialize metrics timer."""
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


# Convenience functions for common metrics operations
def track_http_request(method: str, endpoint: str, status_code: int, duration_seconds: float) -> None:
    """Track HTTP request metrics."""
    metrics_collector.track_http_request(method, endpoint, status_code, duration_seconds)


def track_auth_attempt(method: str, outcome: str) -> None:
    """Track authentication attempt."""
    metrics_collector.track_auth_attempt(method, outcome)


def track_db_query(operation: str, table: str, duration_seconds: float, status: str = "success") -> None:
    """Track database query metrics."""
    metrics_collector.track_db_query(operation, table, duration_seconds, status)


def track_error(error_type: str, component: str) -> None:
    """Track error metrics."""
    metrics_collector.track_error(error_type, component)


def cleanup_metrics() -> None:
    """
    Cleanup metrics resources during application shutdown.

    This function performs any necessary cleanup for the metrics system,
    such as flushing pending metrics or closing connections.
    """
    try:
        logger.info("Cleaning up metrics resources...")

        # Clear the registry if needed (optional, usually not necessary)
        # REGISTRY.clear()

        # Reset cache stats
        metrics_collector._cache_stats = {"hits": 0, "misses": 0}

        logger.info("Metrics cleanup completed")

    except Exception as e:
        logger.error(f"Error during metrics cleanup: {e}", exc_info=True)
