# Multi-stage Dockerfile for production-ready FastAPI application
# Build stage - Install dependencies and prepare application
FROM python:3.11-slim as builder

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install Poetry and export dependencies
RUN pip install poetry==1.6.1 && \
    poetry config virtualenvs.create false && \
    poetry export -f requirements.txt --output requirements.txt --without-hashes

# Production stage - Minimal runtime image
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/app/.local/bin:$PATH"

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements from builder stage
COPY --from=builder /app/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY config/ ./config/
COPY scripts/docker-entrypoint.sh ./scripts/
COPY scripts/health-check.py ./scripts/

# Create necessary directories and set permissions
RUN mkdir -p logs && \
    chmod +x scripts/docker-entrypoint.sh && \
    chmod +x scripts/health-check.py && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check using custom script
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/health-check.py --timeout 5 || exit 1

# Signal handling and graceful shutdown
STOPSIGNAL SIGTERM

# Use entrypoint script for proper signal handling
ENTRYPOINT ["./scripts/docker-entrypoint.sh"]

# Start application using our main.py with graceful shutdown
CMD ["python", "-m", "src.main"]