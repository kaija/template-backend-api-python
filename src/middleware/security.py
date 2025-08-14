"""
Security middleware for handling security headers and common vulnerabilities.

This module provides middleware for adding security headers and protecting
against common web vulnerabilities.
"""

import logging
from typing import Dict, List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Import configuration functions with fallback for testing
try:
    from src.config.settings import is_development, is_production
except Exception:
    # Fallback for testing when configuration is not available
    def is_development():
        return True

    def is_production():
        return False

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to responses.

    This middleware adds various security headers to protect against
    common web vulnerabilities like XSS, clickjacking, and MIME sniffing.
    """

    def __init__(
        self,
        app: ASGIApp,
        custom_headers: Optional[Dict[str, str]] = None,
        enable_hsts: bool = True,
        enable_csp: bool = True,
        csp_policy: Optional[str] = None
    ):
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application instance
            custom_headers: Additional custom security headers
            enable_hsts: Whether to enable HTTP Strict Transport Security
            enable_csp: Whether to enable Content Security Policy
            csp_policy: Custom CSP policy string
        """
        super().__init__(app)
        self.custom_headers = custom_headers or {}
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp
        self.csp_policy = csp_policy

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request and add security headers to response.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response with security headers added
        """
        # Process request
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response)

        return response

    def _add_security_headers(self, response: Response) -> None:
        """
        Add security headers to the response.

        Args:
            response: FastAPI response object
        """
        # Basic security headers
        security_headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Prevent clickjacking
            "X-Frame-Options": "DENY",

            # Enable XSS protection (legacy browsers)
            "X-XSS-Protection": "1; mode=block",

            # Prevent information disclosure
            "X-Powered-By": "",
            "Server": "",

            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",

            # Permissions policy (formerly Feature Policy)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            )
        }

        # Add HSTS header for HTTPS (production only)
        if self.enable_hsts and is_production():
            security_headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Add Content Security Policy
        if self.enable_csp:
            csp_policy = self.csp_policy or self._get_default_csp_policy()
            security_headers["Content-Security-Policy"] = csp_policy

        # Add custom headers
        security_headers.update(self.custom_headers)

        # Apply headers to response
        for header, value in security_headers.items():
            if value:  # Only add non-empty values
                response.headers[header] = value

    def _get_default_csp_policy(self) -> str:
        """
        Get default Content Security Policy.

        Returns:
            Default CSP policy string
        """
        if is_development():
            # More permissive policy for development
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
                "connect-src 'self' ws: wss:; "
                "frame-ancestors 'none'"
            )
        else:
            # Strict policy for production (allows CDN for documentation)
            return (
                "default-src 'self'; "
                "script-src 'self' https://cdn.jsdelivr.net; "
                "style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
                "img-src 'self' data: https://fastapi.tiangolo.com; "
                "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic rate limiting middleware.

    This middleware provides simple rate limiting based on client IP.
    For production use, consider using Redis-based rate limiting.
    """

    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        enabled: bool = True
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: ASGI application instance
            requests_per_minute: Maximum requests per minute per client
            burst_size: Maximum burst requests allowed
            enabled: Whether rate limiting is enabled
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.enabled = enabled

        # Simple in-memory storage (use Redis in production)
        self._client_requests: Dict[str, List[float]] = {}

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response object or rate limit error
        """
        if not self.enabled:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        if self._is_rate_limited(client_id):
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"}
            )

        # Record request
        self._record_request(client_id)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = self._get_remaining_requests(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(60)  # Reset in 60 seconds

        return response

    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.

        Args:
            request: FastAPI request object

        Returns:
            Client identifier string
        """
        # Try to get real IP from headers (behind proxy)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",
            "x-client-ip",
        ]

        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one
                return ip.split(",")[0].strip()

        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

    def _is_rate_limited(self, client_id: str) -> bool:
        """
        Check if client is rate limited.

        Args:
            client_id: Client identifier

        Returns:
            True if client is rate limited
        """
        import time

        current_time = time.time()
        minute_ago = current_time - 60

        # Get client request history
        requests = self._client_requests.get(client_id, [])

        # Remove old requests (older than 1 minute)
        recent_requests = [req_time for req_time in requests if req_time > minute_ago]

        # Update client request history
        self._client_requests[client_id] = recent_requests

        # Check if rate limited
        return len(recent_requests) >= self.requests_per_minute

    def _record_request(self, client_id: str) -> None:
        """
        Record a request for the client.

        Args:
            client_id: Client identifier
        """
        import time

        current_time = time.time()

        if client_id not in self._client_requests:
            self._client_requests[client_id] = []

        self._client_requests[client_id].append(current_time)

    def _get_remaining_requests(self, client_id: str) -> int:
        """
        Get remaining requests for client.

        Args:
            client_id: Client identifier

        Returns:
            Number of remaining requests
        """
        requests = self._client_requests.get(client_id, [])
        return max(0, self.requests_per_minute - len(requests))


class TrustedHostMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate trusted hosts.

    This middleware validates that requests come from trusted hosts
    to prevent Host header attacks.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_hosts: List[str],
        allow_any: bool = False
    ):
        """
        Initialize trusted host middleware.

        Args:
            app: ASGI application instance
            allowed_hosts: List of allowed host patterns
            allow_any: Whether to allow any host (development only)
        """
        super().__init__(app)
        self.allowed_hosts = allowed_hosts
        self.allow_any = allow_any

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with host validation.

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain

        Returns:
            Response object or host validation error
        """
        if self.allow_any:
            return await call_next(request)

        # Get host from request
        host = request.headers.get("host", "")

        # Validate host
        if not self._is_allowed_host(host):
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid host header"}
            )

        return await call_next(request)

    def _is_allowed_host(self, host: str) -> bool:
        """
        Check if host is allowed.

        Args:
            host: Host header value

        Returns:
            True if host is allowed
        """
        if not host:
            return False

        # Remove port from host if present
        host_without_port = host.split(":")[0]

        for allowed_host in self.allowed_hosts:
            if allowed_host == "*":
                return True

            # Exact match
            if host_without_port == allowed_host:
                return True

            # Wildcard subdomain match
            if allowed_host.startswith("*."):
                domain = allowed_host[2:]
                if host_without_port.endswith(f".{domain}") or host_without_port == domain:
                    return True

        return False
