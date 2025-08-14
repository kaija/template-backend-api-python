"""
Tests for audit logging system.
"""

import json
import pytest
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.audit.audit_logger import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    AuditSeverity,
    audit_logger,
    set_correlation_id,
    get_correlation_id,
    set_user_context,
    generate_correlation_id,
)
from src.audit.decorators import (
    audit_event,
    audit_user_creation,
    AuditScope,
)
from src.audit.middleware import (
    AuditMiddleware,
    SecurityEventDetector,
)


class TestAuditEvent:
    """Test AuditEvent data class."""
    
    def test_audit_event_creation(self):
        """Test creating an audit event."""
        timestamp = datetime.utcnow()
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            message="User logged in",
            timestamp=timestamp,
            user_id="user123",
            ip_address="192.168.1.1"
        )
        
        assert event.event_type == AuditEventType.LOGIN_SUCCESS
        assert event.severity == AuditSeverity.LOW
        assert event.message == "User logged in"
        assert event.timestamp == timestamp
        assert event.user_id == "user123"
        assert event.ip_address == "192.168.1.1"
    
    def test_audit_event_to_dict(self):
        """Test converting audit event to dictionary."""
        timestamp = datetime.utcnow()
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            message="User logged in",
            timestamp=timestamp,
            user_id="user123",
            metadata={"key": "value"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_type"] == "auth.login.success"
        assert event_dict["severity"] == "low"
        assert event_dict["message"] == "User logged in"
        assert event_dict["timestamp"] == timestamp.isoformat()
        assert event_dict["user_id"] == "user123"
        assert event_dict["metadata"] == {"key": "value"}
        
        # Should not include None values
        assert "ip_address" not in event_dict
    
    def test_audit_event_to_json(self):
        """Test converting audit event to JSON."""
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            message="User logged in",
            timestamp=datetime.utcnow(),
        )
        
        json_str = event.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["event_type"] == "auth.login.success"
        assert parsed["severity"] == "low"
        assert parsed["message"] == "User logged in"


