#!/bin/bash
# Docker entrypoint script with proper signal handling and graceful shutdown

set -e

# Function to handle shutdown signals
shutdown() {
    echo "Received shutdown signal, gracefully shutting down..."
    
    # Send SIGTERM to the main process
    if [ -n "$MAIN_PID" ]; then
        echo "Sending SIGTERM to main process (PID: $MAIN_PID)..."
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        
        # Get shutdown timeout from environment or use default
        local shutdown_timeout=${SHUTDOWN_TIMEOUT:-30}
        echo "Waiting up to ${shutdown_timeout} seconds for graceful shutdown..."
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$MAIN_PID" 2>/dev/null && [ $count -lt $shutdown_timeout ]; do
            sleep 1
            count=$((count + 1))
            
            # Show progress every 5 seconds
            if [ $((count % 5)) -eq 0 ]; then
                echo "Still waiting for shutdown... (${count}/${shutdown_timeout}s)"
            fi
        done
        
        # Check if process is still running
        if kill -0 "$MAIN_PID" 2>/dev/null; then
            echo "Graceful shutdown timeout exceeded, force killing main process..."
            kill -KILL "$MAIN_PID" 2>/dev/null || true
            
            # Wait a bit more for force kill to take effect
            sleep 2
            
            if kill -0 "$MAIN_PID" 2>/dev/null; then
                echo "Warning: Process still running after force kill"
            else
                echo "Process terminated after force kill"
            fi
        else
            echo "Graceful shutdown completed successfully"
        fi
    fi
    
    echo "Container shutdown complete"
    exit 0
}

# Trap shutdown signals
trap shutdown SIGTERM SIGINT SIGQUIT

# Wait for database to be ready
wait_for_db() {
    echo "Waiting for database to be ready..."
    
    # Extract database connection details from DATABASE_URL
    # Format: postgresql+asyncpg://user:pass@host:port/db
    if [ -n "$DATABASE_URL" ]; then
        # Simple check using python
        python -c "
import asyncio
import asyncpg
import os
import sys
from urllib.parse import urlparse

async def check_db():
    try:
        url = os.environ.get('DATABASE_URL', '')
        if not url:
            return True
        
        # Parse URL and convert to asyncpg format
        parsed = urlparse(url)
        if parsed.scheme == 'postgresql+asyncpg':
            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:] if parsed.path else 'postgres'
            )
            await conn.close()
            print('Database connection successful')
            return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False

if not asyncio.run(check_db()):
    sys.exit(1)
" || {
            echo "Database connection check failed, retrying in 5 seconds..."
            sleep 5
            return 1
        }
    fi
}

# Wait for database with retries
retry_count=0
max_retries=12  # 1 minute total (5 seconds * 12)

while ! wait_for_db && [ $retry_count -lt $max_retries ]; do
    retry_count=$((retry_count + 1))
    echo "Database not ready, attempt $retry_count/$max_retries"
done

if [ $retry_count -eq $max_retries ]; then
    echo "Database connection failed after $max_retries attempts"
    exit 1
fi

# Run database migrations if requested
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "Running database migrations..."
    python -m alembic upgrade head
fi

# Start the main application
echo "Starting application..."

# Execute the main command and capture PID
exec "$@" &
MAIN_PID=$!

# Wait for the main process
wait $MAIN_PID