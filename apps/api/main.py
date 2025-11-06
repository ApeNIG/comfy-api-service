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

from .routers import generate, health
from .middleware.request_id import RequestIDMiddleware
from .middleware.limit_upload_size import LimitUploadSizeMiddleware
from .middleware.version_headers import VersionHeadersMiddleware

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

    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting ComfyUI API Service...")
    logger.info("API documentation available at /docs")
    yield
    # Shutdown
    logger.info("Shutting down ComfyUI API Service...")


# Initialize FastAPI application
app = FastAPI(
    title="ComfyUI API Service",
    description="""
    # ComfyUI API Service

    A production-ready REST API wrapper for ComfyUI image generation.

    ## Features

    - **Image Generation**: Generate images from text prompts using various models
    - **Batch Processing**: Generate multiple images in a single request
    - **Health Monitoring**: Check service status and available models
    - **Async Operations**: Non-blocking I/O for high performance

    ## Getting Started

    1. Check service health: `GET /health`
    2. List available models: `GET /models`
    3. Generate an image: `POST /api/v1/generate`

    ## Authentication

    Currently, no authentication is required (development mode).

    ## Rate Limits

    No rate limits currently enforced (development mode).

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

# 3. Upload size limits
app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=10_485_760)  # 10MB

# 4. CORS (allow cross-origin requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(generate.router)


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
