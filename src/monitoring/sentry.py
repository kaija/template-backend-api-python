"""
Sentry integration for error tracking and monitoring.

This module provides Sentry configuration and integration for comprehensive
error tracking with environment tagging and context.
"""

import logging
from typing import Any, Dict, Optional

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration

from src.config.settings import settings, is_development, is_production
from src.utils.logging import get_logger

logger = get_logger(__name__)


def configure_sentry() -> None:
    """
    Configure Sentry for error tracking.

    This function initializes Sentry with appropriate configuration
    for the current environment.
    """
    # Get Sentry configuration
    sentry_dsn = getattr(settings, "sentry_dsn", None)

    if not sentry_dsn:
        logger.info("Sentry DSN not configured, skipping Sentry initialization")
        return

    # Environment-specific configuration
    if is_development():
        # In development, capture fewer events and include more debug info
        sample_rate = 1.0
        traces_sample_rate = 1.0
        debug = True
        attach_stacktrace = True
        send_default_pii = True  # Include PII for debugging
    elif is_production():
        # In production, sample events and exclude PII
        sample_rate = getattr(settings, "sentry_sample_rate", 0.1)
        traces_sample_rate = getattr(settings, "sentry_traces_sample_rate", 0.1)
        debug = False
        attach_stacktrace = False
        send_default_pii = False  # Don't include PII in production
    else:
        # Staging/testing environment
        sample_rate = getattr(settings, "sentry_sample_rate", 0.5)
        traces_sample_rate = getattr(settings, "sentry_traces_sample_rate", 0.5)
        debug = False
        attach_stacktrace = True
        send_default_pii = False

    # Configure integrations
    integrations = [
        # FastAPI integration
        FastApiIntegration(
            auto_enabling_integrations=True,
            transaction_style="endpoint",
            failed_request_status_codes=[400, 401, 403, 404, 405, 500, 502, 503, 504],
        ),

        # SQLAlchemy integration
        SqlalchemyIntegration(),

        # Redis integration
        RedisIntegration(),

        # Standard library integration
        StdlibIntegration(),

        # Logging integration
        LoggingIntegration(
            level=logging.INFO,  # Capture info and above
            event_level=logging.ERROR,  # Send errors as events
        ),
    ]

    # Initialize Sentry
    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=getattr(settings, "env", "development"),
            release=getattr(settings, "version", "0.1.0"),
            sample_rate=sample_rate,
            traces_sample_rate=traces_sample_rate,
            debug=debug,
            attach_stacktrace=attach_stacktrace,
            send_default_pii=send_default_pii,
            integrations=integrations,
            before_send=before_send_filter,
            before_send_transaction=before_send_transaction_filter,
        )

        # Set global tags
        sentry_sdk.set_tag("service", getattr(settings, "app_name", "generic-api-framework"))
        sentry_sdk.set_tag("version", getattr(settings, "version", "0.1.0"))
        sentry_sdk.set_tag("environment", getattr(settings, "env", "development"))

        # Set global context
        sentry_sdk.set_context("app", {
            "name": getattr(settings, "app_name", "generic-api-framework"),
            "version": getattr(settings, "version", "0.1.0"),
            "environment": getattr(settings, "env", "development"),
        })

        logger.info(f"Sentry initialized for environment: {getattr(settings, 'env', 'development')}")

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter events before sending to Sentry.

    This function allows filtering out certain events or modifying
    them before they are sent to Sentry.

    Args:
        event: Sentry event data
        hint: Additional context about the event

    Returns:
        Modified event or None to drop the event
    """
    try:
        # Filter out health check errors
        if "request" in event and event["request"].get("url"):
            url = event["request"]["url"]
            if any(path in url for path in ["/healthz", "/readyz", "/metrics"]):
                return None

        # Filter out certain exception types in development
        if is_development():
            exc_info = hint.get("exc_info")
            if exc_info:
                exc_type = exc_info[0]
                if exc_type and exc_type.__name__ in ["KeyboardInterrupt", "SystemExit"]:
                    return None

        # Add correlation ID if available
        if "extra" in event and "correlation_id" in event["extra"]:
            event["tags"] = event.get("tags", {})
            event["tags"]["correlation_id"] = event["extra"]["correlation_id"]

        # Sanitize sensitive data
        event = sanitize_event_data(event)

        return event

    except Exception as e:
        logger.error(f"Error in Sentry before_send filter: {e}")
        return event


def before_send_transaction_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter transaction events before sending to Sentry.

    Args:
        event: Sentry transaction event data
        hint: Additional context about the event

    Returns:
        Modified event or None to drop the event
    """
    try:
        # Filter out health check transactions
        if "transaction" in event:
            transaction_name = event["transaction"]
            if any(path in transaction_name for path in ["/healthz", "/readyz", "/metrics"]):
                return None

        return event

    except Exception as e:
        logger.error(f"Error in Sentry before_send_transaction filter: {e}")
        return event


