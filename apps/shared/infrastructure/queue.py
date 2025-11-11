"""
Dramatiq message broker setup for background task queue

Usage:
    from apps.shared.infrastructure.queue import broker
    from dramatiq import actor

    @actor
    def process_image(image_url: str):
        # Background task logic
        ...

    # Enqueue task
    process_image.send(image_url="https://...")
"""

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import (
    AgeLimit,
    TimeLimit,
    Callbacks,
    Pipelines,
    Prometheus,
    Retries,
)
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend
import structlog

from config import settings

logger = structlog.get_logger(__name__)

# Create Redis backend for storing results
result_backend = RedisBackend(url=settings.REDIS_URL)

# Create Redis broker
broker = RedisBroker(url=settings.REDIS_URL)

# Add middleware
broker.add_middleware(
    # Store task results
    Results(backend=result_backend),

    # Retry failed tasks
    Retries(
        max_retries=settings.WORKER_MAX_RETRIES,
        min_backoff=1000,  # 1 second
        max_backoff=900000,  # 15 minutes
    ),

    # Time limits
    AgeLimit(max_age=3600000),  # 1 hour max age
    TimeLimit(time_limit=settings.COMFYUI_TIMEOUT * 1000),  # Convert to ms

    # Callbacks for success/failure
    Callbacks(),

    # Task pipelines
    Pipelines(),
)

# Add Prometheus metrics if enabled
if settings.METRICS_ENABLED:
    broker.add_middleware(Prometheus())

# Set as default broker
dramatiq.set_broker(broker)


# Logging actor for debugging
@dramatiq.actor
def log_task(level: str, message: str, **kwargs):
    """Simple logging task for testing queue"""
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(message, **kwargs)


def init_queue():
    """
    Initialize task queue.

    Usage:
        # Run once on app startup
        from apps.shared.infrastructure.queue import init_queue
        init_queue()
    """
    logger.info("queue_initializing", broker=broker.__class__.__name__)
    logger.info("queue_initialized")


def close_queue():
    """
    Close queue connections.

    Usage:
        # Run on app shutdown
        from apps.shared.infrastructure.queue import close_queue
        close_queue()
    """
    logger.info("queue_closing_connections")
    broker.close()
    logger.info("queue_connections_closed")


# Helper function to check if worker is healthy
def is_worker_healthy() -> bool:
    """
    Check if Dramatiq workers are running and healthy.

    Returns:
        True if workers are responding, False otherwise
    """
    try:
        # Send a test task
        result = log_task.send_with_options(
            args=("info", "health_check"),
            delay=0
        )

        # Wait for result (with timeout)
        result.get(block=True, timeout=5000)  # 5 seconds
        return True
    except Exception as e:
        logger.error("worker_health_check_failed", error=str(e))
        return False