class TestAuditLogger:
    """Test AuditLogger class."""
    
    @pytest.fixture
    def temp_log_file(self):
        """Create temporary log file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)
    
    def test_audit_logger_initialization(self, temp_log_file):
        """Test audit logger initialization."""
        logger = AuditLogger(
            logger_name="test_audit",
            enable_console=False,
            enable_file=True,
            log_file_path=temp_log_file
        )
        
        assert logger.logger.name == "test_audit"
        assert len(logger.logger.handlers) > 0
    
    def test_log_event(self, temp_log_file):
        """Test logging an audit event."""
        logger = AuditLogger(
            logger_name="test_audit",
            enable_console=False,
            enable_file=True,
            log_file_path=temp_log_file
        )
        
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            message="Test event",
            timestamp=datetime.utcnow(),
        )
        
        logger.log_event(event)
        
        # Check that log file was written
        log_content = Path(temp_log_file).read_text()
        assert "Test event" in log_content
        assert "auth.login.success" in log_content
    
    def test_log_login_success(self, temp_log_file):
        """Test logging successful login."""
        logger = AuditLogger(
            logger_name="test_audit",
            enable_console=False,
            enable_file=True,
            log_file_path=temp_log_file
        )
        
        logger.log_login_success(
            user_id="user123",
            username="testuser",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        log_content = Path(temp_log_file).read_text()
        assert "testuser logged in successfully" in log_content
        assert "192.168.1.1" in log_content
    
    def test_log_login_failure(self, temp_log_file):
        """Test logging failed login."""
        logger = AuditLogger(
            logger_name="test_audit",
            enable_console=False,
            enable_file=True,
            log_file_path=temp_log_file
        )
        
        logger.log_login_failure(
            username="testuser",
            reason="Invalid password",
            ip_address="192.168.1.1"
        )
        
        log_content = Path(temp_log_file).read_text()
        assert "Login failed for user testuser" in log_content
        assert "Invalid password" in log_content
    
    def test_log_suspicious_activity(self, temp_log_file):
        """Test logging suspicious activity."""
        logger = AuditLogger(
            logger_name="test_audit",
            enable_console=False,
            enable_file=True,
            log_file_path=temp_log_file
        )
        
        logger.log_suspicious_activity(
            activity_type="brute_force",
            description="Multiple failed login attempts",
            risk_score=80,
            ip_address="192.168.1.1"
        )
        
        log_content = Path(temp_log_file).read_text()
        assert "Suspicious activity detected" in log_content
        assert "Multiple failed login attempts" in log_content
        assert "brute_force" in log_content


class TestCorrelationIdManagement:
    """Test correlation ID context management."""
    
    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        correlation_id = "test-correlation-123"
        set_correlation_id(correlation_id)
        
        assert get_correlation_id() == correlation_id
    
    def test_generate_correlation_id(self):
        """Test generating correlation ID."""
        correlation_id = generate_correlation_id()
        
        assert isinstance(correlation_id, str)
        assert len(correlation_id) > 0
        # Should be a valid UUID format
        assert len(correlation_id.split('-')) == 5
    
    def test_user_context(self):
        """Test setting user context."""
        set_user_context("user123")
        
        # Context should be available in the same execution context
        # This is tested indirectly through audit events


class TestAuditDecorators:
    """Test audit decorators."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger for testing."""
        with patch('src.audit.decorators.audit_logger') as mock:
            yield mock
    
    def test_audit_event_decorator_sync(self, mock_audit_logger):
        """Test audit event decorator on synchronous function."""
        @audit_event(
            event_type=AuditEventType.USER_CREATED,
            message_template="User {username} created",
            log_args=True
        )
        def create_user(username: str, email: str):
            return {"id": "user123", "username": username, "email": email}
        
        result = create_user("testuser", "test@example.com")
        
        assert result["username"] == "testuser"
        mock_audit_logger.log_event.assert_called_once()
        
        # Check the logged event
        logged_event = mock_audit_logger.log_event.call_args[0][0]
        assert logged_event.event_type == AuditEventType.USER_CREATED
        assert "testuser created" in logged_event.message
        assert "arguments" in logged_event.metadata
    
    @pytest.mark.asyncio
    async def test_audit_event_decorator_async(self, mock_audit_logger):
        """Test audit event decorator on asynchronous function."""
        @audit_event(
            event_type=AuditEventType.USER_UPDATED,
            message_template="User {user_id} updated",
            log_args=True
        )
        async def update_user(user_id: str, data: dict):
            return {"id": user_id, "updated": True}
        
        result = await update_user("user123", {"name": "New Name"})
        
        assert result["id"] == "user123"
        mock_audit_logger.log_event.assert_called_once()
    
    def test_audit_user_creation_decorator(self, mock_audit_logger):
        """Test audit user creation decorator."""
        @audit_user_creation(
            message_template="User {username} created by admin",
            sensitive_args=["password"]
        )
        def create_user(username: str, email: str, password: str):
            return {"id": "user123", "username": username}
        
        result = create_user("testuser", "test@example.com", "secret123")
        
        assert result["username"] == "testuser"
        mock_audit_logger.log_event.assert_called_once()
        
        # Check that password was redacted
        logged_event = mock_audit_logger.log_event.call_args[0][0]
        assert logged_event.metadata["arguments"]["password"] == "[REDACTED]"
    
    def test_audit_decorator_with_exception(self, mock_audit_logger):
        """Test audit decorator when function raises exception."""
        @audit_event(
            event_type=AuditEventType.USER_CREATED,
            message_template="User creation attempted"
        )
        def failing_function():
            raise ValueError("Something went wrong")
        
        with pytest.raises(ValueError):
            failing_function()
        
        # Should log both the original event and error event
        assert mock_audit_logger.log_event.call_count == 2
        
        # Check error event
        error_event = mock_audit_logger.log_event.call_args_list[1][0][0]
        assert error_event.event_type == AuditEventType.ERROR_OCCURRED
        assert "Something went wrong" in error_event.message


