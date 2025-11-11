"""
Structured logging setup using structlog

Usage:
    from apps.shared.utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("user_created", user_id=user.id, email=user.email)
    logger.error("process_failed", error=str(e), job_id=job_id)
"""

import logging
import sys
import structlog
from structlog.types import FilteringBoundLogger
from typing import Any

from config import settings


def configure_logging():
    """
    Configure structured logging for the application.

    Call once on app startup:
        from apps.shared.utils.logger import configure_logging
        configure_logging()
    """

    # Determine processors based on environment
    if settings.LOG_FORMAT == "json":
        # JSON logging for production
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console logging for development
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger

    Usage:
        logger = get_logger(__name__)
        logger.info("user_login", user_id=user.id, ip=request.client.host)
    """
    return structlog.get_logger(name)


# Request ID middleware for FastAPI
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid

# Context variable for request ID
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request ID to all log messages.

    Usage:
        from fastapi import FastAPI
        from apps.shared.utils.logger import RequestIDMiddleware

        app = FastAPI()
        app.add_middleware(RequestIDMiddleware)
    """

    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in context
        request_id_ctx.set(request_id)

        # Bind to structlog context
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Clear context
            structlog.contextvars.clear_contextvars()


# Logging middleware for requests
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests.

    Usage:
        from fastapi import FastAPI
        from apps.shared.utils.logger import RequestLoggingMiddleware

        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
    """

    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger(__name__)

    async def dispatch(self, request: Request, call_next):
        # Log request
        self.logger.info(
            "http_request_started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
        )

        try:
            response: Response = await call_next(request)

            # Log response
            self.logger.info(
                "http_request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )

            return response

        except Exception as e:
            # Log error
            self.logger.error(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                exc_info=True,
            )
            raise


# Helper function to log function execution
def log_execution(logger_name: str = None):
    """
    Decorator to log function execution.

    Usage:
        @log_execution()
        async def process_image(image_url: str):
            ...

        # Logs:
        # - process_image_started
        # - process_image_completed (with duration)
        # - process_image_failed (on error)
    """
    import time
    from functools import wraps

    def decorator(func):
        logger = get_logger(logger_name or func.__module__)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(f"{func_name}_started", args=args, kwargs=kwargs)

            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # ms

                logger.info(
                    f"{func_name}_completed",
                    duration_ms=duration,
                )
                return result

            except Exception as e:
                duration = (time.time() - start_time) * 1000  # ms
                logger.error(
                    f"{func_name}_failed",
                    duration_ms=duration,
                    error=str(e),
                    exc_info=True,
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.info(f"{func_name}_started", args=args, kwargs=kwargs)

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = (time.time() - start_time) * 1000  # ms

                logger.info(
                    f"{func_name}_completed",
                    duration_ms=duration,
                )
                return result

            except Exception as e:
                duration = (time.time() - start_time) * 1000  # ms
                logger.error(
                    f"{func_name}_failed",
                    duration_ms=duration,
                    error=str(e),
                    exc_info=True,
                )
                raise

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
