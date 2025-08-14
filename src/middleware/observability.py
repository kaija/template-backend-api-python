"""
Observability middleware for request/response logging and monitoring.

This module provides middleware for comprehensive request/response logging
with sensitive data masking, performance metrics, and correlation tracking.
"""

import time
from typing import Any, Dict, Optional, Set

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.utils.logging import get_logger, log_request, log_response, set_correlation_id


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for comprehensive observability and monitoring.
    
    This middleware provides:
    - Request/response logging with sensitive data masking
    - Performance metrics collection
    - Correlation ID tracking
    - Error tracking and monitoring
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        mask_sensitive_data: bool = True,
        track_performance: bool = True,
    ):
        """
        Initialize observability middleware.
        
        Args:
            app: ASGI application instance
            log_requests: Whether to log incoming requests
            log_responses: Whether to log outgoing responses
            log_request_body: Whether to log request body (be careful with sensitive data)
            log_response_body: Whether to log response body (be careful with sensitive data)
            mask_sensitive_data: Whether to mask sensitive data in logs
            track_performance: Whether to track performance metrics
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.mask_sensitive_data = mask_sensitive_data
        self.track_performance = track_performance
        
        self.logger = get_logger(__name__)
        
        # Sensitive headers to mask
        self.sensitive_headers = {
            "authorization",
            "x-api-key",
            "cookie",
            "set-cookie",
            "x-auth-token",
            "x-access-token",
            "x-refresh-token",
            "x-session-token",
            "x-csrf-token",
            "x-xsrf-token",
        }
        
        # Sensitive query parameters to mask
        self.sensitive_params = {
            "password",
            "token",
            "api_key",
            "secret",
            "key",
            "access_token",
            "refresh_token",
            "session_id",
            "csrf_token",
            "xsrf_token",
        }
        
        # Paths to exclude from detailed logging
        self.excluded_paths = {
            "/healthz",
            "/readyz",
            "/metrics",
            "/favicon.ico",
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with observability tracking.
        
        Args:
            request: FastAPI request object
            call_next: Next middleware/handler in chain
            
        Returns:
            Response object
        """
        # Skip detailed logging for excluded paths
        should_log = request.url.path not in self.excluded_paths
        
        # Get correlation ID from request state (set by CorrelationIDMiddleware)
        correlation_id = getattr(request.state, "correlation_id", None)
        
        # Set correlation ID in logging context
        if correlation_id:
            set_correlation_id(correlation_id)
        
        # Start performance tracking
        start_time = time.time()
        
        # Log incoming request
        if should_log and self.log_requests:
            await self._log_request(request, correlation_id)
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000
        
        # Add performance headers
        if self.track_performance:
            response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
        
        # Log outgoing response
        if should_log and self.log_responses:
            await self._log_response(request, response, response_time_ms, correlation_id)
        
        # Track performance metrics
        if self.track_performance:
            await self._track_performance_metrics(
                request, response, response_time_ms, correlation_id
            )
        
        return response
    
    async def _log_request(self, request: Request, correlation_id: Optional[str]) -> None:
        """
        Log incoming HTTP request.
        
        Args:
            request: FastAPI request object
            correlation_id: Request correlation ID
        """
        try:
            # Extract request information
            headers = dict(request.headers)
            query_params = dict(request.query_params)
            
            # Mask sensitive data if enabled
            if self.mask_sensitive_data:
                headers = self._mask_sensitive_data(headers, self.sensitive_headers)
                query_params = self._mask_sensitive_data(query_params, self.sensitive_params)
            
            # Get client information
            client_ip = self._get_client_ip(request)
            user_agent = headers.get("user-agent", "unknown")
            
            # Get user information if available
            user_id = None
            username = None
            if hasattr(request.state, "user") and request.state.user:
                user_id = request.state.user.get("user_id")
                username = request.state.user.get("username")
            
            # Prepare log data
            log_data = {
                "query_params": query_params,
                "headers": headers,
                "client_ip": client_ip,
                "user_agent": user_agent,
                "user_id": user_id,
                "username": username,
                "content_type": headers.get("content-type"),
                "content_length": headers.get("content-length"),
            }
            
            # Log request body if enabled (be very careful with this)
            if self.log_request_body:
                try:
                    # Note: This consumes the request body, so it needs to be handled carefully
                    # In production, you might want to avoid this or implement body streaming
                    body = await request.body()
                    if body:
                        # Only log small bodies and mask sensitive data
                        if len(body) < 1024:  # 1KB limit
                            log_data["request_body_size"] = len(body)
                            if self.mask_sensitive_data:
                                log_data["request_body"] = "***MASKED***"
                            else:
                                log_data["request_body"] = body.decode("utf-8", errors="ignore")
                        else:
                            log_data["request_body_size"] = len(body)
                            log_data["request_body"] = "***TOO_LARGE***"
                except Exception as e:
                    log_data["request_body_error"] = str(e)
            
            # Log the request
            log_request(
                method=request.method,
                path=request.url.path,
                correlation_id=correlation_id,
                **log_data
            )
            
        except Exception as e:
            self.logger.error(
                "Error logging request",
                error=str(e),
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
            )
    
    async def _log_response(
        self,
        request: Request,
        response: Response,
        response_time_ms: float,
        correlation_id: Optional[str]
    ) -> None:
        """
        Log outgoing HTTP response.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object
            response_time_ms: Response time in milliseconds
            correlation_id: Request correlation ID
        """
        try:
            # Get response size
            response_size = None
            if hasattr(response, "headers") and "content-length" in response.headers:
                try:
                    response_size = int(response.headers["content-length"])
                except (ValueError, TypeError):
                    pass
            
            # Prepare log data
            log_data = {
                "response_time_ms": round(response_time_ms, 2),
                "response_size": response_size,
                "content_type": getattr(response, "media_type", None),
            }
            
            # Add response headers (masked)
            if hasattr(response, "headers"):
                response_headers = dict(response.headers)
                if self.mask_sensitive_data:
                    response_headers = self._mask_sensitive_data(
                        response_headers, self.sensitive_headers
                    )
                log_data["response_headers"] = response_headers
            
            # Log response body if enabled (be very careful with this)
            if self.log_response_body and hasattr(response, "body"):
                try:
                    if response.body and len(response.body) < 1024:  # 1KB limit
                        if self.mask_sensitive_data:
                            log_data["response_body"] = "***MASKED***"
                        else:
                            log_data["response_body"] = response.body.decode("utf-8", errors="ignore")
                    elif response.body:
                        log_data["response_body"] = "***TOO_LARGE***"
                except Exception as e:
                    log_data["response_body_error"] = str(e)
            
            # Log the response
            log_response(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                response_size=response_size,
                correlation_id=correlation_id,
                content_type=log_data.get("content_type"),
                response_headers=log_data.get("response_headers")
            )
            
        except Exception as e:
            self.logger.error(
                "Error logging response",
                error=str(e),
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
                status_code=getattr(response, "status_code", None),
            )
    
    async def _track_performance_metrics(
        self,
        request: Request,
        response: Response,
        response_time_ms: float,
        correlation_id: Optional[str]
    ) -> None:
        """
        Track performance metrics for monitoring.
        
        Args:
            request: FastAPI request object
            response: FastAPI response object
            response_time_ms: Response time in milliseconds
            correlation_id: Request correlation ID
        """
        try:
            # Import metrics here to avoid circular imports
            from src.monitoring.metrics import (
                http_requests_total,
                http_request_duration_seconds,
                http_request_size_bytes,
                http_response_size_bytes,
            )
            
            # Track request count
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code
            ).inc()
            
            # Track request duration
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(response_time_ms / 1000)  # Convert to seconds
            
            # Track request size
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    request_size = int(content_length)
                    http_request_size_bytes.labels(
                        method=request.method,
                        endpoint=request.url.path
                    ).observe(request_size)
                except (ValueError, TypeError):
                    pass
            
            # Track response size
            response_content_length = getattr(response, "headers", {}).get("content-length")
            if response_content_length:
                try:
                    response_size = int(response_content_length)
                    http_response_size_bytes.labels(
                        method=request.method,
                        endpoint=request.url.path
                    ).observe(response_size)
                except (ValueError, TypeError):
                    pass
            
        except ImportError:
            # Metrics not available yet
            pass
        except Exception as e:
            self.logger.error(
                "Error tracking performance metrics",
                error=str(e),
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
            )
    
    def _mask_sensitive_data(self, data: Dict[str, Any], sensitive_keys: Set[str]) -> Dict[str, Any]:
        """
        Mask sensitive data in dictionary.
        
        Args:
            data: Dictionary to mask
            sensitive_keys: Set of sensitive keys to mask
            
        Returns:
            Dictionary with sensitive values masked
        """
        if not self.mask_sensitive_data:
            return data
        
        masked_data = {}
        
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                masked_data[key] = "***MASKED***"
            elif isinstance(value, str) and self._contains_sensitive_pattern(value):
                masked_data[key] = "***MASKED***"
            else:
                masked_data[key] = value
        
        return masked_data
    
    def _contains_sensitive_pattern(self, value: str) -> bool:
        """
        Check if string value contains sensitive patterns.
        
        Args:
            value: String value to check
            
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
        ]
        
        value_lower = value.lower()
        return any(pattern in value_lower for pattern in sensitive_patterns)
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Extract client IP address from request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address or None
        """
        # Check for forwarded headers (from load balancers/proxies)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip",
            "cf-connecting-ip",  # Cloudflare
            "x-client-ip",
            "x-forwarded",
            "forwarded-for",
            "forwarded",
        ]
        
        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs, take the first one
                return ip.split(",")[0].strip()
        
        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return None