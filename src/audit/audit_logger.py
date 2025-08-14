"""
Audit logging system for tracking security events and data changes.

This module provides comprehensive audit logging capabilities with
structured logging, correlation IDs, and security event detection.
"""

import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from pathlib import Path

# Context variable for correlation ID tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class AuditEventType(Enum):
    """Audit event types for categorization."""

    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password.change"
    PASSWORD_RESET_REQUEST = "auth.password.reset.request"
    PASSWORD_RESET_SUCCESS = "auth.password.reset.success"
    EMAIL_VERIFICATION = "auth.email.verification"
    ACCOUNT_LOCKED = "auth.account.locked"
    ACCOUNT_UNLOCKED = "auth.account.unlocked"

    # API Key events
    API_KEY_CREATED = "api.key.created"
    API_KEY_USED = "api.key.used"
    API_KEY_REVOKED = "api.key.revoked"
    API_KEY_EXPIRED = "api.key.expired"

    # Data modification events
    USER_CREATED = "data.user.created"
    USER_UPDATED = "data.user.updated"
    USER_DELETED = "data.user.deleted"
    USER_ROLE_CHANGED = "data.user.role.changed"
    USER_STATUS_CHANGED = "data.user.status.changed"

    # Administrative events
    ADMIN_LOGIN = "admin.login"
    ADMIN_ACTION = "admin.action"
    SYSTEM_CONFIG_CHANGED = "admin.config.changed"
    BULK_OPERATION = "admin.bulk.operation"

    # Security events
    SUSPICIOUS_ACTIVITY = "security.suspicious.activity"
    RATE_LIMIT_EXCEEDED = "security.rate.limit.exceeded"
    UNAUTHORIZED_ACCESS = "security.unauthorized.access"
    PERMISSION_DENIED = "security.permission.denied"
    INVALID_TOKEN = "security.token.invalid"
    BRUTE_FORCE_ATTEMPT = "security.brute.force"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    DATABASE_CONNECTION = "system.database.connection"
    HEALTH_CHECK = "system.health.check"
    ERROR_OCCURRED = "system.error"


