"""
Redis cache infrastructure

Usage:
    from apps.shared.infrastructure.cache import get_cache, cache_result

    # Get Redis client
    cache = get_cache()
    cache.set("key", "value", ex=60)
    value = cache.get("key")

    # Use decorator for caching expensive operations
    @cache_result(ttl=300)
    async def expensive_function():
        ...
"""

import redis
from redis import ConnectionPool, Redis
from typing import Optional, Any, Callable
from functools import wraps
import json
import structlog

from config import settings

logger = structlog.get_logger(__name__)

# Create connection pool
redis_pool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=settings.REDIS_MAX_CONNECTIONS,
    decode_responses=settings.REDIS_DECODE_RESPONSES,
)

# Create Redis client
redis_client = Redis(connection_pool=redis_pool)


def get_cache() -> Redis:
    """
    Get Redis client instance.

    Usage:
        cache = get_cache()
        cache.set("key", "value", ex=60)
        value = cache.get("key")
    """
    return redis_client


def cache_result(ttl: int = 300, prefix: str = "cache"):
    """
    Decorator to cache function results in Redis.

    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        prefix: Cache key prefix (default: "cache")

    Usage:
        @cache_result(ttl=60)
        async def get_user_stats(user_id: str):
            # Expensive database queries...
            return stats

        # First call: computes and caches
        stats = await get_user_stats("user_123")

        # Second call: returns from cache
        stats = await get_user_stats("user_123")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(prefix, func.__name__, args, kwargs)

            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                logger.debug(
                    "cache_hit",
                    function=func.__name__,
                    key=cache_key
                )
                return json.loads(cached)

            # Cache miss - compute result
            logger.debug(
                "cache_miss",
                function=func.__name__,
                key=cache_key
            )
            result = await func(*args, **kwargs)

            # Store in cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)  # default=str handles UUIDs, dates
            )

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Same logic for sync functions
            cache_key = _generate_cache_key(prefix, func.__name__, args, kwargs)

            cached = redis_client.get(cache_key)
            if cached:
                logger.debug("cache_hit", function=func.__name__, key=cache_key)
                return json.loads(cached)

            logger.debug("cache_miss", function=func.__name__, key=cache_key)
            result = func(*args, **kwargs)

            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, default=str)
            )

            return result

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def invalidate_cache(pattern: str):
    """
    Invalidate cache keys matching a pattern.

    Usage:
        # Invalidate all user-related cache
        invalidate_cache("cache:get_user_stats:*")

        # Invalidate specific user
        invalidate_cache(f"cache:get_user_stats:user_{user_id}:*")
    """
    keys = redis_client.keys(pattern)
    if keys:
        redis_client.delete(*keys)
        logger.info("cache_invalidated", pattern=pattern, count=len(keys))


def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """Generate a cache key from function name and arguments"""
    # Convert args and kwargs to strings
    args_str = ":".join(str(arg) for arg in args)
    kwargs_str = ":".join(f"{k}={v}" for k, v in sorted(kwargs.items()))

    # Combine into cache key
    parts = [prefix, func_name]
    if args_str:
        parts.append(args_str)
    if kwargs_str:
        parts.append(kwargs_str)

    return ":".join(parts)


# Rate limiting using Redis
class RateLimiter:
    """
    Redis-based rate limiter.

    Usage:
        limiter = RateLimiter()

        # Check if allowed
        if limiter.is_allowed("user_123", limit=100, window=3600):
            # Process request
            ...
        else:
            raise HTTPException(429, "Rate limit exceeded")
    """

    def __init__(self, redis_client: Redis = redis_client):
        self.redis = redis_client

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int
    ) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (e.g., user_id, IP address)
            limit: Max requests allowed
            window: Time window in seconds

        Returns:
            True if allowed, False if rate limit exceeded
        """
        cache_key = f"ratelimit:{key}"

        # Get current count
        current = self.redis.get(cache_key)

        if current is None:
            # First request in window
            self.redis.setex(cache_key, window, 1)
            return True

        current = int(current)
        if current < limit:
            # Increment counter
            self.redis.incr(cache_key)
            return True

        # Rate limit exceeded
        logger.warning(
            "rate_limit_exceeded",
            key=key,
            limit=limit,
            current=current
        )
        return False

    def reset(self, key: str):
        """Reset rate limit for a key"""
        cache_key = f"ratelimit:{key}"
        self.redis.delete(cache_key)


def close_cache():
    """
    Close Redis connection pool.

    Usage:
        # Run on app shutdown
        from apps.shared.infrastructure.cache import close_cache
        close_cache()
    """
    logger.info("cache_closing_connections")
    redis_pool.disconnect()
    logger.info("cache_connections_closed")
