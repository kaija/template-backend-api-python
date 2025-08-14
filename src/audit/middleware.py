"""
Audit middleware for automatic request tracking and context management.

This middleware automatically tracks requests, sets correlation IDs,
and logs security-relevant events.
"""

import time
import uuid
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .audit_logger import (
    audit_logger,
    set_correlation_id,
    set_request_context,
    set_user_context,
    get_correlation_id,
    AuditEventType,
    AuditSeverity,
    AuditEvent,
)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware for audit logging and request tracking.

    Automatically:
    - Sets correlation IDs for request tracking
    - Logs request/response information
    - Tracks authentication events
    - Detects suspicious patterns
    """

    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        log_responses: bool = True,
        log_errors: bool = True,
        sensitive_headers: Optional[set] = None,
        excluded_paths: Optional[set] = None,
    ):
        """
        Initialize audit middleware.

        Args:
            app: ASGI application
            log_requests: Whether to log incoming requests
            log_responses: Whether to log outgoing responses
            log_errors: Whether to log errors
            sensitive_headers: Headers to exclude from logging
            excluded_paths: Paths to exclude from audit logging
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_errors = log_errors

        # Default sensitive headers to exclude
        self.sensitive_headers = sensitive_headers or {
            'authorization',
            'cookie',
            'x-api-key',
            'x-auth-token',
            'x-access-token',
        }

        # Paths to exclude from audit logging
        self.excluded_paths = excluded_paths or {
            '/health',
            '/healthz',
            '/readyz',
            '/metrics',
            '/favicon.ico',
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and response with audit logging."""
        start_time = time.time()

        # Skip audit logging for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Set up request context
        correlation_id = self._get_or_create_correlation_id(request)
        request_id = str(uuid.uuid4())

        set_correlation_id(correlation_id)
        set_request_context(request_id)

        # Extract user context if available
        user_id = self._extract_user_id(request)
        if user_id:
            set_user_context(user_id)

        # Log incoming request
        if self.log_requests:
            self._log_request(request, correlation_id, request_id)

        # Process request and handle errors
        try:
            response = await call_next(request)

            # Log outgoing response
            if self.log_responses:
                self._log_response(
                    request, response, correlation_id,
                    request_id, time.time() - start_time
                )

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Log error
            if self.log_errors:
                self._log_error(request, e, correlation_id, request_id)

            # Re-raise the exception
            raise

    def _get_or_create_correlation_id(self, request: Request) -> str:
        """Get correlation ID from request headers or create new one."""
        # Check for existing correlation ID in headers
        correlation_id = request.headers.get('x-correlation-id')
        if not correlation_id:
            correlation_id = request.headers.get('x-request-id')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        return correlation_id

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request context."""
        # Try to get user from request state (set by auth middleware)
        if hasattr(request.state, 'user') and request.state.user:
            return getattr(request.state.user, 'id', None)

        # Try to get user ID from custom header
        return request.headers.get('x-user-id')

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _sanitize_headers(self, headers: dict) -> dict:
        """Remove sensitive headers from logging."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized

    def _log_request(
        self,
        request: Request,
        correlation_id: str,
        request_id: str
    ) -> None:
        """Log incoming request details."""
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get('user-agent', 'unknown')

        # Create request audit event
        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_STARTUP,  # Using as generic request event
            severity=AuditSeverity.LOW,
            message=f"{request.method} {request.url.path}",
            timestamp=time.time(),
            correlation_id=correlation_id,
            request_id=request_id,
            ip_address=client_ip,
            user_agent=user_agent,
            action="request",
            metadata={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "headers": self._sanitize_headers(dict(request.headers)),
            }
        )

        audit_logger.log_event(event)

    def _log_response(
        self,
        request: Request,
        response: Response,
        correlation_id: str,
        request_id: str,
        duration: float,
    ) -> None:
        """Log outgoing response details."""
        client_ip = self._get_client_ip(request)

        # Determine severity based on status code
        if response.status_code >= 500:
            severity = AuditSeverity.HIGH
        elif response.status_code >= 400:
            severity = AuditSeverity.MEDIUM
        else:
            severity = AuditSeverity.LOW

        # Create response audit event
        event = AuditEvent(
            event_type=AuditEventType.SYSTEM_STARTUP,  # Using as generic response event
            severity=severity,
            message=f"{request.method} {request.url.path} -> {response.status_code}",
            timestamp=time.time(),
            correlation_id=correlation_id,
            request_id=request_id,
            ip_address=client_ip,
            action="response",
            metadata={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "response_headers": self._sanitize_headers(dict(response.headers)),
            }
        )

        audit_logger.log_event(event)

        # Log suspicious patterns
        self._detect_suspicious_patterns(request, response, client_ip, duration)

    def _log_error(
        self,
        request: Request,
        error: Exception,
        correlation_id: str,
        request_id: str,
    ) -> None:
        """Log request processing errors."""
        client_ip = self._get_client_ip(request)

        # Create error audit event
        event = AuditEvent(
            event_type=AuditEventType.ERROR_OCCURRED,
            severity=AuditSeverity.HIGH,
            message=f"Request error: {str(error)}",
            timestamp=time.time(),
            correlation_id=correlation_id,
            request_id=request_id,
            ip_address=client_ip,
            action="error",
            metadata={
                "method": request.method,
                "path": request.url.path,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
            tags=["error", "request_processing"]
        )

        audit_logger.log_event(event)

    def _detect_suspicious_patterns(
        self,
        request: Request,
        response: Response,
        client_ip: str,
        duration: float,
    ) -> None:
        """Detect and log suspicious request patterns."""
        suspicious_indicators = []
        risk_score = 0

        # Check for multiple failed authentication attempts
        if response.status_code == 401:
            suspicious_indicators.append("authentication_failure")
            risk_score += 30

        # Check for forbidden access attempts
        if response.status_code == 403:
            suspicious_indicators.append("forbidden_access")
            risk_score += 40

        # Check for suspicious paths
        suspicious_paths = [
            '/admin', '/.env', '/config', '/backup',
            '/wp-admin', '/phpmyadmin', '/mysql',
            '/../', '/etc/passwd', '/proc/version'
        ]

        if any(path in request.url.path.lower() for path in suspicious_paths):
            suspicious_indicators.append("suspicious_path")
            risk_score += 50

        # Check for suspicious user agents
        user_agent = request.headers.get('user-agent', '').lower()
        suspicious_agents = [
            'sqlmap', 'nikto', 'nmap', 'masscan',
            'burp', 'owasp', 'scanner', 'bot'
        ]

        if any(agent in user_agent for agent in suspicious_agents):
            suspicious_indicators.append("suspicious_user_agent")
            risk_score += 60

        # Check for unusually long request duration (potential DoS)
        if duration > 10.0:  # 10 seconds
            suspicious_indicators.append("slow_request")
            risk_score += 20

        # Check for unusual request methods
        if request.method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
            suspicious_indicators.append("unusual_method")
            risk_score += 30

        # Log suspicious activity if risk score is high enough
        if risk_score >= 50:
            audit_logger.log_suspicious_activity(
                activity_type="request_pattern",
                description=f"Suspicious request pattern detected: {', '.join(suspicious_indicators)}",
                risk_score=risk_score,
                ip_address=client_ip,
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                    "indicators": suspicious_indicators,
                }
            )


class SecurityEventDetector:
    """
    Advanced security event detection and alerting.

    Analyzes audit logs and request patterns to detect
    potential security threats and anomalies.
    """

    def __init__(self):
        """Initialize security event detector."""
        self.failed_login_attempts = {}  # IP -> count
        self.request_counts = {}  # IP -> count
        self.suspicious_ips = set()

    def analyze_login_attempt(
        self,
        ip_address: str,
        username: str,
        success: bool,
        timestamp: float,
    ) -> None:
        """Analyze login attempt for brute force detection."""
        if not success:
            # Track failed attempts per IP
            if ip_address not in self.failed_login_attempts:
                self.failed_login_attempts[ip_address] = []

            self.failed_login_attempts[ip_address].append({
                'username': username,
                'timestamp': timestamp,
            })

            # Clean old attempts (older than 1 hour)
            cutoff_time = timestamp - 3600
            self.failed_login_attempts[ip_address] = [
                attempt for attempt in self.failed_login_attempts[ip_address]
                if attempt['timestamp'] > cutoff_time
            ]

            # Check for brute force pattern
            recent_failures = len(self.failed_login_attempts[ip_address])
            if recent_failures >= 5:  # 5 failures in 1 hour
                self._log_brute_force_attempt(ip_address, username, recent_failures)
        else:
            # Clear failed attempts on successful login
            if ip_address in self.failed_login_attempts:
                del self.failed_login_attempts[ip_address]

    def _log_brute_force_attempt(
        self,
        ip_address: str,
        username: str,
        attempt_count: int,
    ) -> None:
        """Log brute force attempt detection."""
        audit_logger.log_suspicious_activity(
            activity_type="brute_force",
            description=f"Brute force login attempt detected: {attempt_count} failures",
            risk_score=80,
            ip_address=ip_address,
            metadata={
                "username": username,
                "attempt_count": attempt_count,
                "detection_type": "brute_force_login",
            }
        )

        # Add IP to suspicious list
        self.suspicious_ips.add(ip_address)


# Global security event detector
security_detector = SecurityEventDetector()
