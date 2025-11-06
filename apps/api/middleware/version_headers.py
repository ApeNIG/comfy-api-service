"""Middleware to add API version headers to responses."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class VersionHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add API version information to response headers.

    Adds:
    - X-API-Version: API version number
    - X-Service-Name: Service name

    This helps clients know which version of the API they're interacting with
    and makes debugging easier.

    Usage:
        app.add_middleware(VersionHeadersMiddleware, version="1.0.0")
    """

    def __init__(self, app, version: str = "1.0.0", service_name: str = "ComfyUI API Service"):
        """
        Initialize middleware.

        Args:
            app: FastAPI application instance
            version: API version string
            service_name: Name of the service
        """
        super().__init__(app)
        self.version = version
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add version headers to response."""
        response = await call_next(request)

        # Add version headers
        response.headers["X-API-Version"] = self.version
        response.headers["X-Service-Name"] = self.service_name

        return response
