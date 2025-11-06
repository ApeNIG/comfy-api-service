"""Request ID middleware for request tracking."""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request.

    - Accepts X-Request-ID from client if provided
    - Generates UUID if not provided
    - Adds X-Request-ID to response headers
    - Stores request_id in request.state for use in handlers
    - Logs request_id with each request

    Usage:
        app.add_middleware(RequestIDMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and add request ID."""
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.request_id = request_id

        # Log the request
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client": request.client.host if request.client else None
            }
        )

        # Process request
        try:
            response = await call_next(request)

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            # Log completion
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "status_code": response.status_code
                }
            )

            return response

        except Exception as e:
            # Log error with request ID
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
