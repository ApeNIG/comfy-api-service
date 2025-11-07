"""
Rate limiting middleware with X-RateLimit-* headers.

Applies rate limits before request processing and adds
standard rate limit headers to all responses.
"""

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

from ..services.rate_limiter import get_rate_limiter, RateLimitInfo
from ..services.auth_service import get_auth_service
from ..config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces rate limits and adds rate limit headers.

    Applied globally to all authenticated requests.
    """

    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = get_rate_limiter()
        self.auth_service = get_auth_service()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        1. Extract user from Authorization header (if present)
        2. Check rate limit
        3. If denied, return 429 Too Many Requests
        4. If allowed, process request and add rate limit headers
        """
        # Skip rate limiting if disabled
        if not settings.rate_limit_enabled:
            response = await call_next(request)
            return response

        # Extract API key from Authorization header
        auth_header = request.headers.get("Authorization", "")
        api_key = None

        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]  # Remove "Bearer " prefix

        # If no API key, allow request (unauthenticated endpoints)
        if not api_key:
            response = await call_next(request)
            return response

        # Validate API key and get user
        try:
            user = await self.auth_service.validate_api_key(api_key)

            if not user:
                # Invalid key - let auth middleware handle it
                response = await call_next(request)
                return response

            # Check rate limit
            rate_limit_info = await self.rate_limiter.check_rate_limit(
                user_id=user.user_id,
                limit=user.rate_limit_per_minute,
            )

            # Store rate limit info in request state for later use
            request.state.rate_limit_info = rate_limit_info

            # If denied, return 429
            if not rate_limit_info.allowed:
                logger.warning(
                    f"Rate limit exceeded for user {user.user_id} "
                    f"({user.email}): {rate_limit_info.limit} req/{settings.rate_limit_window}s"
                )

                # Return 429 with rate limit headers
                return Response(
                    content='{"error":{"code":"RATE_LIMIT_EXCEEDED","message":"Too many requests. Please try again later.","limit":%d,"retry_after":%d}}' % (
                        rate_limit_info.limit,
                        rate_limit_info.retry_after or 0,
                    ),
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json",
                    headers={
                        "X-RateLimit-Limit": str(rate_limit_info.limit),
                        "X-RateLimit-Remaining": str(rate_limit_info.remaining),
                        "X-RateLimit-Reset": str(rate_limit_info.reset),
                        "Retry-After": str(rate_limit_info.retry_after or 0),
                    },
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(rate_limit_info.limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
            response.headers["X-RateLimit-Reset"] = str(rate_limit_info.reset)

            return response

        except Exception as e:
            # If rate limiting fails, log error and allow request (fail open)
            logger.error(f"Rate limiting error: {e}", exc_info=True)
            response = await call_next(request)
            return response


def add_rate_limit_headers(response: Response, rate_limit_info: RateLimitInfo) -> Response:
    """
    Add rate limit headers to a response.

    Helper function for manual header addition in endpoints.

    Args:
        response: FastAPI response object
        rate_limit_info: Rate limit information

    Returns:
        Response with added headers
    """
    response.headers["X-RateLimit-Limit"] = str(rate_limit_info.limit)
    response.headers["X-RateLimit-Remaining"] = str(rate_limit_info.remaining)
    response.headers["X-RateLimit-Reset"] = str(rate_limit_info.reset)

    if rate_limit_info.retry_after:
        response.headers["Retry-After"] = str(rate_limit_info.retry_after)

    return response
