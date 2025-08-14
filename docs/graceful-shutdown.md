# Graceful Shutdown

This document describes the graceful shutdown functionality implemented in the production API framework.

## Overview

The graceful shutdown system ensures that the application terminates cleanly when receiving shutdown signals (SIGTERM, SIGINT, SIGHUP), properly closing database connections, completing in-flight requests, and cleaning up resources.

## Features

### Signal Handling
- **SIGTERM**: Standard termination signal (sent by Docker, Kubernetes, etc.)
- **SIGINT**: Interrupt signal (Ctrl+C)
- **SIGHUP**: Hangup signal (terminal disconnect)

### Connection Management
- Tracks active HTTP requests
- Waits for in-flight requests to complete
- Cancels requests that exceed timeout
- Properly closes database connections

### Resource Cleanup
- Database connection pool cleanup
- Redis connection cleanup (when implemented)
- Prometheus metrics cleanup
- Sentry error tracking flush

### Timeout Handling
- Configurable shutdown timeout (default: 30 seconds)
- Graceful shutdown within timeout period
- Forced termination if timeout exceeded

## Configuration

### Environment Variables

```bash
# Shutdown timeout in seconds (default: 30)
SHUTDOWN_TIMEOUT=30

# Whether to wait for active connections (default: true)
SHUTDOWN_WAIT_FOR_CONNECTIONS=true

# Whether to force shutdown after timeout (default: true)
SHUTDOWN_FORCE_AFTER_TIMEOUT=true
```

### Configuration File

Add to `config/settings.toml`:

```toml
# Shutdown settings
shutdown_timeout = 30
shutdown_wait_for_connections = true
shutdown_force_after_timeout = true
```

## Implementation Details

### GracefulShutdown Class

The `GracefulShutdown` class in `src/main.py` handles the shutdown process:

```python
shutdown_handler = GracefulShutdown(shutdown_timeout=30)
```

Key methods:
- `signal_handler()`: Handles incoming signals
- `cleanup_resources()`: Performs resource cleanup
- `wait_for_shutdown()`: Waits for shutdown signal
- `add_connection()`: Tracks active connections

### Connection Tracking Middleware

The `ConnectionTrackingMiddleware` tracks active HTTP requests:

```python
from src.middleware.connection_tracking import ConnectionTrackingMiddleware

app.add_middleware(ConnectionTrackingMiddleware)
```

### Database Cleanup

Database connections are properly closed during shutdown:

```python
from src.database.config import close_database
await close_database()
```

## Usage in Docker

### Dockerfile Configuration

The Dockerfile is configured for proper signal handling:

```dockerfile
# Use proper signal handling
STOPSIGNAL SIGTERM

# Health check with custom script
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/health-check.py --timeout 5 || exit 1

# Start application using our main.py with graceful shutdown
CMD ["python", "-m", "src.main"]
```

### Docker Compose

Configure shutdown timeout in docker-compose.yml:

```yaml
services:
  api:
    build: .
    environment:
      - SHUTDOWN_TIMEOUT=30
    stop_grace_period: 35s  # Slightly longer than shutdown timeout
```

### Kubernetes

Configure termination grace period:

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      terminationGracePeriodSeconds: 35  # Slightly longer than shutdown timeout
      containers:
      - name: api
        env:
        - name: SHUTDOWN_TIMEOUT
          value: "30"
```

## Testing

### Unit Tests

Run the graceful shutdown unit tests:

```bash
python -m pytest tests/unit/test_graceful_shutdown.py -v
```

### Integration Tests

Run the integration tests:

```bash
python -m pytest tests/integration/test_graceful_shutdown_integration.py -v
```

### Manual Testing

Use the test script to verify graceful shutdown:

```bash
python scripts/test-graceful-shutdown.py
```

### Health Check Testing

Test the health check script:

```bash
# Basic health check
python scripts/health-check.py

# Wait for shutdown
python scripts/health-check.py --wait-shutdown 30
```

## Monitoring

### Logs

The graceful shutdown process generates structured logs:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Received SIGTERM, initiating graceful shutdown...",
  "event_type": "shutdown_initiated"
}
```

### Metrics

Shutdown metrics are tracked:
- `shutdown_duration_seconds`: Time taken for shutdown
- `active_connections_at_shutdown`: Number of active connections during shutdown
- `forced_shutdown_total`: Number of forced shutdowns due to timeout

## Best Practices

### Application Code

1. **Use async/await**: Ensure all I/O operations are async
2. **Handle cancellation**: Properly handle `asyncio.CancelledError`
3. **Cleanup resources**: Close files, connections, etc. in finally blocks
4. **Avoid blocking operations**: Don't use blocking I/O during shutdown

### Deployment

1. **Set appropriate timeouts**: Configure shutdown timeout based on your application needs
2. **Monitor shutdown time**: Track how long shutdowns take
3. **Test regularly**: Verify graceful shutdown works in your environment
4. **Use health checks**: Implement proper health check endpoints

### Container Orchestration

1. **Configure grace periods**: Set termination grace period longer than shutdown timeout
2. **Use proper signals**: Ensure orchestrator sends SIGTERM first
3. **Monitor pod termination**: Watch for pods that don't terminate gracefully
4. **Implement readiness probes**: Use readiness probes to stop traffic before shutdown

## Troubleshooting

### Common Issues

1. **Shutdown timeout exceeded**
   - Check for blocking operations
   - Increase shutdown timeout
   - Review active connections at shutdown

2. **Database connections not closing**
   - Verify database cleanup is called
   - Check for hanging transactions
   - Review connection pool configuration

3. **Requests not completing**
   - Check request timeout settings
   - Review middleware order
   - Verify connection tracking

### Debug Logging

Enable debug logging for shutdown process:

```bash
export LOG_LEVEL=DEBUG
```

### Health Check Debugging

Use verbose health check for debugging:

```bash
python scripts/health-check.py --verbose
```

## Examples

### Basic Usage

```python
from src.main import GracefulShutdown, setup_signal_handlers

# Create shutdown handler
shutdown_handler = GracefulShutdown(shutdown_timeout=30)

# Set up signal handlers
setup_signal_handlers(shutdown_handler)

# Your application code here...

# Wait for shutdown signal
await shutdown_handler.wait_for_shutdown()

# Perform cleanup
await shutdown_handler.cleanup_resources()
```

### Custom Cleanup

```python
class CustomGracefulShutdown(GracefulShutdown):
    async def _cleanup_other_resources(self):
        # Call parent cleanup
        await super()._cleanup_other_resources()
        
        # Add custom cleanup
        await self._cleanup_custom_resources()
    
    async def _cleanup_custom_resources(self):
        # Your custom cleanup code here
        pass
```

### Testing Shutdown

```python
import signal
import asyncio

async def test_shutdown():
    shutdown_handler = GracefulShutdown(shutdown_timeout=5)
    
    # Simulate shutdown signal
    shutdown_handler.signal_handler(signal.SIGTERM, None)
    
    # Perform cleanup
    await shutdown_handler.cleanup_resources()
    
    assert shutdown_handler.shutdown is True
```

## References

- [Docker STOPSIGNAL documentation](https://docs.docker.com/engine/reference/builder/#stopsignal)
- [Kubernetes Pod Lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Uvicorn Deployment](https://www.uvicorn.org/deployment/)