class TestAuditScope:
    """Test AuditScope context manager."""
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock audit logger for testing."""
        with patch('src.audit.decorators.audit_logger') as mock:
            yield mock
    
    def test_audit_scope_success(self, mock_audit_logger):
        """Test audit scope with successful operation."""
        with AuditScope("test_operation", "transaction", "user123"):
            # Simulate some work
            pass
        
        # Should log start and end events
        assert mock_audit_logger.log_event.call_count == 2
        
        start_event = mock_audit_logger.log_event.call_args_list[0][0][0]
        end_event = mock_audit_logger.log_event.call_args_list[1][0][0]
        
        assert "started" in start_event.message
        assert "completed successfully" in end_event.message
        assert end_event.metadata["result"] == "success"
    
    def test_audit_scope_with_exception(self, mock_audit_logger):
        """Test audit scope with exception."""
        with pytest.raises(ValueError):
            with AuditScope("test_operation", "transaction", "user123"):
                raise ValueError("Test error")
        
        # Should log start and end events
        assert mock_audit_logger.log_event.call_count == 2
        
        end_event = mock_audit_logger.log_event.call_args_list[1][0][0]
        assert "failed" in end_event.message
        assert end_event.metadata["result"] == "failure"
        assert "Test error" in end_event.metadata["error"]


class TestSecurityEventDetector:
    """Test SecurityEventDetector class."""
    
    def test_brute_force_detection(self):
        """Test brute force attack detection."""
        detector = SecurityEventDetector()
        
        with patch('src.audit.middleware.audit_logger') as mock_logger:
            # Simulate multiple failed login attempts
            for i in range(6):
                detector.analyze_login_attempt(
                    ip_address="192.168.1.100",
                    username="testuser",
                    success=False,
                    timestamp=1640995200 + i  # Sequential timestamps
                )
            
            # Should detect brute force after 5 failures
            mock_logger.log_suspicious_activity.assert_called()
            
            call_args = mock_logger.log_suspicious_activity.call_args
            assert call_args[1]["activity_type"] == "brute_force"
            assert call_args[1]["risk_score"] == 80
    
    def test_successful_login_clears_failures(self):
        """Test that successful login clears failed attempts."""
        detector = SecurityEventDetector()
        
        # Add some failed attempts
        for i in range(3):
            detector.analyze_login_attempt(
                ip_address="192.168.1.100",
                username="testuser",
                success=False,
                timestamp=1640995200 + i
            )
        
        # Successful login should clear failures
        detector.analyze_login_attempt(
            ip_address="192.168.1.100",
            username="testuser",
            success=True,
            timestamp=1640995300
        )
        
        assert "192.168.1.100" not in detector.failed_login_attempts


class TestAuditMiddleware:
    """Test AuditMiddleware class."""
    
    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        request = Mock()
        request.url.path = "/api/users"
        request.method = "GET"
        request.headers = {
            "user-agent": "Mozilla/5.0",
            "x-forwarded-for": "192.168.1.1"
        }
        request.query_params = {}
        request.client.host = "192.168.1.1"
        request.state = Mock()
        request.state.user = None
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create mock response."""
        response = Mock()
        response.status_code = 200
        response.headers = {}
        return response
    
    @pytest.mark.asyncio
    async def test_middleware_request_logging(self, mock_request, mock_response):
        """Test middleware request logging."""
        middleware = AuditMiddleware(
            app=Mock(),
            log_requests=True,
            log_responses=True,
            excluded_paths=set()
        )
        
        async def mock_call_next(request):
            return mock_response
        
        with patch('src.audit.middleware.audit_logger') as mock_logger:
            response = await middleware.dispatch(mock_request, mock_call_next)
            
            # Should log request and response
            assert mock_logger.log_event.call_count >= 2
            assert response.headers["X-Correlation-ID"]
            assert response.headers["X-Request-ID"]
    
    @pytest.mark.asyncio
    async def test_middleware_excluded_paths(self, mock_request, mock_response):
        """Test middleware excludes certain paths."""
        mock_request.url.path = "/health"
        
        middleware = AuditMiddleware(
            app=Mock(),
            log_requests=True,
            excluded_paths={"/health"}
        )
        
        async def mock_call_next(request):
            return mock_response
        
        with patch('src.audit.middleware.audit_logger') as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)
            
            # Should not log anything for excluded paths
            mock_logger.log_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_middleware_error_handling(self, mock_request):
        """Test middleware error handling."""
        middleware = AuditMiddleware(
            app=Mock(),
            log_errors=True,
            excluded_paths=set()
        )
        
        async def mock_call_next(request):
            raise ValueError("Test error")
        
        with patch('src.audit.middleware.audit_logger') as mock_logger:
            with pytest.raises(ValueError):
                await middleware.dispatch(mock_request, mock_call_next)
            
            # Should log the error
            mock_logger.log_event.assert_called()
            
            # Find the error event
            error_logged = False
            for call in mock_logger.log_event.call_args_list:
                event = call[0][0]
                if event.event_type == AuditEventType.ERROR_OCCURRED:
                    error_logged = True
                    assert "Test error" in event.message
                    break
            
            assert error_logged


class TestAuditIntegration:
    """Integration tests for audit system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_audit_flow(self):
        """Test complete audit flow from request to logging."""
        # This would be a more comprehensive integration test
        # that tests the entire audit pipeline
        pass
    
    def test_audit_log_format_compliance(self):
        """Test that audit logs meet compliance requirements."""
        # Test that logs contain required fields for compliance
        event = AuditEvent(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.LOW,
            message="User logged in",
            timestamp=datetime.utcnow(),
            user_id="user123",
            ip_address="192.168.1.1",
            correlation_id="corr-123"
        )
        
        event_dict = event.to_dict()
        
        # Check required compliance fields
        required_fields = [
            "event_type", "severity", "message", "timestamp",
            "user_id", "ip_address", "correlation_id"
        ]
        
        for field in required_fields:
            assert field in event_dict
            assert event_dict[field] is not None