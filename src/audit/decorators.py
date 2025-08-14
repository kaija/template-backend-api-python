"""
Audit decorators for automatic function-level audit logging.

This module provides decorators that can be applied to functions
to automatically log audit events for various operations.
"""

import functools
import inspect
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from datetime import datetime

from .audit_logger import (
    audit_logger,
    AuditEventType,
    AuditSeverity,
    AuditEvent,
    get_correlation_id,
    user_id_var,
)

F = TypeVar('F', bound=Callable[..., Any])


def audit_event(
    event_type: AuditEventType,
    severity: AuditSeverity = AuditSeverity.MEDIUM,
    message_template: Optional[str] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    log_args: bool = False,
    log_result: bool = False,
    sensitive_args: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """
    Decorator for automatic audit logging of function calls.

    Args:
        event_type: Type of audit event
        severity: Event severity level
        message_template: Template for audit message (can use function args)
        resource_type: Type of resource being operated on
        action: Action being performed
        log_args: Whether to log function arguments
        log_result: Whether to log function result
        sensitive_args: List of argument names to redact

    Example:
        @audit_event(
            event_type=AuditEventType.USER_CREATED,
            message_template="User {username} created by admin",
            resource_type="user",
            action="create",
            log_args=True,
            sensitive_args=["password"]
        )
        def create_user(username: str, email: str, password: str):
            # Function implementation
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await _execute_with_audit_async(
                func, args, kwargs, event_type, severity,
                message_template, resource_type, action,
                log_args, log_result, sensitive_args
            )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return _execute_with_audit_sync(
                func, args, kwargs, event_type, severity,
                message_template, resource_type, action,
                log_args, log_result, sensitive_args
            )

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _execute_with_audit_sync(
    func: Callable,
    args: tuple,
    kwargs: dict,
    event_type: AuditEventType,
    severity: AuditSeverity,
    message_template: Optional[str],
    resource_type: Optional[str],
    action: Optional[str],
    log_args: bool,
    log_result: bool,
    sensitive_args: Optional[List[str]],
) -> Any:
    """Execute synchronous function with audit logging."""
    start_time = time.time()

    # Get function signature for argument mapping
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    # Create audit message
    message = _create_audit_message(
        func, message_template, bound_args.arguments
    )

    # Prepare metadata
    metadata = {
        "function": func.__name__,
        "module": func.__module__,
        "execution_time": None,  # Will be set after execution
    }

    # Add arguments to metadata if requested
    if log_args:
        sanitized_args = _sanitize_arguments(
            bound_args.arguments, sensitive_args or []
        )
        metadata["arguments"] = sanitized_args

    # Extract resource ID if available
    resource_id = _extract_resource_id(bound_args.arguments)

    try:
        # Execute function
        result = func(*args, **kwargs)

        # Calculate execution time
        execution_time = time.time() - start_time
        metadata["execution_time"] = round(execution_time * 1000, 2)  # ms

        # Add result to metadata if requested
        if log_result:
            metadata["result"] = _sanitize_result(result)

        # Create and log audit event
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            correlation_id=get_correlation_id(),
            user_id=user_id_var.get(),
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            metadata=metadata,
        )

        audit_logger.log_event(event)

        return result

    except Exception as e:
        # Log error event
        execution_time = time.time() - start_time
        metadata["execution_time"] = round(execution_time * 1000, 2)
        metadata["error"] = {
            "type": type(e).__name__,
            "message": str(e),
        }

        error_event = AuditEvent(
            event_type=AuditEventType.ERROR_OCCURRED,
            severity=AuditSeverity.HIGH,
            message=f"Error in {func.__name__}: {str(e)}",
            timestamp=datetime.utcnow(),
            correlation_id=get_correlation_id(),
            user_id=user_id_var.get(),
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            metadata=metadata,
            tags=["error", "function_execution"],
        )

        audit_logger.log_event(error_event)

        # Re-raise the exception
        raise


async def _execute_with_audit_async(
    func: Callable,
    args: tuple,
    kwargs: dict,
    event_type: AuditEventType,
    severity: AuditSeverity,
    message_template: Optional[str],
    resource_type: Optional[str],
    action: Optional[str],
    log_args: bool,
    log_result: bool,
    sensitive_args: Optional[List[str]],
) -> Any:
    """Execute asynchronous function with audit logging."""
    start_time = time.time()

    # Get function signature for argument mapping
    sig = inspect.signature(func)
    bound_args = sig.bind(*args, **kwargs)
    bound_args.apply_defaults()

    # Create audit message
    message = _create_audit_message(
        func, message_template, bound_args.arguments
    )

    # Prepare metadata
    metadata = {
        "function": func.__name__,
        "module": func.__module__,
        "execution_time": None,  # Will be set after execution
    }

    # Add arguments to metadata if requested
    if log_args:
        sanitized_args = _sanitize_arguments(
            bound_args.arguments, sensitive_args or []
        )
        metadata["arguments"] = sanitized_args

    # Extract resource ID if available
    resource_id = _extract_resource_id(bound_args.arguments)

    try:
        # Execute function
        result = await func(*args, **kwargs)

        # Calculate execution time
        execution_time = time.time() - start_time
        metadata["execution_time"] = round(execution_time * 1000, 2)  # ms

        # Add result to metadata if requested
        if log_result:
            metadata["result"] = _sanitize_result(result)

        # Create and log audit event
        event = AuditEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            correlation_id=get_correlation_id(),
            user_id=user_id_var.get(),
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            metadata=metadata,
        )

        audit_logger.log_event(event)

        return result

    except Exception as e:
        # Log error event
        execution_time = time.time() - start_time
        metadata["execution_time"] = round(execution_time * 1000, 2)
        metadata["error"] = {
            "type": type(e).__name__,
            "message": str(e),
        }

        error_event = AuditEvent(
            event_type=AuditEventType.ERROR_OCCURRED,
            severity=AuditSeverity.HIGH,
            message=f"Error in {func.__name__}: {str(e)}",
            timestamp=datetime.utcnow(),
            correlation_id=get_correlation_id(),
            user_id=user_id_var.get(),
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            metadata=metadata,
            tags=["error", "function_execution"],
        )

        audit_logger.log_event(error_event)

        # Re-raise the exception
        raise


def _create_audit_message(
    func: Callable,
    message_template: Optional[str],
    arguments: Dict[str, Any],
) -> str:
    """Create audit message from template or function name."""
    if message_template:
        try:
            return message_template.format(**arguments)
        except (KeyError, ValueError):
            # Fall back to default message if template formatting fails
            pass

    # Default message
    return f"Function {func.__name__} executed"


def _sanitize_arguments(
    arguments: Dict[str, Any],
    sensitive_args: List[str],
) -> Dict[str, Any]:
    """Sanitize function arguments for logging."""
    sanitized = {}

    for key, value in arguments.items():
        if key in sensitive_args:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, (str, int, float, bool, type(None))):
            sanitized[key] = value
        elif isinstance(value, (list, tuple)):
            sanitized[key] = f"<{type(value).__name__} with {len(value)} items>"
        elif isinstance(value, dict):
            sanitized[key] = f"<dict with {len(value)} keys>"
        else:
            sanitized[key] = f"<{type(value).__name__}>"

    return sanitized


def _sanitize_result(result: Any) -> Any:
    """Sanitize function result for logging."""
    if isinstance(result, (str, int, float, bool, type(None))):
        return result
    elif isinstance(result, (list, tuple)):
        return f"<{type(result).__name__} with {len(result)} items>"
    elif isinstance(result, dict):
        return f"<dict with {len(result)} keys>"
    else:
        return f"<{type(result).__name__}>"


def _extract_resource_id(arguments: Dict[str, Any]) -> Optional[str]:
    """Extract resource ID from function arguments."""
    # Common parameter names that might contain resource IDs
    id_params = ['id', 'user_id', 'resource_id', 'entity_id', 'record_id']

    for param in id_params:
        if param in arguments:
            value = arguments[param]
            if isinstance(value, (str, int)):
                return str(value)

    return None


# Convenience decorators for common audit events
def audit_login(
    message_template: str = "User {username} login attempt",
    log_args: bool = True,
    sensitive_args: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """Decorator for login function auditing."""
    return audit_event(
        event_type=AuditEventType.LOGIN_SUCCESS,
        severity=AuditSeverity.MEDIUM,
        message_template=message_template,
        action="login",
        log_args=log_args,
        sensitive_args=sensitive_args or ["password", "token"],
    )


def audit_user_creation(
    message_template: str = "User {username} created",
    log_args: bool = True,
    sensitive_args: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """Decorator for user creation function auditing."""
    return audit_event(
        event_type=AuditEventType.USER_CREATED,
        severity=AuditSeverity.MEDIUM,
        message_template=message_template,
        resource_type="user",
        action="create",
        log_args=log_args,
        sensitive_args=sensitive_args or ["password", "hashed_password"],
    )


def audit_user_update(
    message_template: str = "User {user_id} updated",
    log_args: bool = True,
    sensitive_args: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """Decorator for user update function auditing."""
    return audit_event(
        event_type=AuditEventType.USER_UPDATED,
        severity=AuditSeverity.MEDIUM,
        message_template=message_template,
        resource_type="user",
        action="update",
        log_args=log_args,
        sensitive_args=sensitive_args or ["password", "hashed_password"],
    )


def audit_user_deletion(
    message_template: str = "User {user_id} deleted",
    log_args: bool = True,
) -> Callable[[F], F]:
    """Decorator for user deletion function auditing."""
    return audit_event(
        event_type=AuditEventType.USER_DELETED,
        severity=AuditSeverity.HIGH,
        message_template=message_template,
        resource_type="user",
        action="delete",
        log_args=log_args,
    )


def audit_api_key_creation(
    message_template: str = "API key {name} created for user {user_id}",
    log_args: bool = True,
    sensitive_args: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """Decorator for API key creation function auditing."""
    return audit_event(
        event_type=AuditEventType.API_KEY_CREATED,
        severity=AuditSeverity.MEDIUM,
        message_template=message_template,
        resource_type="api_key",
        action="create",
        log_args=log_args,
        sensitive_args=sensitive_args or ["key", "key_hash", "raw_key"],
    )


def audit_admin_action(
    message_template: str = "Admin action performed",
    log_args: bool = True,
    sensitive_args: Optional[List[str]] = None,
) -> Callable[[F], F]:
    """Decorator for admin action function auditing."""
    return audit_event(
        event_type=AuditEventType.ADMIN_ACTION,
        severity=AuditSeverity.HIGH,
        message_template=message_template,
        action="admin",
        log_args=log_args,
        sensitive_args=sensitive_args or [],
    )


def audit_security_event(
    message_template: str = "Security event occurred",
    severity: AuditSeverity = AuditSeverity.HIGH,
    log_args: bool = True,
) -> Callable[[F], F]:
    """Decorator for security event function auditing."""
    return audit_event(
        event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
        severity=severity,
        message_template=message_template,
        action="security",
        log_args=log_args,
    )


# Context manager for audit scoping
class AuditScope:
    """
    Context manager for grouping related audit events.

    Allows grouping multiple audit events under a single
    operation or transaction scope.
    """

    def __init__(
        self,
        operation_name: str,
        operation_type: str = "transaction",
        user_id: Optional[str] = None,
    ):
        """
        Initialize audit scope.

        Args:
            operation_name: Name of the operation
            operation_type: Type of operation
            user_id: User performing the operation
        """
        self.operation_name = operation_name
        self.operation_type = operation_type
        self.user_id = user_id
        self.start_time = None
        self.events = []

    def __enter__(self):
        """Enter audit scope."""
        self.start_time = time.time()

        # Log operation start
        start_event = AuditEvent(
            event_type=AuditEventType.ADMIN_ACTION,
            severity=AuditSeverity.LOW,
            message=f"Operation {self.operation_name} started",
            timestamp=datetime.utcnow(),
            correlation_id=get_correlation_id(),
            user_id=self.user_id or user_id_var.get(),
            action="operation_start",
            metadata={
                "operation_name": self.operation_name,
                "operation_type": self.operation_type,
            },
        )

        audit_logger.log_event(start_event)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit audit scope."""
        duration = time.time() - self.start_time if self.start_time else 0

        # Determine operation result
        if exc_type is None:
            result = "success"
            severity = AuditSeverity.LOW
            message = f"Operation {self.operation_name} completed successfully"
        else:
            result = "failure"
            severity = AuditSeverity.HIGH
            message = f"Operation {self.operation_name} failed: {str(exc_val)}"

        # Log operation end
        end_event = AuditEvent(
            event_type=AuditEventType.ADMIN_ACTION,
            severity=severity,
            message=message,
            timestamp=datetime.utcnow(),
            correlation_id=get_correlation_id(),
            user_id=self.user_id or user_id_var.get(),
            action="operation_end",
            metadata={
                "operation_name": self.operation_name,
                "operation_type": self.operation_type,
                "result": result,
                "duration_ms": round(duration * 1000, 2),
                "error": str(exc_val) if exc_val else None,
            },
        )

        audit_logger.log_event(end_event)

    def add_event(self, event: AuditEvent) -> None:
        """Add event to the current scope."""
        self.events.append(event)
        audit_logger.log_event(event)
