"""
Metrics endpoint for Prometheus monitoring.

This module provides the /metrics endpoint for Prometheus to scrape
application metrics.
"""

import time

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from src.monitoring.metrics import get_metrics_data, get_metrics_content_type
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    tags=["monitoring"],
    responses={
        200: {
            "description": "Prometheus metrics",
            "content": {"text/plain": {"example": "# HELP http_requests_total Total HTTP requests\n# TYPE http_requests_total counter\nhttp_requests_total{method=\"GET\",endpoint=\"/healthz\",status_code=\"200\"} 1.0"}},
        }
    },
)


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Get Prometheus metrics",
    description="Returns application metrics in Prometheus format for scraping",
    include_in_schema=False,  # Don't include in OpenAPI docs for security
)
async def get_metrics() -> Response:
    """
    Get Prometheus metrics endpoint.

    This endpoint returns application metrics in Prometheus text format
    for monitoring and alerting systems to scrape.

    Returns:
        Plain text response with Prometheus metrics
    """
    try:
        # Get metrics data
        metrics_data = get_metrics_data()

        # Return metrics with proper content type
        return PlainTextResponse(
            content=metrics_data,
            media_type=get_metrics_content_type(),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")

        # Return error metrics
        error_metrics = f"""# HELP metrics_generation_errors_total Total metrics generation errors
# TYPE metrics_generation_errors_total counter
metrics_generation_errors_total 1.0

# HELP metrics_last_error_timestamp_seconds Timestamp of last metrics error
# TYPE metrics_last_error_timestamp_seconds gauge
metrics_last_error_timestamp_seconds {int(time.time())}
"""

        return PlainTextResponse(
            content=error_metrics,
            media_type=get_metrics_content_type(),
            status_code=500,
        )
