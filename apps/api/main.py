"""
ComfyUI API Service
===================

A FastAPI-based REST API wrapper for ComfyUI image generation.

This service provides a production-ready API interface for ComfyUI,
enabling programmatic access to AI image generation capabilities.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .routers import generate, health

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

# Configure CORS
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
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors.
    """
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": str(exc) if logger.level == logging.DEBUG else None
            }
        }
    )


# Health check for backwards compatibility
@app.get("/ping", include_in_schema=False)
async def ping():
    """Legacy health check endpoint."""
    return {"ok": True}
