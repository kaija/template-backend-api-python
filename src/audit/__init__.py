"""
Audit logging module for security event tracking and compliance.

This module provides comprehensive audit logging capabilities including:
- Structured audit event logging
- Request/response tracking middleware
- Function-level audit decorators
- Security event detection
- Correlation ID management
"""

from .audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    audit_logger,
    set_correlation_id,
    get_correlation_id,
    set_user_context,
    set_request_context,
    generate_correlation_id,
    log_login_success,
    log_login_failure,
    log_suspicious_activity,
)

from .middleware import (
    AuditMiddleware,
    SecurityEventDetector,
    security_detector,
)

from .decorators import (
    audit_event,
    audit_login,
    audit_user_creation,
    audit_user_update,
    audit_user_deletion,
    audit_api_key_creation,
    audit_admin_action,
    audit_security_event,
    AuditScope,
)

__all__ = [
    # Core audit logging
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "AuditSeverity",
    "audit_logger",
    
    # Context management
    "set_correlation_id",
    "get_correlation_id",
    "set_user_context",
    "set_request_context",
    "generate_correlation_id",
    
    # Convenience functions
    "log_login_success",
    "log_login_failure",
    "log_suspicious_activity",
    
    # Middleware
    "AuditMiddleware",
    "SecurityEventDetector",
    "security_detector",
    
    # Decorators
    "audit_event",
    "audit_login",
    "audit_user_creation",
    "audit_user_update",
    "audit_user_deletion",
    "audit_api_key_creation",
    "audit_admin_action",
    "audit_security_event",
    "AuditScope",
]