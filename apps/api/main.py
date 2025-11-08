"""
ComfyUI API Service
===================

A FastAPI-based REST API wrapper for ComfyUI image generation.

This service provides a production-ready API interface for ComfyUI,
enabling programmatic access to AI image generation capabilities.
"""

import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .routers import generate, health, jobs, websocket, metrics, admin, monitoring
from .middleware.request_id import RequestIDMiddleware
from .middleware.limit_upload_size import LimitUploadSizeMiddleware
from .middleware.version_headers import VersionHeadersMiddleware
from .middleware.rate_limit import RateLimitMiddleware
from .services.redis_client import redis_client
from .services.job_queue import job_queue
from .config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the FastAPI application.

    Handles startup and shutdown events for:
    - Redis connection
    - ARQ job queue
    - Storage client initialization
    """
    # Startup
    logger.info("Starting ComfyUI API Service...")

    # Connect to Redis
    if settings.jobs_enabled:
        try:
            await redis_client.connect()
            logger.info("✓ Connected to Redis")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Redis: {e}")
            logger.warning("Job queue features will be unavailable")

        # Connect to ARQ (job queue)
        try:
            await job_queue.connect()
            logger.info("✓ Connected to ARQ job queue")
        except Exception as e:
            logger.error(f"✗ Failed to connect to ARQ: {e}")
            logger.warning("Job submission will be unavailable")
    else:
        logger.info("Job queue disabled (jobs_enabled=False)")

    logger.info("API documentation available at /docs")
    logger.info(f"Metrics available at /metrics")
    if settings.websocket_enabled:
        logger.info(f"WebSocket available at /ws/jobs/{{job_id}}")

    yield

    # Shutdown
    logger.info("Shutting down ComfyUI API Service...")

    # Disconnect from services
    if settings.jobs_enabled:
        try:
            await job_queue.disconnect()
            logger.info("✓ Disconnected from ARQ")
        except Exception as e:
            logger.error(f"Error disconnecting from ARQ: {e}")

        try:
            await redis_client.disconnect()
            logger.info("✓ Disconnected from Redis")
        except Exception as e:
            logger.error(f"Error disconnecting from Redis: {e}")

    logger.info("Shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="ComfyUI API Service",
    description="""
    # ComfyUI API Service

    A production-ready REST API wrapper for ComfyUI image generation.

    ## Features

    - **Async Job Queue**: Submit jobs, get job_id immediately (202 Accepted)
    - **Real-time Progress**: WebSocket updates during generation
    - **Image Generation**: Generate images from text prompts using various models
    - **Batch Processing**: Generate multiple images in a single request
    - **Idempotency**: Prevent duplicate work with Idempotency-Key header
    - **Artifact Storage**: Secure presigned URLs for generated images
    - **Health Monitoring**: Check service status and available models
    - **Metrics**: Prometheus metrics for observability

    ## Getting Started

    ### Synchronous (Simple)
    1. Check service health: `GET /health`
    2. List available models: `GET /models`
    3. Generate an image: `POST /api/v1/generate` (waits for completion)

    ### Asynchronous (Recommended)
    1. Submit job: `POST /api/v1/jobs` (returns job_id immediately)
    2. Check status: `GET /api/v1/jobs/{job_id}` (poll or use WebSocket)
    3. Download image: Use presigned URL from result

    ## Authentication

    Currently, no authentication is required (development mode).
    In production, use API keys or JWT tokens.

    ## Rate Limits

    No rate limits currently enforced (development mode).
    In production, rate limits are per-token and tier-based.

    ## Support

    - Documentation: See endpoints below
    - Issues: GitHub repository
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "ComfyUI API Service",
        "url": "https://github.com/ApeNIG/comfy-api-service"
    },
    license_info={
        "name": "MIT"
    }
)

# Add middleware (order matters - first added = outermost)
# 1. Request ID tracking (outermost - needs to wrap everything)
app.add_middleware(RequestIDMiddleware)

# 2. Version headers
app.add_middleware(VersionHeadersMiddleware, version="1.0.1", service_name="ComfyUI API Service")

# 3. Rate limiting (before auth, needs user info)
app.add_middleware(RateLimitMiddleware)

# 4. Upload size limits
app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=10_485_760)  # 10MB

# 5. CORS (allow cross-origin requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(generate.router)  # Synchronous endpoints (backwards compatible)
app.include_router(jobs.router)  # Async job queue endpoints
app.include_router(websocket.router)  # WebSocket for real-time progress
app.include_router(metrics.router)  # Prometheus metrics
app.include_router(admin.router)  # Admin endpoints for user/key management
app.include_router(monitoring.router)  # Cost tracking and monitoring


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.

    Catches all unhandled exceptions and returns a consistent error response
    with request tracking information.
    """
    # Get request ID from request state
    request_id = getattr(request.state, "request_id", "unknown")

    # Log the exception with context
    logger.exception(
        f"Unhandled exception",
        extra={
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "error_type": type(exc).__name__
        }
    )

    # Return consistent error response
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": str(exc) if logger.level == logging.DEBUG else None,
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        headers={"X-Request-ID": request_id}
    )


# Health check for backwards compatibility
@app.get("/ping", include_in_schema=False)
async def ping():
    """Legacy health check endpoint."""
    return {"ok": True}
