"""
Job queue service for async image generation.

Handles job submission, idempotency, and queueing to ARQ workers.
"""

import uuid
import hashlib
import json
from typing import Optional
from datetime import datetime, timezone
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
import logging

from ..models.requests import GenerateImageRequest
from ..models.jobs import JobStatus, JobCreateResponse
from .redis_client import redis_client
from ..config import settings

logger = logging.getLogger(__name__)


class JobQueueService:
    """
    Service for managing job queue operations.

    Responsibilities:
    - Job submission with idempotency
    - ARQ queue integration
    - Job cancellation
    - Queue health monitoring
    """

    def __init__(self):
        self._pool: Optional[ArqRedis] = None

    async def connect(self):
        """
        Connect to ARQ (Redis-backed job queue).

        Call this during application startup.
        """
        # Parse Redis URL to extract host and port
        redis_url = settings.redis_url
        if "://" in redis_url:
            redis_url = redis_url.split("://")[1]

        if ":" in redis_url:
            host, port_str = redis_url.split(":")
            port = int(port_str.split("/")[0])  # Handle /db suffix
        else:
            host = redis_url
            port = 6379

        self._pool = await create_pool(
            RedisSettings(
                host=host,
                port=port
            )
        )
        logger.info(f"Connected to ARQ queue at {host}:{port}")

    async def disconnect(self):
        """Disconnect from ARQ pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Disconnected from ARQ queue")

    def _generate_job_id(self) -> str:
        """Generate unique job ID."""
        return f"j_{uuid.uuid4().hex[:12]}"

    def _compute_idempotency_key(
        self,
        request: GenerateImageRequest,
        token: str
    ) -> str:
        """
        Compute stable idempotency key from request.

        This creates a hash of the request parameters so identical
        requests can be deduplicated even without explicit Idempotency-Key header.

        Args:
            request: Generation request
            token: User/client token

        Returns:
            16-character hex string
        """
        # Normalize request to dict (deterministic order)
        data = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "cfg_scale": request.cfg_scale,
            "sampler": request.sampler.value if hasattr(request.sampler, 'value') else request.sampler,
            "seed": request.seed,
            "model": request.model,
            "batch_size": request.batch_size,
            "token": token,
            "version": "v1"
        }

        # Serialize and hash
        content = json.dumps(data, sort_keys=True)
        hash_digest = hashlib.sha256(content.encode()).hexdigest()

        # Return first 16 chars for brevity
        return hash_digest[:16]

    async def submit_job(
        self,
        request: GenerateImageRequest,
        token: str = "anonymous",
        idempotency_key: Optional[str] = None
    ) -> JobCreateResponse:
        """
        Submit a new job to the queue.

        Implements idempotency: if a job with the same idempotency key
        was submitted recently (24h window), returns the existing job ID.

        Args:
            request: Image generation parameters
            token: User/client identifier (for rate limiting and auth)
            idempotency_key: Optional explicit idempotency key

        Returns:
            Job creation response with job_id and status

        Raises:
            RuntimeError: If ARQ pool not connected
        """
        if not self._pool:
            raise RuntimeError("Job queue not connected. Call connect() first.")

        # Generate or use provided idempotency key
        if not idempotency_key:
            idempotency_key = self._compute_idempotency_key(request, token)

        logger.debug(f"Submitting job with idempotency_key={idempotency_key}")

        # Check for existing job (idempotency)
        existing_job_id = await redis_client.check_idempotency(token, idempotency_key)
        if existing_job_id:
            logger.info(f"Idempotency hit: returning existing job {existing_job_id}")

            # Get existing job data
            job_data = await redis_client.get_job(existing_job_id)
            if job_data:
                return JobCreateResponse(
                    job_id=existing_job_id,
                    status=JobStatus(job_data["status"]),
                    queued_at=datetime.fromisoformat(job_data["queued_at"]),
                    location=f"/api/v1/jobs/{existing_job_id}"
                )
            else:
                # Job data missing but idempotency key exists
                # This shouldn't happen, but handle gracefully
                logger.warning(f"Idempotency key exists but job data missing: {existing_job_id}")

        # Create new job
        job_id = self._generate_job_id()

        logger.info(f"Creating new job {job_id}")

        # Store job metadata in Redis
        await redis_client.create_job(job_id, {
            "owner_token": token,
            "idempotency_key": idempotency_key,
            "params": request.model_dump(),
        })

        # Set idempotency mapping (24h TTL)
        await redis_client.set_idempotency(token, idempotency_key, job_id, ttl=86400)

        # Enqueue to ARQ for processing
        try:
            job = await self._pool.enqueue_job(
                "generate_task",  # Function name in worker
                job_id,  # First argument to function
                _queue_name=settings.arq_queue_name
            )
            logger.info(f"Enqueued job {job_id} to ARQ (arq_job_id={job.job_id if job else 'N/A'})")
        except Exception as e:
            # If enqueue fails, mark job as failed
            logger.error(f"Failed to enqueue job {job_id}: {e}")
            await redis_client.update_job_status(
                job_id,
                "failed",
                error={"message": f"Failed to enqueue job: {str(e)}"}
            )
            raise

        # Increment metrics
        await redis_client.increment_metric("jobs_total", {"status": "queued"})

        return JobCreateResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            queued_at=datetime.now(timezone.utc),
            location=f"/api/v1/jobs/{job_id}"
        )

    async def cancel_job(self, job_id: str) -> tuple[bool, JobStatus]:
        """
        Cancel a job.

        If queued: removes from queue immediately
        If running: sets cancel flag for worker to check

        Args:
            job_id: Job to cancel

        Returns:
            Tuple of (success, new_status)
        """
        job_data = await redis_client.get_job(job_id)
        if not job_data:
            logger.warning(f"Attempted to cancel non-existent job {job_id}")
            return False, None

        status = job_data["status"]
        logger.info(f"Cancelling job {job_id} (current status: {status})")

        if status == "queued":
            # Job hasn't started yet - mark as canceled immediately
            await redis_client.update_job_status(job_id, "canceled")
            await redis_client.increment_metric("jobs_total", {"status": "canceled"})
            logger.info(f"Job {job_id} cancelled (was queued)")
            return True, JobStatus.CANCELED

        elif status == "running":
            # Job is processing - set cancel flag for worker
            await redis_client.set_cancel_flag(job_id)
            await redis_client.update_job_status(job_id, "canceling")
            logger.info(f"Job {job_id} cancellation requested (is running)")
            return True, JobStatus.CANCELED  # Return "canceled" even though it's "canceling"

        elif status in ["succeeded", "failed", "canceled", "expired"]:
            # Job already finished
            logger.info(f"Job {job_id} already finished with status {status}")
            return False, JobStatus(status)

        return False, JobStatus(status)

    async def get_job_status(self, job_id: str) -> Optional[dict]:
        """
        Get job status from Redis.

        Args:
            job_id: Job identifier

        Returns:
            Job data dict or None if not found
        """
        return await redis_client.get_job(job_id)

    async def health_check(self) -> dict:
        """
        Check health of job queue system.

        Returns:
            Dict with health status of components
        """
        health = {
            "arq_connected": self._pool is not None,
            "redis_connected": False,
            "queue_depth": 0,
            "in_progress_jobs": 0
        }

        # Check Redis
        try:
            health["redis_connected"] = await redis_client.health_check()
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")

        # Get queue metrics
        try:
            health["in_progress_jobs"] = len(await redis_client.get_in_progress_jobs())
        except Exception as e:
            logger.error(f"Failed to get in-progress jobs: {e}")

        return health


# Global instance
job_queue = JobQueueService()
