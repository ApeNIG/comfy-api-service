"""
Global error handling middleware

Catches all unhandled exceptions and returns structured error responses.
"""

import traceback
from typing import Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from apps.shared.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware:
    """
    Middleware that catches all exceptions and returns structured JSON errors.

    Benefits:
    - Consistent error format across entire API
    - Automatic logging of errors with request context
    - Prevents leaking sensitive error details to clients
    - Proper HTTP status codes for different error types
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except ValidationError as exc:
            # Pydantic validation errors (400 Bad Request)
            logger.warning(
                "validation_error",
                path=request.url.path,
                method=request.method,
                errors=exc.errors(),
            )

            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Validation Error",
                    "detail": exc.errors(),
                    "path": request.url.path,
                },
            )

        except SQLAlchemyError as exc:
            # Database errors (500 Internal Server Error)
            logger.error(
                "database_error",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_info=True,
            )

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Database Error",
                    "detail": "An error occurred while accessing the database",
                    "path": request.url.path,
                },
            )

        except ValueError as exc:
            # Value errors (400 Bad Request)
            logger.warning(
                "value_error",
                path=request.url.path,
                method=request.method,
                error=str(exc),
            )

            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Invalid Value",
                    "detail": str(exc),
                    "path": request.url.path,
                },
            )

        except PermissionError as exc:
            # Permission errors (403 Forbidden)
            logger.warning(
                "permission_error",
                path=request.url.path,
                method=request.method,
                error=str(exc),
            )

            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Permission Denied",
                    "detail": str(exc),
                    "path": request.url.path,
                },
            )

        except Exception as exc:
            # Catch-all for unexpected errors (500 Internal Server Error)
            logger.error(
                "unhandled_exception",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                error_type=type(exc).__name__,
                traceback=traceback.format_exc(),
                exc_info=True,
            )

            # Don't leak error details in production
            from config import settings

            if settings.DEBUG:
                detail = f"{type(exc).__name__}: {str(exc)}"
            else:
                detail = "An unexpected error occurred"

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal Server Error",
                    "detail": detail,
                    "path": request.url.path,
                },
            )


def add_error_handler_middleware(app):
    """
    Add error handler middleware to FastAPI app.

    Usage:
        from fastapi import FastAPI
        from apps.creator.middleware.error_handler import add_error_handler_middleware

        app = FastAPI()
        add_error_handler_middleware(app)
    """
    app.add_middleware(ErrorHandlerMiddleware)