def sanitize_event_data(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive data from Sentry event.

    Args:
        event: Sentry event data

    Returns:
        Sanitized event data
    """
    try:
        # Sanitize request data
        if "request" in event:
            request_data = event["request"]

            # Sanitize headers
            if "headers" in request_data:
                request_data["headers"] = sanitize_headers(request_data["headers"])

            # Sanitize query parameters
            if "query_string" in request_data:
                request_data["query_string"] = sanitize_query_string(request_data["query_string"])

            # Sanitize cookies
            if "cookies" in request_data:
                request_data["cookies"] = "***MASKED***"

            # Sanitize form data
            if "data" in request_data and isinstance(request_data["data"], dict):
                request_data["data"] = sanitize_form_data(request_data["data"])

        # Sanitize extra data
        if "extra" in event:
            event["extra"] = sanitize_extra_data(event["extra"])

        return event

    except Exception as e:
        logger.error(f"Error sanitizing Sentry event data: {e}")
        return event


def sanitize_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive headers.

    Args:
        headers: Request headers

    Returns:
        Sanitized headers
    """
    sensitive_headers = {
        "authorization",
        "x-api-key",
        "cookie",
        "x-auth-token",
        "x-access-token",
        "x-refresh-token",
    }

    sanitized = {}
    for key, value in headers.items():
        if key.lower() in sensitive_headers:
            sanitized[key] = "***MASKED***"
        else:
            sanitized[key] = value

    return sanitized


def sanitize_query_string(query_string: str) -> str:
    """
    Sanitize sensitive query parameters.

    Args:
        query_string: Query string

    Returns:
        Sanitized query string
    """
    sensitive_params = {"token", "api_key", "password", "secret"}

    if not query_string:
        return query_string

    # Simple sanitization - replace sensitive parameter values
    for param in sensitive_params:
        if f"{param}=" in query_string.lower():
            # This is a simple approach - in production you might want more sophisticated parsing
            return "***CONTAINS_SENSITIVE_DATA***"

    return query_string


def sanitize_form_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive form data.

    Args:
        data: Form data

    Returns:
        Sanitized form data
    """
    sensitive_fields = {
        "password",
        "token",
        "api_key",
        "secret",
        "credit_card",
        "ssn",
    }

    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_fields:
            sanitized[key] = "***MASKED***"
        else:
            sanitized[key] = value

    return sanitized


def sanitize_extra_data(extra: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive extra data.

    Args:
        extra: Extra event data

    Returns:
        Sanitized extra data
    """
    # Keep correlation_id and other non-sensitive data
    safe_keys = {
        "correlation_id",
        "user_id",
        "username",
        "method",
        "path",
        "status_code",
        "response_time_ms",
    }

    sanitized = {}
    for key, value in extra.items():
        if key in safe_keys:
            sanitized[key] = value
        elif isinstance(value, (str, int, float, bool)):
            # Keep simple values but check for sensitive patterns
            if not contains_sensitive_pattern(str(value)):
                sanitized[key] = value
            else:
                sanitized[key] = "***MASKED***"
        else:
            # For complex objects, be conservative and mask them
            sanitized[key] = "***MASKED***"

    return sanitized


def contains_sensitive_pattern(value: str) -> bool:
    """
    Check if value contains sensitive patterns.

    Args:
        value: Value to check

    Returns:
        True if value contains sensitive patterns
    """
    sensitive_patterns = [
        "bearer ",
        "basic ",
        "token=",
        "key=",
        "password=",
        "secret=",
        "jwt",
    ]

    value_lower = value.lower()
    return any(pattern in value_lower for pattern in sensitive_patterns)


def capture_exception(
    exception: Exception,
    correlation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Capture exception with additional context.

    Args:
        exception: Exception to capture
        correlation_id: Request correlation ID
        user_id: User ID if available
        extra_context: Additional context data
    """
    try:
        with sentry_sdk.push_scope() as scope:
            # Set correlation ID
            if correlation_id:
                scope.set_tag("correlation_id", correlation_id)
                scope.set_context("correlation", {"id": correlation_id})

            # Set user context
            if user_id:
                scope.set_user({"id": user_id})

            # Set extra context
            if extra_context:
                for key, value in extra_context.items():
                    scope.set_extra(key, value)

            # Capture the exception
            sentry_sdk.capture_exception(exception)

    except Exception as e:
        logger.error(f"Error capturing exception in Sentry: {e}")


def capture_message(
    message: str,
    level: str = "info",
    correlation_id: Optional[str] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Capture message with additional context.

    Args:
        message: Message to capture
        level: Message level (debug, info, warning, error, fatal)
        correlation_id: Request correlation ID
        extra_context: Additional context data
    """
    try:
        with sentry_sdk.push_scope() as scope:
            # Set correlation ID
            if correlation_id:
                scope.set_tag("correlation_id", correlation_id)

            # Set extra context
            if extra_context:
                for key, value in extra_context.items():
                    scope.set_extra(key, value)

            # Capture the message
            sentry_sdk.capture_message(message, level=level)

    except Exception as e:
        logger.error(f"Error capturing message in Sentry: {e}")


def set_user_context(user_id: str, username: Optional[str] = None, email: Optional[str] = None) -> None:
    """
    Set user context for Sentry.

    Args:
        user_id: User ID
        username: Username (optional)
        email: User email (optional, will be masked in production)
    """
    try:
        user_data = {"id": user_id}

        if username:
            user_data["username"] = username

        # Only include email in development
        if email and is_development():
            user_data["email"] = email

        sentry_sdk.set_user(user_data)

    except Exception as e:
        logger.error(f"Error setting user context in Sentry: {e}")


def clear_user_context() -> None:
    """Clear user context from Sentry."""
    try:
        sentry_sdk.set_user(None)
    except Exception as e:
        logger.error(f"Error clearing user context in Sentry: {e}")


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Add breadcrumb to Sentry.

    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Breadcrumb level
        data: Additional data
    """
    try:
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )
    except Exception as e:
        logger.error(f"Error adding breadcrumb to Sentry: {e}")


# Initialize Sentry when module is imported
configure_sentry()