class AuditSeverity(Enum):
    """Audit event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    Structured audit event data.

    Represents a single audit event with all relevant metadata.
    """

    # Core event information
    event_type: AuditEventType
    severity: AuditSeverity
    message: str
    timestamp: datetime

    # Request context
    correlation_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None

    # User context
    user_id: Optional[str] = None
    username: Optional[str] = None
    user_role: Optional[str] = None

    # Network context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Resource context
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None

    # Additional data
    metadata: Optional[Dict[str, Any]] = None

    # Security context
    risk_score: Optional[int] = None
    tags: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary for logging."""
        data = asdict(self)

        # Convert enum values to strings
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value

        # Convert timestamp to ISO format
        if isinstance(self.timestamp, (int, float)):
            # Convert Unix timestamp to datetime then to ISO format
            from datetime import datetime
            data['timestamp'] = datetime.fromtimestamp(self.timestamp).isoformat()
        else:
            # Assume it's already a datetime object
            data['timestamp'] = self.timestamp.isoformat()

        # Remove None values to keep logs clean
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Main audit logging class.

    Provides methods for logging various types of audit events with
    automatic context enrichment and structured formatting.
    """

    def __init__(
        self,
        logger_name: str = "audit",
        log_level: int = logging.INFO,
        enable_console: bool = True,
        enable_file: bool = True,
        log_file_path: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ):
        """
        Initialize audit logger.

        Args:
            logger_name: Name of the logger
            log_level: Logging level
            enable_console: Whether to log to console
            enable_file: Whether to log to file
            log_file_path: Path to log file
            max_file_size: Maximum log file size in bytes
            backup_count: Number of backup files to keep
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers(
                enable_console, enable_file, log_file_path,
                max_file_size, backup_count
            )

    def _setup_handlers(
        self,
        enable_console: bool,
        enable_file: bool,
        log_file_path: Optional[str],
        max_file_size: int,
        backup_count: int,
    ) -> None:
        """Set up logging handlers."""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Console handler
        if enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler with rotation
        if enable_file:
            from logging.handlers import RotatingFileHandler

            if log_file_path is None:
                log_file_path = "logs/audit.log"

            # Ensure log directory exists
            Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_file_size,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _get_context(self) -> Dict[str, Any]:
        """Get current request context."""
        return {
            'correlation_id': correlation_id_var.get(),
            'user_id': user_id_var.get(),
            'request_id': request_id_var.get(),
        }

    def _create_event(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity,
        message: str,
        **kwargs
    ) -> AuditEvent:
        """Create audit event with context enrichment."""
        context = self._get_context()

        # Use provided user_id if available, otherwise use context
        user_id = kwargs.get('user_id') or context.get('user_id')

        # Remove user_id from kwargs to avoid duplicate parameter
        kwargs_copy = kwargs.copy()
        kwargs_copy.pop('user_id', None)

        return AuditEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            correlation_id=context.get('correlation_id'),
            user_id=user_id,
            request_id=context.get('request_id'),
            **kwargs_copy
        )

    def log_event(self, event: AuditEvent) -> None:
        """
        Log an audit event.

        Args:
            event: Audit event to log
        """
        # Convert event to structured log message
        log_data = event.to_dict()

        # Determine log level based on severity
        level_mapping = {
            AuditSeverity.LOW: logging.INFO,
            AuditSeverity.MEDIUM: logging.WARNING,
            AuditSeverity.HIGH: logging.ERROR,
            AuditSeverity.CRITICAL: logging.CRITICAL,
        }

        log_level = level_mapping.get(event.severity, logging.INFO)

        # Create extra data for logging, avoiding conflicts with reserved fields
        extra_data = {
            'audit_event': True,
            'audit_event_type': event.event_type.value,
            'audit_severity': event.severity.value,
        }

        # Add non-conflicting fields from log_data
        reserved_fields = {'message', 'asctime', 'name', 'levelname', 'levelno', 'pathname', 'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'processName', 'process'}

        for key, value in log_data.items():
            if key not in reserved_fields:
                extra_data[f'audit_{key}'] = value

        # Log the structured event
        self.logger.log(
            log_level,
            json.dumps(log_data, default=str),
            extra=extra_data
        )

    # Authentication event methods
    def log_login_success(
        self,
        user_id: str,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log successful login event."""
        event = self._create_event(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            message=f"User {username} logged in successfully",
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            action="login",
            **kwargs
        )
        self.log_event(event)

    def log_login_failure(
        self,
        username: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log failed login attempt."""
        event = self._create_event(
            event_type=AuditEventType.LOGIN_FAILURE,
            severity=AuditSeverity.MEDIUM,
            message=f"Login failed for user {username}: {reason}",
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            action="login",
            metadata={"failure_reason": reason},
            **kwargs
        )
        self.log_event(event)

    def log_logout(
        self,
        user_id: str,
        username: str,
        **kwargs
    ) -> None:
        """Log user logout event."""
        event = self._create_event(
            event_type=AuditEventType.LOGOUT,
            severity=AuditSeverity.LOW,
            message=f"User {username} logged out",
            user_id=user_id,
            username=username,
            action="logout",
            **kwargs
        )
        self.log_event(event)

    def log_password_change(
        self,
        user_id: str,
        username: str,
        **kwargs
    ) -> None:
        """Log password change event."""
        event = self._create_event(
            event_type=AuditEventType.PASSWORD_CHANGE,
            severity=AuditSeverity.MEDIUM,
            message=f"Password changed for user {username}",
            user_id=user_id,
            username=username,
            action="password_change",
            **kwargs
        )
        self.log_event(event)

    # API Key event methods
    def log_api_key_created(
        self,
        user_id: str,
        key_id: str,
        key_name: str,
        **kwargs
    ) -> None:
        """Log API key creation event."""
        event = self._create_event(
            event_type=AuditEventType.API_KEY_CREATED,
            severity=AuditSeverity.MEDIUM,
            message=f"API key '{key_name}' created",
            user_id=user_id,
            resource_type="api_key",
            resource_id=key_id,
            action="create",
            metadata={"key_name": key_name},
            **kwargs
        )
        self.log_event(event)

    def log_api_key_used(
        self,
        user_id: str,
        key_id: str,
        endpoint: str,
        ip_address: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log API key usage event."""
        event = self._create_event(
            event_type=AuditEventType.API_KEY_USED,
            severity=AuditSeverity.LOW,
            message=f"API key used to access {endpoint}",
            user_id=user_id,
            resource_type="api_key",
            resource_id=key_id,
            action="use",
            ip_address=ip_address,
            metadata={"endpoint": endpoint},
            **kwargs
        )
        self.log_event(event)

    # Data modification event methods
    def log_user_created(
        self,
        created_user_id: str,
        created_username: str,
        created_by_user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log user creation event."""
        event = self._create_event(
            event_type=AuditEventType.USER_CREATED,
            severity=AuditSeverity.MEDIUM,
            message=f"User {created_username} created",
            user_id=created_by_user_id,
            resource_type="user",
            resource_id=created_user_id,
            action="create",
            metadata={"created_username": created_username},
            **kwargs
        )
        self.log_event(event)

    def log_user_updated(
        self,
        updated_user_id: str,
        updated_username: str,
        updated_fields: List[str],
        updated_by_user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log user update event."""
        event = self._create_event(
            event_type=AuditEventType.USER_UPDATED,
            severity=AuditSeverity.MEDIUM,
            message=f"User {updated_username} updated",
            user_id=updated_by_user_id,
            resource_type="user",
            resource_id=updated_user_id,
            action="update",
            metadata={
                "updated_username": updated_username,
                "updated_fields": updated_fields
            },
            **kwargs
        )
        self.log_event(event)

    # Security event methods
    def log_suspicious_activity(
        self,
        activity_type: str,
        description: str,
        risk_score: int,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log suspicious activity event."""
        event = self._create_event(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            severity=AuditSeverity.HIGH,
            message=f"Suspicious activity detected: {description}",
            user_id=user_id,
            ip_address=ip_address,
            risk_score=risk_score,
            metadata={
                "activity_type": activity_type,
                "description": description
            },
            tags=["security", "suspicious"],
            **kwargs
        )
        self.log_event(event)

    def log_rate_limit_exceeded(
        self,
        endpoint: str,
        ip_address: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log rate limit exceeded event."""
        event = self._create_event(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            severity=AuditSeverity.MEDIUM,
            message=f"Rate limit exceeded for {endpoint}",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"endpoint": endpoint},
            tags=["security", "rate_limit"],
            **kwargs
        )
        self.log_event(event)

    def log_unauthorized_access(
        self,
        resource: str,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log unauthorized access attempt."""
        event = self._create_event(
            event_type=AuditEventType.UNAUTHORIZED_ACCESS,
            severity=AuditSeverity.HIGH,
            message=f"Unauthorized access attempt to {resource}",
            user_id=user_id,
            ip_address=ip_address,
            metadata={"resource": resource},
            tags=["security", "unauthorized"],
            **kwargs
        )
        self.log_event(event)

    # System event methods
    def log_system_startup(self, **kwargs) -> None:
        """Log system startup event."""
        event = self._create_event(
            event_type=AuditEventType.SYSTEM_STARTUP,
            severity=AuditSeverity.LOW,
            message="System started",
            action="startup",
            **kwargs
        )
        self.log_event(event)

    def log_error(
        self,
        error_type: str,
        error_message: str,
        **kwargs
    ) -> None:
        """Log system error event."""
        event = self._create_event(
            event_type=AuditEventType.ERROR_OCCURRED,
            severity=AuditSeverity.HIGH,
            message=f"System error: {error_message}",
            metadata={
                "error_type": error_type,
                "error_message": error_message
            },
            tags=["error"],
            **kwargs
        )
        self.log_event(event)


# Global audit logger instance
audit_logger = AuditLogger()


# Context management functions
def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context."""
    return correlation_id_var.get()


def set_user_context(user_id: str) -> None:
    """Set user ID for current context."""
    user_id_var.set(user_id)


def set_request_context(request_id: str) -> None:
    """Set request ID for current context."""
    request_id_var.set(request_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


# Convenience functions for common audit events
def log_login_success(
    user_id: str,
    username: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Log successful login."""
    audit_logger.log_login_success(user_id, username, ip_address, user_agent)


def log_login_failure(
    username: str,
    reason: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """Log failed login attempt."""
    audit_logger.log_login_failure(username, reason, ip_address, user_agent)


def log_suspicious_activity(
    activity_type: str,
    description: str,
    risk_score: int,
    ip_address: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Log suspicious activity."""
    audit_logger.log_suspicious_activity(
        activity_type, description, risk_score, ip_address, user_id
    )


def log_authentication_event(
    event_type: AuditEventType,
    username: Optional[str] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    correlation_id: Optional[str] = None,
    outcome: str = "unknown",
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log authentication event."""
    if event_type == AuditEventType.LOGIN_SUCCESS:
        audit_logger.log_login_success(user_id or "unknown", username or "unknown", ip_address, user_agent)
    elif event_type == AuditEventType.LOGIN_FAILURE:
        audit_logger.log_login_failure(username or "unknown", outcome, ip_address, user_agent)
    else:
        # Generic authentication event
        event = AuditEvent(
            event_type=event_type,
            severity=AuditSeverity.MEDIUM,
            message=f"Authentication event: {event_type.value}",
            timestamp=time.time(),
            correlation_id=correlation_id or get_correlation_id(),
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            action="authentication",
            outcome=outcome,
            metadata=details or {},
        )
        audit_logger.log_event(event)


def log_admin_action_event(
    action: str,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    ip_address: Optional[str] = None,
    correlation_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Log admin action event."""
    event = AuditEvent(
        event_type=AuditEventType.ADMIN_ACTION,
        severity=AuditSeverity.HIGH,
        message=f"Admin action: {action}",
        timestamp=time.time(),
        correlation_id=correlation_id or get_correlation_id(),
        user_id=user_id,
        username=username,
        ip_address=ip_address,
        action=action,
        outcome="success",
        metadata=details or {},
        tags=["admin", "action"],
    )
    audit_logger.log_event(event)
