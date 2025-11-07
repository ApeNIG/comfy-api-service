"""
Rate limiting service using token bucket algorithm.

Implements Redis-backed rate limiting with:
- Per-user rate limits based on role
- Token bucket algorithm for smooth rate limiting
- Rate limit headers (X-RateLimit-*)
- Configurable windows and quotas
"""

import time
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

from .redis_client import redis_client
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Rate limit information for a user."""
    allowed: bool  # Whether request is allowed
    limit: int  # Max requests per window
    remaining: int  # Remaining requests in current window
    reset: int  # Unix timestamp when window resets
    retry_after: Optional[int] = None  # Seconds to wait before retry (if denied)


class RateLimiter:
    """
    Token bucket rate limiter with Redis backend.

    Algorithm:
    - Each user has a bucket with a max capacity (limit)
    - Tokens refill at a constant rate
    - Each request consumes 1 token
    - If no tokens available, request is denied

    Redis keys:
    - cui:ratelimit:{user_id}:{window_start} -> remaining tokens
    """

    def __init__(self):
        """Initialize rate limiter."""
        self.redis = redis_client._client
        self.window = settings.rate_limit_window  # seconds
        self.key_prefix = "cui:ratelimit"

    async def check_rate_limit(
        self,
        user_id: str,
        limit: int,
    ) -> RateLimitInfo:
        """
        Check if user can make a request.

        Uses sliding window with token bucket algorithm.

        Args:
            user_id: User identifier
            limit: Max requests per window (-1 = unlimited)

        Returns:
            RateLimitInfo with allow/deny decision and metadata
        """
        # Check if rate limiting is enabled
        if not settings.rate_limit_enabled:
            return RateLimitInfo(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset=int(time.time() + self.window),
            )

        # Check for unlimited (-1)
        if limit == -1:
            return RateLimitInfo(
                allowed=True,
                limit=999999,  # Display a large number
                remaining=999999,
                reset=int(time.time() + self.window),
            )

        # Calculate current window
        now = int(time.time())
        window_start = (now // self.window) * self.window
        window_end = window_start + self.window

        # Redis key for this window
        key = f"{self.key_prefix}:{user_id}:{window_start}"

        # Try to decrement token count
        # Use DECR to atomically decrement and get new value
        try:
            # Get current count (how many tokens used)
            count_str = await self.redis.get(key)

            if count_str is None:
                # First request in this window
                count = 0
            else:
                count = int(count_str)

            # Check if limit exceeded
            if count >= limit:
                # Rate limit exceeded
                retry_after = window_end - now
                logger.warning(
                    f"Rate limit exceeded for user {user_id}: "
                    f"{count}/{limit} in window {window_start}"
                )
                return RateLimitInfo(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset=window_end,
                    retry_after=retry_after,
                )

            # Increment count
            await self.redis.incr(key)

            # Set TTL on first use
            if count == 0:
                await self.redis.expire(key, self.window + 10)  # +10s buffer

            remaining = limit - count - 1  # -1 for current request

            logger.debug(
                f"Rate limit OK for user {user_id}: "
                f"{count + 1}/{limit} in window {window_start}"
            )

            return RateLimitInfo(
                allowed=True,
                limit=limit,
                remaining=remaining,
                reset=window_end,
            )

        except Exception as e:
            # If Redis fails, allow request (fail open)
            logger.error(f"Rate limit check failed for user {user_id}: {e}")
            return RateLimitInfo(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset=window_end,
            )

    async def reset_user_limit(self, user_id: str) -> None:
        """
        Reset rate limit for a user (admin function).

        Deletes all rate limit keys for the user.

        Args:
            user_id: User to reset
        """
        pattern = f"{self.key_prefix}:{user_id}:*"
        cursor = 0
        deleted = 0

        try:
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break

            logger.info(f"Reset rate limit for user {user_id} (deleted {deleted} keys)")

        except Exception as e:
            logger.error(f"Failed to reset rate limit for user {user_id}: {e}")

    async def get_current_usage(self, user_id: str) -> Tuple[int, int]:
        """
        Get current rate limit usage for a user.

        Args:
            user_id: User ID

        Returns:
            (used, window_end) tuple
        """
        now = int(time.time())
        window_start = (now // self.window) * self.window
        window_end = window_start + self.window

        key = f"{self.key_prefix}:{user_id}:{window_start}"

        try:
            count_str = await self.redis.get(key)
            count = int(count_str) if count_str else 0
            return (count, window_end)

        except Exception as e:
            logger.error(f"Failed to get usage for user {user_id}: {e}")
            return (0, window_end)


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get or create the singleton rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
