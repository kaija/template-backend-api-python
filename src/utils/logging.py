"""
Structured logging utilities for the application.

This module provides structured JSON logging with correlation ID support,
sensitive data masking, and proper formatting for observability.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Union

import structlog
from structlog.types import EventDict, Processor

from src.config.settings import settings, is_development, is_production


class CorrelationIDProcessor:
    """
    Processor to add correlation ID to log entries.
    
    This processor extracts correlation ID from context variables
    and adds it to every log entry.
    """
    
    def __call__(self, logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
        """
        Process log entry and add correlation ID.
        
        Args:
            logger: Logger instance
            method_name: Log method name
            event_dict: Log event dictionary
            
        Returns:
            Updated event dictionary with correlation ID
        """
        # Try to get correlation ID from various sources
        correlation_id = event_dict.get("correlation_id")
        
        if not correlation_id:
            # Try to get from structlog context variables
            try:
                correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
            except (AttributeError, TypeError):
                # Fallback if contextvars not available
                pass
        
        if correlation_id:
            event_dict["correlation_id"] = correlation_id
        
        return event_dict


class SensitiveDataProcessor:
    """
    Processor to mask sensitive data in log entries.
    
    This processor identifies and masks sensitive fields to prevent
    accidental logging of secrets, passwords, or PII.
    """
    
    def __init__(self):
        """Initialize sensitive data processor."""
        self.sensitive_keys = {
            "password",
            "passwd",
            "secret",
            "token",
            "key",
            "authorization",
            "auth",
            "api_key",
            "access_token",
            "refresh_token",
            "jwt",
            "bearer",
            "cookie",
            "session",
            "ssn",
            "social_security",
            "credit_card",
            "card_number",
            "cvv",
            "pin",
            "email",  # Mask email for privacy
            "phone",
            "address",
        }
        
        self.mask_value = "***MASKED***"
    
    def __call__(self, logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
        """
        Process log entry and mask sensitive data.
        
        Args:
            logger: Logger instance
            method_name: Log method name
            event_dict: Log event dictionary
            
        Returns:
            Updated event dictionary with masked sensitive data
        """
        return self._mask_dict(event_dict)
    
    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively mask sensitive data in dictionary.
        
        Args:
            data: Dictionary to process
            
        Returns:
            Dictionary with sensitive values masked
        """
        if not isinstance(data, dict):
            return data
        
        masked_data = {}
        
        for key, value in data.items():
            if self._is_sensitive_key(key):
                masked_data[key] = self.mask_value
            elif isinstance(value, dict):
                masked_data[key] = self._mask_dict(value)
            elif isinstance(value, list):
                masked_data[key] = self._mask_list(value)
            else:
                masked_data[key] = value
        
        return masked_data
    
    def _mask_list(self, data: list) -> list:
        """
        Recursively mask sensitive data in list.
        
        Args:
            data: List to process
            
        Returns:
            List with sensitive values masked
        """
        masked_list = []
        
        for item in data:
            if isinstance(item, dict):
                masked_list.append(self._mask_dict(item))
            elif isinstance(item, list):
                masked_list.append(self._mask_list(item))
            else:
                masked_list.append(item)
        
        return masked_list
    
    def _is_sensitive_key(self, key: str) -> bool:
        """
        Check if key contains sensitive data.
        
        Args:
            key: Key to check
            
        Returns:
            True if key is sensitive
        """
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.sensitive_keys)


