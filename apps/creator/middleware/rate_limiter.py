"""
Rate limiting middleware

Prevents API abuse by limiting requests per user/IP.
"""

from typing import Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse

from apps.shared.infrastructure.cache import get_cache
from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


class RateLimiterMiddleware:
    """
    Rate limiting middleware using Redis.

    Implements token bucket algorithm:
    - Each user/IP gets a bucket of tokens
    - Each request consumes 1 token
    - Tokens refill at a fixed rate
    - When bucket is empty, requests are rejected

    Limits:
    - Per minute: Fast refill for burst traffic
    - Per hour: Slower refill for sustained traffic
    """

    def __init__(self, app):
        self.app = app
        self.cache = None  # Will be initialized on first request

    def _get_cache(self):
        """Get cache instance (lazy initialization)."""
        if self.cache is None:
            self.cache = get_cache()
        return self.cache

    def _get_client_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting.

        Priority:
        1. User ID from auth token (if authenticated)
        2. API key (if present)
        3. Client IP address

        Args:
            request: FastAPI request

        Returns:
            Client identifier string
        """
        # Try to get user ID from request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return f"user:{request.state.user_id}"

        # Try to get API key from header
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key[:16]}"

        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"

    def _check_rate_limit(
        self, identifier: str, limit: int, window: int, limit_type: str
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Client identifier
            limit: Max requests allowed
            window: Time window in seconds
            limit_type: Type of limit ("minute" or "hour")

        Returns:
            Tuple of (is_allowed, headers_dict)
        """
        cache = self._get_cache()
        key = f"ratelimit:{limit_type}:{identifier}"

        # Get current count
        current = cache.get(key)

        if current is None:
            # First request in this window
            cache.setex(key, window, 1)
            return True, {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(limit - 1),
                "X-RateLimit-Reset": str(window),
            }

        current = int(current)

        if current < limit:
            # Within limit, increment counter
            cache.incr(key)
            ttl = cache.ttl(key)

            return True, {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(limit - current - 1),
                "X-RateLimit-Reset": str(ttl),
            }

        # Rate limit exceeded
        ttl = cache.ttl(key)

        return False, {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(ttl),
            "Retry-After": str(ttl),
        }

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting if disabled
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/healthz", "/metrics"]:
            return await call_next(request)

        identifier = self._get_client_identifier(request)

        # Check per-minute limit
        allowed_minute, headers_minute = self._check_rate_limit(
            identifier,
            settings.RATE_LIMIT_PER_MINUTE,
            60,  # 1 minute window
            "minute",
        )

        if not allowed_minute:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                path=request.url.path,
                limit_type="per_minute",
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate Limit Exceeded",
                    "detail": f"Too many requests. Limit: {settings.RATE_LIMIT_PER_MINUTE} per minute.",
                    "path": request.url.path,
                },
                headers=headers_minute,
            )

        # Check per-hour limit
        allowed_hour, headers_hour = self._check_rate_limit(
            identifier,
            settings.RATE_LIMIT_PER_HOUR,
            3600,  # 1 hour window
            "hour",
        )

        if not allowed_hour:
            logger.warning(
                "rate_limit_exceeded",
                identifier=identifier,
                path=request.url.path,
                limit_type="per_hour",
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate Limit Exceeded",
                    "detail": f"Too many requests. Limit: {settings.RATE_LIMIT_PER_HOUR} per hour.",
                    "path": request.url.path,
                },
                headers=headers_hour,
            )

        # Request is allowed, proceed
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers_minute.items():
            response.headers[key] = value

        return response


def add_rate_limiter_middleware(app):
    """
    Add rate limiter middleware to FastAPI app.

    Usage:
        from fastapi import FastAPI
        from apps.creator.middleware.rate_limiter import add_rate_limiter_middleware

        app = FastAPI()
        add_rate_limiter_middleware(app)
    """
    app.add_middleware(RateLimiterMiddleware)
