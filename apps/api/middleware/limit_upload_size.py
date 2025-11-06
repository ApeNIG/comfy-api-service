"""Middleware to limit request body size."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce maximum request body size.

    Prevents clients from sending excessively large requests that could
    consume server resources or cause out-of-memory errors.

    Args:
        max_upload_size: Maximum size in bytes (default: 10MB)

    Usage:
        app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=10485760)
    """

    def __init__(self, app, max_upload_size: int = 10_485_760):
        """
        Initialize middleware.

        Args:
            app: FastAPI application instance
            max_upload_size: Max size in bytes (default 10MB)
        """
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        """Check request size before processing."""
        # Get content length from headers
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)

            if content_length > self.max_upload_size:
                request_id = getattr(request.state, "request_id", "unknown")

                logger.warning(
                    f"Request body too large",
                    extra={
                        "request_id": request_id,
                        "content_length": content_length,
                        "max_allowed": self.max_upload_size,
                        "url": str(request.url)
                    }
                )

                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"Request body too large. Maximum size is {self.max_upload_size} bytes ({self.max_upload_size / 1024 / 1024:.1f}MB)",
                            "details": {
                                "content_length": content_length,
                                "max_size": self.max_upload_size
                            },
                            "request_id": request_id
                        }
                    },
                    headers={"X-Request-ID": request_id} if request_id != "unknown" else {}
                )

        return await call_next(request)