class TimestampProcessor:
    """
    Processor to add ISO timestamp to log entries.
    
    This processor adds a consistent timestamp format to all log entries.
    """
    
    def __call__(self, logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
        """
        Process log entry and add timestamp.
        
        Args:
            logger: Logger instance
            method_name: Log method name
            event_dict: Log event dictionary
            
        Returns:
            Updated event dictionary with timestamp
        """
        event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
        return event_dict


class LevelProcessor:
    """
    Processor to normalize log level names.
    
    This processor ensures consistent log level naming across all entries.
    """
    
    def __call__(self, logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
        """
        Process log entry and normalize level.
        
        Args:
            logger: Logger instance
            method_name: Log method name
            event_dict: Log event dictionary
            
        Returns:
            Updated event dictionary with normalized level
        """
        # Map structlog method names to standard levels
        level_mapping = {
            "debug": "DEBUG",
            "info": "INFO",
            "warning": "WARNING",
            "warn": "WARNING",
            "error": "ERROR",
            "critical": "CRITICAL",
            "exception": "ERROR",
        }
        
        event_dict["level"] = level_mapping.get(method_name, method_name.upper())
        return event_dict


class ServiceInfoProcessor:
    """
    Processor to add service information to log entries.
    
    This processor adds consistent service metadata to all log entries.
    """
    
    def __init__(self):
        """Initialize service info processor."""
        self.service_info = {
            "service": getattr(settings, "app_name", "production-api-framework"),
            "version": getattr(settings, "version", "0.1.0"),
            "environment": settings.env,
        }
    
    def __call__(self, logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
        """
        Process log entry and add service info.
        
        Args:
            logger: Logger instance
            method_name: Log method name
            event_dict: Log event dictionary
            
        Returns:
            Updated event dictionary with service info
        """
        event_dict.update(self.service_info)
        return event_dict


def configure_structlog() -> None:
    """
    Configure structlog for structured JSON logging.
    
    This function sets up structlog with appropriate processors
    for different environments.
    """
    # Common processors for all environments
    processors = [
        # Add service information
        ServiceInfoProcessor(),
        
        # Add correlation ID
        CorrelationIDProcessor(),
        
        # Add timestamp
        TimestampProcessor(),
        
        # Normalize log level
        LevelProcessor(),
        
        # Add logger name
        structlog.stdlib.add_logger_name,
        
        # Add log level
        structlog.stdlib.add_log_level,
        
        # Position arguments
        structlog.stdlib.PositionalArgumentsFormatter(),
        
        # Stack info
        structlog.processors.StackInfoRenderer(),
        
        # Format exception
        structlog.processors.format_exc_info,
        
        # Unicode decode errors
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add sensitive data masking (except in development for debugging)
    if not is_development() or getattr(settings, "mask_sensitive_logs", True):
        processors.append(SensitiveDataProcessor())
    
    # Environment-specific configuration
    if is_development():
        # Development: Pretty console output
        processors.extend([
            structlog.dev.ConsoleRenderer(colors=True)
        ])
        
        # Configure standard library logging for development
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
        )
    else:
        # Production/Staging: JSON output
        processors.extend([
            structlog.processors.JSONRenderer()
        ])
        
        # Configure standard library logging for production
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=getattr(logging, settings.log_level.upper(), logging.INFO),
        )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str) -> None:
    """
    Set correlation ID in structlog context.
    
    Args:
        correlation_id: Correlation ID to set
    """
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from structlog context."""
    structlog.contextvars.unbind_contextvars("correlation_id")


def log_request(
    method: str,
    path: str,
    query_params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, Any]] = None,
    client_ip: Optional[str] = None,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log HTTP request with structured data.
    
    Args:
        method: HTTP method
        path: Request path
        query_params: Query parameters
        headers: Request headers
        client_ip: Client IP address
        user_id: User ID if authenticated
        correlation_id: Request correlation ID
        **kwargs: Additional fields to log
    """
    logger = get_logger("http.request")
    
    log_data = {
        "event_type": "http_request",
        "method": method,
        "path": path,
        "correlation_id": correlation_id,
        **kwargs
    }
    
    if query_params:
        log_data["query_params"] = query_params
    
    if headers:
        log_data["headers"] = headers
    
    if client_ip:
        log_data["client_ip"] = client_ip
    
    if user_id:
        log_data["user_id"] = user_id
    
    logger.info("HTTP request", **log_data)


def log_response(
    method: str,
    path: str,
    status_code: int,
    response_time_ms: Optional[float] = None,
    response_size: Optional[int] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log HTTP response with structured data.
    
    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        response_size: Response size in bytes
        correlation_id: Request correlation ID
        **kwargs: Additional fields to log
    """
    logger = get_logger("http.response")
    
    log_data = {
        "event_type": "http_response",
        "method": method,
        "path": path,
        "status_code": status_code,
        "correlation_id": correlation_id,
        **kwargs
    }
    
    if response_time_ms is not None:
        log_data["response_time_ms"] = response_time_ms
    
    if response_size is not None:
        log_data["response_size"] = response_size
    
    # Determine log level based on status code
    if status_code >= 500:
        logger.error("HTTP response", **log_data)
    elif status_code >= 400:
        logger.warning("HTTP response", **log_data)
    else:
        logger.info("HTTP response", **log_data)


def log_database_operation(
    operation: str,
    table: Optional[str] = None,
    duration_ms: Optional[float] = None,
    rows_affected: Optional[int] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log database operation with structured data.
    
    Args:
        operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
        duration_ms: Operation duration in milliseconds
        rows_affected: Number of rows affected
        correlation_id: Request correlation ID
        **kwargs: Additional fields to log
    """
    logger = get_logger("database")
    
    log_data = {
        "event_type": "database_operation",
        "operation": operation,
        "correlation_id": correlation_id,
        **kwargs
    }
    
    if table:
        log_data["table"] = table
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    
    if rows_affected is not None:
        log_data["rows_affected"] = rows_affected
    
    logger.info("Database operation", **log_data)


def log_external_api_call(
    service: str,
    method: str,
    url: str,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    correlation_id: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log external API call with structured data.
    
    Args:
        service: External service name
        method: HTTP method
        url: Request URL
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        correlation_id: Request correlation ID
        **kwargs: Additional fields to log
    """
    logger = get_logger("external_api")
    
    log_data = {
        "event_type": "external_api_call",
        "service": service,
        "method": method,
        "url": url,
        "correlation_id": correlation_id,
        **kwargs
    }
    
    if status_code is not None:
        log_data["status_code"] = status_code
    
    if duration_ms is not None:
        log_data["duration_ms"] = duration_ms
    
    # Determine log level based on status code
    if status_code and status_code >= 500:
        logger.error("External API call", **log_data)
    elif status_code and status_code >= 400:
        logger.warning("External API call", **log_data)
    else:
        logger.info("External API call", **log_data)


# Initialize structlog when module is imported
configure_structlog()