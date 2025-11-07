"""
Prometheus metrics endpoint for observability.

Exposes metrics in Prometheus text format for scraping.
"""

from fastapi import APIRouter
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"])

# Module-level flag to prevent duplicate metric registration
_metrics_registered = False

# Declare metric variables
jobs_total = None
jobs_created = None
job_duration_seconds = None
queue_depth = None
active_workers = None
jobs_in_progress = None
http_requests_total = None
http_request_duration_seconds = None
storage_uploads_total = None
storage_upload_bytes = None
redis_operations_total = None
comfyui_requests_total = None
comfyui_request_duration_seconds = None


def _ensure_metrics_registered():
    """Ensure metrics are registered exactly once."""
    global _metrics_registered
    global jobs_total, jobs_created, job_duration_seconds, queue_depth
    global active_workers, jobs_in_progress, http_requests_total
    global http_request_duration_seconds, storage_uploads_total
    global storage_upload_bytes, redis_operations_total
    global comfyui_requests_total, comfyui_request_duration_seconds

    if _metrics_registered:
        return

    try:
        # Job counters
        jobs_total = Counter(
            "comfyui_jobs_total",
            "Total number of jobs by status",
            ["status"]
        )

        jobs_created = Counter(
            "comfyui_jobs_created_total",
            "Total number of jobs created"
        )

        # Job duration histogram
        job_duration_seconds = Histogram(
            "comfyui_job_duration_seconds",
            "Job processing duration in seconds",
            buckets=[5, 10, 30, 60, 120, 300, 600, 1200, 1800]  # 5s to 30min
        )

        # Queue depth gauge
        queue_depth = Gauge(
            "comfyui_queue_depth",
            "Number of jobs waiting in queue"
        )

        # Active workers gauge
        active_workers = Gauge(
            "comfyui_active_workers",
            "Number of active worker processes"
        )

        # In-progress jobs gauge
        jobs_in_progress = Gauge(
            "comfyui_jobs_in_progress",
            "Number of jobs currently being processed"
        )

        # API request metrics
        http_requests_total = Counter(
            "comfyui_http_requests_total",
            "Total HTTP requests by method, endpoint, and status",
            ["method", "endpoint", "status"]
        )

        http_request_duration_seconds = Histogram(
            "comfyui_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        # Storage metrics
        storage_uploads_total = Counter(
            "comfyui_storage_uploads_total",
            "Total number of artifact uploads",
            ["status"]  # success, failure
        )

        storage_upload_bytes = Counter(
            "comfyui_storage_upload_bytes_total",
            "Total bytes uploaded to storage"
        )

        # Redis metrics
        redis_operations_total = Counter(
            "comfyui_redis_operations_total",
            "Total Redis operations by type and status",
            ["operation", "status"]
        )

        # ComfyUI backend metrics
        comfyui_requests_total = Counter(
            "comfyui_backend_requests_total",
            "Total requests to ComfyUI backend by status",
            ["status"]
        )

        comfyui_request_duration_seconds = Histogram(
            "comfyui_backend_request_duration_seconds",
            "ComfyUI backend request duration",
            buckets=[1, 5, 10, 30, 60, 120, 300]
        )

        _metrics_registered = True
        logger.info("Prometheus metrics registered")

    except ValueError as e:
        # Metrics already registered (from another import), skip silently
        logger.debug(f"Metrics already registered: {e}")
        _metrics_registered = True


# Register metrics on module import
_ensure_metrics_registered()


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="""
    Prometheus metrics endpoint for monitoring and alerting.

    Returns metrics in Prometheus text format.

    **Available Metrics:**

    **Job Metrics:**
    - `comfyui_jobs_total{status}` - Total jobs by status
    - `comfyui_jobs_created_total` - Total jobs created
    - `comfyui_job_duration_seconds` - Job processing duration histogram
    - `comfyui_queue_depth` - Current queue depth
    - `comfyui_jobs_in_progress` - Jobs currently processing
    - `comfyui_active_workers` - Active worker count

    **API Metrics:**
    - `comfyui_http_requests_total{method, endpoint, status}` - HTTP requests
    - `comfyui_http_request_duration_seconds{method, endpoint}` - Request duration

    **Storage Metrics:**
    - `comfyui_storage_uploads_total{status}` - Upload operations
    - `comfyui_storage_upload_bytes_total` - Bytes uploaded

    **Backend Metrics:**
    - `comfyui_backend_requests_total{status}` - ComfyUI requests
    - `comfyui_backend_request_duration_seconds` - Backend duration

    **Redis Metrics:**
    - `comfyui_redis_operations_total{operation, status}` - Redis ops

    **Prometheus Configuration:**
    ```yaml
    scrape_configs:
      - job_name: 'comfyui-api'
        scrape_interval: 15s
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/metrics'
    ```

    **Grafana Dashboard:**
    Import dashboard ID: (TODO: publish to grafana.com)
    """,
    responses={
        200: {
            "description": "Metrics in Prometheus text format",
            "content": {
                "text/plain; version=0.0.4": {
                    "example": """# HELP comfyui_jobs_total Total number of jobs by status
# TYPE comfyui_jobs_total counter
comfyui_jobs_total{status="queued"} 10
comfyui_jobs_total{status="running"} 2
comfyui_jobs_total{status="succeeded"} 45
comfyui_jobs_total{status="failed"} 3
"""
                }
            }
        }
    }
)
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.

    This endpoint should be called periodically by Prometheus
    (typically every 15-60 seconds).
    """
    try:
        # Ensure metrics are registered
        _ensure_metrics_registered()

        # Generate metrics in Prometheus format
        metrics_output = generate_latest()

        return Response(
            content=metrics_output,
            media_type=CONTENT_TYPE_LATEST
        )

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}", exc_info=True)
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type=CONTENT_TYPE_LATEST,
            status_code=500
        )


# Helper functions to update metrics (used by other modules)

def record_job_created():
    """Increment jobs_created counter."""
    _ensure_metrics_registered()
    jobs_created.inc()


def record_job_status(status: str):
    """Increment jobs_total counter for given status."""
    _ensure_metrics_registered()
    jobs_total.labels(status=status).inc()


def record_job_duration(duration_seconds: float):
    """Record job processing duration."""
    _ensure_metrics_registered()
    job_duration_seconds.observe(duration_seconds)


def set_queue_depth(depth: int):
    """Update queue depth gauge."""
    _ensure_metrics_registered()
    queue_depth.set(depth)


def set_jobs_in_progress(count: int):
    """Update in-progress jobs gauge."""
    _ensure_metrics_registered()
    jobs_in_progress.set(count)


def set_active_workers(count: int):
    """Update active workers gauge."""
    _ensure_metrics_registered()
    active_workers.set(count)


def record_http_request(method: str, endpoint: str, status: int):
    """Record HTTP request."""
    _ensure_metrics_registered()
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()


def record_http_duration(method: str, endpoint: str, duration_seconds: float):
    """Record HTTP request duration."""
    _ensure_metrics_registered()
    http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration_seconds)


def record_storage_upload(success: bool, bytes_uploaded: int = 0):
    """Record storage upload."""
    _ensure_metrics_registered()
    status_label = "success" if success else "failure"
    storage_uploads_total.labels(status=status_label).inc()
    if success and bytes_uploaded > 0:
        storage_upload_bytes.inc(bytes_uploaded)


def record_redis_operation(operation: str, success: bool):
    """Record Redis operation."""
    _ensure_metrics_registered()
    status_label = "success" if success else "failure"
    redis_operations_total.labels(operation=operation, status=status_label).inc()


def record_comfyui_request(status: str, duration_seconds: float = None):
    """Record ComfyUI backend request."""
    _ensure_metrics_registered()
    comfyui_requests_total.labels(status=status).inc()
    if duration_seconds is not None:
        comfyui_request_duration_seconds.observe(duration_seconds)
