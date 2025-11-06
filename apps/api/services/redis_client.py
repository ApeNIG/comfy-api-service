"""
Redis client for job state management and pub/sub.

Handles job metadata, idempotency tracking, cancellation flags,
and progress updates via Redis pub/sub.
"""

import redis.asyncio as redis
from typing import Optional, Any
import json
from datetime import datetime, timezone
import logging

from ..config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client for job queue operations.

    Provides high-level operations for:
    - Job CRUD (create, read, update, delete)
    - Idempotency checking
    - Cancellation flags
    - Progress pub/sub
    - Metrics tracking
    - Crash recovery (in-progress tracking)
    """

    def __init__(self, url: str, prefix: str = "cui"):
        self.url = url
        self.prefix = prefix
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        """Establish Redis connection."""
        self._client = await redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True
        )
        logger.info(f"Connected to Redis at {self.url}")

    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("Disconnected from Redis")

    def _key(self, pattern: str) -> str:
        """Generate namespaced key."""
        return f"{self.prefix}:{pattern}"

    # -------------------------------------------------------------------------
    # Job Operations
    # -------------------------------------------------------------------------

    async def create_job(self, job_id: str, job_data: dict) -> None:
        """
        Create a new job in Redis.

        Args:
            job_id: Unique job identifier
            job_data: Job metadata (params, owner, etc.)
        """
        key = self._key(f"jobs:{job_id}")

        # Serialize complex fields to JSON
        serialized_data = {
            "job_id": job_id,
            "status": "queued",
            "progress": "0.0",
            "queued_at": datetime.now(timezone.utc).isoformat(),
        }

        for k, v in job_data.items():
            if isinstance(v, (dict, list)):
                serialized_data[f"{k}_json"] = json.dumps(v)
            else:
                serialized_data[k] = str(v)

        await self._client.hset(key, mapping=serialized_data)
        await self._client.expire(key, 86400)  # 24h TTL

        logger.info(f"Created job {job_id}")

    async def get_job(self, job_id: str) -> Optional[dict]:
        """
        Retrieve job data from Redis.

        Args:
            job_id: Job identifier

        Returns:
            Job data dict or None if not found
        """
        key = self._key(f"jobs:{job_id}")
        data = await self._client.hgetall(key)

        if not data:
            return None

        # Parse JSON fields
        for field in ["params", "result", "error"]:
            json_key = f"{field}_json"
            if json_key in data:
                try:
                    data[field] = json.loads(data[json_key])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse {json_key} for job {job_id}")

        return data

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[float] = None,
        **kwargs
    ) -> None:
        """
        Update job status and optional fields.

        Args:
            job_id: Job identifier
            status: New status (queued, running, succeeded, failed, canceled)
            progress: Progress 0.0-1.0 (optional)
            **kwargs: Additional fields to update
        """
        key = self._key(f"jobs:{job_id}")
        updates = {"status": status}

        if progress is not None:
            updates["progress"] = str(progress)

        # Auto-set timestamps based on status
        if status == "running" and "started_at" not in kwargs:
            updates["started_at"] = datetime.now(timezone.utc).isoformat()

        if status in ["succeeded", "failed", "canceled", "expired"]:
            if "finished_at" not in kwargs:
                updates["finished_at"] = datetime.now(timezone.utc).isoformat()

        # Serialize complex fields
        for k, v in kwargs.items():
            if isinstance(v, (dict, list)):
                updates[f"{k}_json"] = json.dumps(v)
            else:
                updates[k] = str(v)

        await self._client.hset(key, mapping=updates)

        logger.debug(f"Updated job {job_id}: status={status}, progress={progress}")

    # -------------------------------------------------------------------------
    # Idempotency
    # -------------------------------------------------------------------------

    async def check_idempotency(
        self,
        token: str,
        idempotency_key: str
    ) -> Optional[str]:
        """
        Check if this request has been submitted before.

        Args:
            token: User/client identifier
            idempotency_key: Unique request key

        Returns:
            Existing job_id if found, None otherwise
        """
        key = self._key(f"idemp:{token}:{idempotency_key}")
        job_id = await self._client.get(key)
        return job_id

    async def set_idempotency(
        self,
        token: str,
        idempotency_key: str,
        job_id: str,
        ttl: int = 86400
    ) -> bool:
        """
        Store idempotency mapping (SET NX - only if not exists).

        Args:
            token: User/client identifier
            idempotency_key: Unique request key
            job_id: Job ID to associate
            ttl: Time-to-live in seconds (default 24h)

        Returns:
            True if stored, False if already exists
        """
        key = self._key(f"idemp:{token}:{idempotency_key}")
        result = await self._client.set(key, job_id, nx=True, ex=ttl)
        return result is not None

    # -------------------------------------------------------------------------
    # Cancellation
    # -------------------------------------------------------------------------

    async def set_cancel_flag(self, job_id: str) -> None:
        """
        Set cancellation flag for a job.

        Workers check this flag periodically and abort if set.

        Args:
            job_id: Job to cancel
        """
        key = self._key(f"jobs:{job_id}:cancel")
        await self._client.set(key, "1", ex=3600)  # 1h TTL
        logger.info(f"Set cancel flag for job {job_id}")

    async def check_cancel_flag(self, job_id: str) -> bool:
        """
        Check if job has been cancelled.

        Args:
            job_id: Job to check

        Returns:
            True if cancel flag is set
        """
        key = self._key(f"jobs:{job_id}:cancel")
        return await self._client.exists(key) > 0

    async def clear_cancel_flag(self, job_id: str) -> None:
        """Clear cancellation flag (after handling)."""
        key = self._key(f"jobs:{job_id}:cancel")
        await self._client.delete(key)

    # -------------------------------------------------------------------------
    # Progress Pub/Sub
    # -------------------------------------------------------------------------

    async def publish_progress(self, job_id: str, data: dict) -> None:
        """
        Publish progress update to job's channel.

        Args:
            job_id: Job identifier
            data: Progress data (type, progress, message, etc.)
        """
        channel = self._key(f"ws:jobs:{job_id}")
        message = json.dumps(data)
        await self._client.publish(channel, message)

        logger.debug(f"Published progress for job {job_id}: {data.get('type')}")

    async def subscribe_progress(self, job_id: str):
        """
        Subscribe to progress updates for a job.

        Args:
            job_id: Job to monitor

        Returns:
            PubSub object for listening
        """
        channel = self._key(f"ws:jobs:{job_id}")
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        logger.debug(f"Subscribed to progress for job {job_id}")
        return pubsub

    # -------------------------------------------------------------------------
    # Metrics
    # -------------------------------------------------------------------------

    async def increment_metric(self, metric: str, labels: Optional[dict] = None) -> None:
        """
        Increment a counter metric.

        Args:
            metric: Metric name (e.g., "jobs_total")
            labels: Optional labels dict (e.g., {"status": "succeeded"})
        """
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in labels.items())
            key = self._key(f"metrics:{metric}{{{label_str}}}")
        else:
            key = self._key(f"metrics:{metric}")

        await self._client.incr(key)

    async def get_metric(self, metric: str, labels: Optional[dict] = None) -> int:
        """Get current value of a counter metric."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in labels.items())
            key = self._key(f"metrics:{metric}{{{label_str}}}")
        else:
            key = self._key(f"metrics:{metric}")

        value = await self._client.get(key)
        return int(value) if value else 0

    # -------------------------------------------------------------------------
    # Crash Recovery (In-Progress Tracking)
    # -------------------------------------------------------------------------

    async def mark_job_in_progress(self, job_id: str) -> None:
        """
        Mark job as actively processing.

        Used for crash recovery - if worker dies, these jobs
        can be detected and requeued.

        Args:
            job_id: Job identifier
        """
        key = self._key("jobs:inprogress")
        await self._client.sadd(key, job_id)

    async def unmark_job_in_progress(self, job_id: str) -> None:
        """Remove job from in-progress set (after completion)."""
        key = self._key("jobs:inprogress")
        await self._client.srem(key, job_id)

    async def get_in_progress_jobs(self) -> list[str]:
        """
        Get all jobs currently marked as in-progress.

        Returns:
            List of job IDs
        """
        key = self._key("jobs:inprogress")
        members = await self._client.smembers(key)
        return list(members)

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check if Redis is responsive."""
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global instance
redis_client = RedisClient(url=settings.redis_url, prefix=settings.redis_prefix)
