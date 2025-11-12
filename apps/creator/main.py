"""
Creator Product - Main Application
===================================

Beautiful, delightful UX for indie creators to automate image workflows.

Features:
- Google Drive integration ("drop file, get result")
- One-click authentication with Google OAuth
- Real-time job progress updates
- Beautiful glassmorphism UI
- Smart defaults and friendly error messages
- Usage-based pricing (Free, Creator, Studio)

This is the indie-friendly SaaS product built on top of ComfyUI.
"""

import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from apps.creator.routers import auth
from apps.web.routers import pages
from apps.shared.infrastructure.database import engine
from apps.shared.models.base import Base
from config import settings

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for Creator application.

    Handles:
    - Database connection and table creation
    - Cache initialization
    - Service health checks
    """
    # Startup
    logger.info("🚀 Starting Creator...")

    # Create database tables if they don't exist
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Database tables initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}")
        raise

    logger.info(f"📖 API docs available at {settings.FRONTEND_URL}/docs")
    logger.info(f"🎨 Web UI available at {settings.FRONTEND_URL}")
    logger.info(f"🔐 OAuth redirect: {settings.GOOGLE_REDIRECT_URI}")

    yield

    # Shutdown
    logger.info("Shutting down Creator...")
    logger.info("✓ Shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="Creator",
    description="""
    # Creator - Image Automation for Indie Creators

    Beautiful, delightful image automation powered by AI.

    ## How it works

    1. **Connect your Google Drive** - One-click OAuth authentication
    2. **Choose a folder to watch** - We'll monitor it for new uploads
    3. **Drop files** - Upload images to your watched folder
    4. **Get results automatically** - Processed images appear in your Drive

    ## Features

    ✨ **One-Click Setup**
    - Google OAuth (no password to remember)
    - Automatic folder creation
    - Smart defaults everywhere

    🎨 **Beautiful UX**
    - Real-time progress updates
    - Friendly error messages
    - Celebration animations
    - Glassmorphism design

    📊 **Transparent Pricing**
    - Free: 10 jobs/month (7-day trial)
    - Creator: 100 jobs/month ($9/mo)
    - Studio: 500 jobs/month ($29/mo)

    💪 **Powerful**
    - ComfyUI workflows
    - Custom models
    - Batch processing
    - WebSocket progress streaming

    ## Getting Started

    1. Sign up: [/signup](/signup)
    2. Connect Drive: [/onboarding](/onboarding)
    3. Upload image: Drop in watched folder
    4. Done! Result appears automatically

    ## Support

    Need help? Contact us at support@creator.com
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    contact={
        "name": "Creator Support",
        "email": "support@creator.com",
    },
)

# Add middleware (order matters!)

# 1. CORS (allow frontend to communicate with backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Register routers

# Web pages (HTML)
app.include_router(pages.router, tags=["Web Pages"])

# API routes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# TODO: Add more routers as we build them
# app.include_router(drive.router, prefix="/drive", tags=["Google Drive"])
# app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
# app.include_router(subscriptions.router, prefix="/subscriptions", tags=["Subscriptions"])

# Serve static assets (generated images, CSS, JS, etc.)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler.

    Provides friendly error messages and logs for debugging.
    """
    logger.exception(
        f"Unhandled exception",
        extra={
            "method": request.method,
            "url": str(request.url),
            "error_type": type(exc).__name__
        }
    )

    # Friendly error response
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Oops! Something went wrong on our end. We're looking into it.",
            "error": {
                "type": type(exc).__name__,
                "details": str(exc) if settings.DEBUG else None,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }
    )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint.

    Redirects to landing page.
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/login")


# Health check
@app.get("/health", include_in_schema=False)
async def health():
    """
    Health check endpoint.

    Returns service status and version.
    """
    return {
        "status": "healthy",
        "service": "Creator",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
    }
