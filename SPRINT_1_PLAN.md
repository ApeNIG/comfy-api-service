# Sprint 1: Job Queue System - Implementation Plan

**Based on expert feedback - Production-grade async job processing**

**Duration:** 1 week
**Goal:** Transform synchronous API into reliable compute service with jobs, progress tracking, and resilience

---

## Overview

Implement a complete job queue system that:
- Accepts work immediately (202 Accepted)
- Processes in background workers
- Provides real-time progress updates
- Handles failures gracefully
- Prevents duplicate work (idempotency)
- Stores artifacts reliably (S3/MinIO)

**Key Principle:** Additive, non-breaking. Keep `/api/v1/generate` for convenience; add `/api/v1/jobs` for production use.

---

## Architecture

```
Client Request
    ↓
POST /api/v1/jobs (with Idempotency-Key)
    ↓
Check Redis idempotency cache
    ↓ (new request)
Store job metadata in Redis
    ↓
Enqueue to ARQ (Redis-backed)
    ↓
Return 202 Accepted + job_id
    ↓
[Worker picks up job]
    ↓
Update status: queued → running
    ↓
Call ComfyUI (with progress callbacks)
    ↓
Publish progress to Redis pub/sub
    ↓
Upload artifacts to MinIO/S3
    ↓
Update status: running → succeeded
    ↓
Client polls GET /jobs/{id} or uses WS /ws/jobs/{id}
```

---

## Components to Build

### 1. Dependencies (pyproject.toml)

```toml
[tool.poetry.dependencies]
# Job Queue
arq = "^0.25.0"              # Async job queue for Python
redis = "^5.0.1"             # Redis client (ARQ dependency + pub/sub)

# Object Storage
minio = "^7.2.0"             # S3-compatible storage (or boto3 for AWS)

# Observability
prometheus-fastapi-instrumentator = "^6.1.0"  # Metrics endpoint
prometheus-client = "^0.19.0"                  # Metrics primitives

# WebSocket (already have FastAPI built-in)
# Already installed: fastapi, uvicorn, httpx, pydantic
```

### 2. Configuration (apps/api/config.py)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_prefix: str = "cui"

    # ARQ
    arq_queue_name: str = "default"
    arq_max_jobs: int = 1000
    arq_worker_concurrency: int = 5

    # Job Settings
    job_timeout: int = 1200  # 20 minutes max
    max_batch_size: int = 10
    max_megapixels: int = 4  # 2048x2048 ~4.2MP

    # Storage
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "comfyui-artifacts"
    minio_secure: bool = False
    artifact_url_ttl: int = 3600  # 1 hour

    # Feature Flags
    jobs_enabled: bool = True
    websocket_enabled: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
```

### 3. Redis Client (apps/api/services/redis_client.py)

```python
import redis.asyncio as redis
from typing import Optional
import json
from datetime import datetime, timezone

class RedisClient:
    def __init__(self, url: str, prefix: str = "cui"):
        self.url = url
        self.prefix = prefix
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        self._client = await redis.from_url(
            self.url,
            encoding="utf-8",
            decode_responses=True
        )

    async def disconnect(self):
        if self._client:
            await self._client.close()

    def _key(self, pattern: str) -> str:
        return f"{self.prefix}:{pattern}"

    # Job operations
    async def create_job(self, job_id: str, job_data: dict) -> None:
        key = self._key(f"jobs:{job_id}")
        await self._client.hset(key, mapping={
            "job_id": job_id,
            "status": "queued",
            "progress": "0.0",
            "queued_at": datetime.now(timezone.utc).isoformat(),
            **{k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
               for k, v in job_data.items()}
        })
        await self._client.expire(key, 86400)  # 24h TTL

    async def get_job(self, job_id: str) -> Optional[dict]:
        key = self._key(f"jobs:{job_id}")
        data = await self._client.hgetall(key)
        if not data:
            return None

        # Parse JSON fields
        for field in ["params", "result", "error"]:
            if f"{field}_json" in data:
                try:
                    data[field] = json.loads(data[f"{field}_json"])
                except json.JSONDecodeError:
                    pass

        return data

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: float = None,
        **kwargs
    ) -> None:
        key = self._key(f"jobs:{job_id}")
        updates = {"status": status}

        if progress is not None:
            updates["progress"] = str(progress)

        if status == "running" and "started_at" not in kwargs:
            updates["started_at"] = datetime.now(timezone.utc).isoformat()

        if status in ["succeeded", "failed", "canceled"]:
            updates["finished_at"] = datetime.now(timezone.utc).isoformat()

        updates.update({
            k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
            for k, v in kwargs.items()
        })

        await self._client.hset(key, mapping=updates)

    # Idempotency
    async def check_idempotency(
        self,
        token: str,
        idempotency_key: str
    ) -> Optional[str]:
        key = self._key(f"idemp:{token}:{idempotency_key}")
        return await self._client.get(key)

    async def set_idempotency(
        self,
        token: str,
        idempotency_key: str,
        job_id: str,
        ttl: int = 86400
    ) -> bool:
        key = self._key(f"idemp:{token}:{idempotency_key}")
        return await self._client.set(key, job_id, nx=True, ex=ttl)

    # Cancellation
    async def set_cancel_flag(self, job_id: str) -> None:
        key = self._key(f"jobs:{job_id}:cancel")
        await self._client.set(key, "1", ex=3600)

    async def check_cancel_flag(self, job_id: str) -> bool:
        key = self._key(f"jobs:{job_id}:cancel")
        return await self._client.exists(key) > 0

    # Progress pub/sub
    async def publish_progress(self, job_id: str, data: dict) -> None:
        channel = self._key(f"ws:jobs:{job_id}")
        await self._client.publish(channel, json.dumps(data))

    async def subscribe_progress(self, job_id: str):
        channel = self._key(f"ws:jobs:{job_id}")
        pubsub = self._client.pubsub()
        await pubsub.subscribe(channel)
        return pubsub

    # Metrics
    async def increment_metric(self, metric: str, labels: dict = None) -> None:
        label_str = ",".join(f"{k}={v}" for k, v in (labels or {}).items())
        key = self._key(f"metrics:{metric}{{{label_str}}}")
        await self._client.incr(key)

    # In-progress tracking (crash recovery)
    async def mark_job_in_progress(self, job_id: str) -> None:
        key = self._key("jobs:inprogress")
        await self._client.sadd(key, job_id)

    async def unmark_job_in_progress(self, job_id: str) -> None:
        key = self._key("jobs:inprogress")
        await self._client.srem(key, job_id)

    async def get_in_progress_jobs(self) -> list[str]:
        key = self._key("jobs:inprogress")
        return list(await self._client.smembers(key))

# Global instance
redis_client = RedisClient(url=settings.redis_url, prefix=settings.redis_prefix)
```

### 4. Storage Client (apps/api/services/storage_client.py)

```python
from minio import Minio
from minio.error import S3Error
import io
from typing import BinaryIO, Optional
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False
    ):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket = bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket: {e}")

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream"
    ) -> str:
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                length,
                content_type=content_type
            )
            return f"s3://{self.bucket}/{object_name}"
        except S3Error as e:
            logger.error(f"Failed to upload {object_name}: {e}")
            raise

    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream"
    ) -> str:
        return self.upload_file(
            object_name,
            io.BytesIO(data),
            len(data),
            content_type
        )

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1)
    ) -> str:
        try:
            return self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=expires
            )
        except S3Error as e:
            logger.error(f"Failed to generate URL for {object_name}: {e}")
            raise

    def delete_object(self, object_name: str) -> None:
        try:
            self.client.remove_object(self.bucket, object_name)
        except S3Error as e:
            logger.error(f"Failed to delete {object_name}: {e}")

# Global instance
storage_client = StorageClient(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    bucket=settings.minio_bucket,
    secure=settings.minio_secure
)
```

### 5. Job Models (apps/api/models/jobs.py)

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    EXPIRED = "expired"

class JobArtifact(BaseModel):
    url: str = Field(..., description="Presigned URL to artifact")
    seed: Optional[int] = Field(None, description="Seed used for generation")
    meta: Optional[dict[str, Any]] = Field(None, description="Additional metadata")

class JobResult(BaseModel):
    artifacts: list[JobArtifact] = Field(default_factory=list)

class JobTimestamps(BaseModel):
    queued_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

class JobResponse(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: float = Field(0.0, ge=0.0, le=1.0, description="Progress 0-1")
    submitted_by: Optional[str] = Field(None, description="Token/user identifier")
    params: Optional[dict[str, Any]] = Field(None, description="Job parameters (if owner)")
    result: Optional[JobResult] = Field(None, description="Job result (if completed)")
    error: Optional[dict[str, Any]] = Field(None, description="Error details (if failed)")
    timestamps: JobTimestamps = Field(..., description="Job lifecycle timestamps")

class JobCreateResponse(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Initial status (queued)")
    queued_at: datetime = Field(..., description="Timestamp when job was queued")
    location: str = Field(..., description="URL to job status endpoint")

class JobListResponse(BaseModel):
    jobs: list[JobResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")
```

### 6. Job Queue Service (apps/api/services/job_queue.py)

```python
import uuid
import hashlib
import json
from typing import Optional
from datetime import datetime, timezone
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis

from ..models.requests import GenerateImageRequest
from ..models.jobs import JobStatus, JobCreateResponse
from .redis_client import redis_client
from ..config import settings

class JobQueueService:
    def __init__(self):
        self._pool: Optional[ArqRedis] = None

    async def connect(self):
        self._pool = await create_pool(
            RedisSettings(
                host=settings.redis_url.split("://")[1].split(":")[0],
                port=int(settings.redis_url.split(":")[-1]) if ":" in settings.redis_url.split("://")[1] else 6379
            )
        )

    async def disconnect(self):
        if self._pool:
            await self._pool.close()

    def _generate_job_id(self) -> str:
        return f"j_{uuid.uuid4().hex[:12]}"

    def _compute_idempotency_key(
        self,
        request: GenerateImageRequest,
        token: str
    ) -> str:
        """Generate stable hash for request deduplication."""
        data = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "steps": request.steps,
            "cfg_scale": request.cfg_scale,
            "sampler": request.sampler,
            "seed": request.seed,
            "model": request.model,
            "batch_size": request.batch_size,
            "token": token,
            "version": "v1"
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def submit_job(
        self,
        request: GenerateImageRequest,
        token: str = "anonymous",
        idempotency_key: Optional[str] = None
    ) -> JobCreateResponse:
        # Check idempotency
        if not idempotency_key:
            idempotency_key = self._compute_idempotency_key(request, token)

        existing_job_id = await redis_client.check_idempotency(token, idempotency_key)
        if existing_job_id:
            # Return existing job
            job_data = await redis_client.get_job(existing_job_id)
            if job_data:
                return JobCreateResponse(
                    job_id=existing_job_id,
                    status=JobStatus(job_data["status"]),
                    queued_at=datetime.fromisoformat(job_data["queued_at"]),
                    location=f"/api/v1/jobs/{existing_job_id}"
                )

        # Create new job
        job_id = self._generate_job_id()

        # Store in Redis
        await redis_client.create_job(job_id, {
            "owner_token": token,
            "idempotency_key": idempotency_key,
            "params_json": request.model_dump(),
        })

        # Set idempotency mapping
        await redis_client.set_idempotency(token, idempotency_key, job_id)

        # Enqueue to ARQ
        await self._pool.enqueue_job(
            "generate_task",
            job_id,
            _queue_name=settings.arq_queue_name
        )

        # Metrics
        await redis_client.increment_metric("jobs_total", {"status": "queued"})

        return JobCreateResponse(
            job_id=job_id,
            status=JobStatus.QUEUED,
            queued_at=datetime.now(timezone.utc),
            location=f"/api/v1/jobs/{job_id}"
        )

    async def cancel_job(self, job_id: str) -> bool:
        job_data = await redis_client.get_job(job_id)
        if not job_data:
            return False

        status = job_data["status"]

        if status == "queued":
            # Remove from queue (best effort)
            await redis_client.update_job_status(job_id, "canceled")
            await redis_client.increment_metric("jobs_total", {"status": "canceled"})
            return True

        elif status == "running":
            # Set cancel flag for worker to check
            await redis_client.set_cancel_flag(job_id)
            await redis_client.update_job_status(job_id, "canceling")
            return True

        return False

# Global instance
job_queue = JobQueueService()
```

### 7. ARQ Worker (apps/worker/main.py)

```python
import asyncio
import json
import logging
from typing import Any
from datetime import datetime, timezone

from arq import cron
from arq.connections import RedisSettings
from arq.worker import Function

from apps.api.services.redis_client import redis_client
from apps.api.services.storage_client import storage_client
from apps.api.services.comfyui_client import ComfyUIClient
from apps.api.models.requests import GenerateImageRequest
from apps.api.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_task(ctx, job_id: str):
    """
    Main worker task: processes a single job.
    """
    logger.info(f"Starting job {job_id}")

    try:
        # Mark as in-progress (for crash recovery)
        await redis_client.mark_job_in_progress(job_id)

        # Update status to running
        await redis_client.update_job_status(job_id, "running")
        await redis_client.publish_progress(job_id, {
            "type": "status",
            "status": "running",
            "progress": 0.0
        })

        # Get job parameters
        job_data = await redis_client.get_job(job_id)
        params_json = job_data.get("params_json") or job_data.get("params")
        if isinstance(params_json, str):
            params_json = json.loads(params_json)

        request = GenerateImageRequest(**params_json)

        # Check for cancellation
        if await redis_client.check_cancel_flag(job_id):
            raise asyncio.CancelledError("Job cancelled by user")

        # Call ComfyUI
        async with ComfyUIClient() as client:
            # Progress callback
            async def on_progress(progress: float, message: str = ""):
                await redis_client.update_job_status(job_id, "running", progress=progress)
                await redis_client.publish_progress(job_id, {
                    "type": "progress",
                    "progress": progress,
                    "message": message
                })
                # Check cancellation between steps
                if await redis_client.check_cancel_flag(job_id):
                    raise asyncio.CancelledError("Job cancelled by user")

            await on_progress(0.1, "Submitting workflow to ComfyUI")

            # Generate image
            result = await client.generate_image(request)

            await on_progress(0.8, "Uploading artifacts")

        # Upload artifacts to storage
        artifacts = []
        for idx, image_data in enumerate(result.images if hasattr(result, 'images') else [result]):
            object_name = f"jobs/{job_id}/image_{idx}.png"

            # Upload image bytes
            storage_client.upload_bytes(
                object_name,
                image_data,  # Assume bytes from ComfyUI
                content_type="image/png"
            )

            # Generate signed URL
            url = storage_client.get_presigned_url(object_name)

            artifacts.append({
                "url": url,
                "seed": result.seed if hasattr(result, 'seed') else None,
                "meta": {}
            })

        # Store result
        result_data = {"artifacts": artifacts}
        await redis_client.update_job_status(
            job_id,
            "succeeded",
            progress=1.0,
            result_json=result_data
        )

        # Publish completion
        await redis_client.publish_progress(job_id, {
            "type": "done",
            "status": "succeeded",
            "result": result_data
        })

        # Metrics
        await redis_client.increment_metric("jobs_total", {"status": "succeeded"})

        logger.info(f"Job {job_id} completed successfully")

    except asyncio.CancelledError:
        await redis_client.update_job_status(
            job_id,
            "canceled",
            error_json={"message": "Job was cancelled"}
        )
        await redis_client.publish_progress(job_id, {
            "type": "done",
            "status": "canceled"
        })
        await redis_client.increment_metric("jobs_total", {"status": "canceled"})
        logger.info(f"Job {job_id} was cancelled")

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")

        # Store error
        await redis_client.update_job_status(
            job_id,
            "failed",
            error_json={
                "message": str(e),
                "type": type(e).__name__
            }
        )

        # Publish failure
        await redis_client.publish_progress(job_id, {
            "type": "done",
            "status": "failed",
            "error": {"message": str(e)}
        })

        # Metrics
        await redis_client.increment_metric("jobs_total", {"status": "failed"})

    finally:
        # Unmark from in-progress
        await redis_client.unmark_job_in_progress(job_id)

async def startup(ctx):
    """Worker startup: connect to Redis."""
    await redis_client.connect()
    logger.info("Worker started, connected to Redis")

async def shutdown(ctx):
    """Worker shutdown: disconnect from Redis."""
    await redis_client.disconnect()
    logger.info("Worker shutting down")

class WorkerSettings:
    """ARQ worker configuration."""
    functions = [Function(generate_task, name="generate_task")]

    redis_settings = RedisSettings(
        host=settings.redis_url.split("://")[1].split(":")[0],
        port=int(settings.redis_url.split(":")[-1]) if ":" in settings.redis_url.split("://")[1] else 6379
    )

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = settings.arq_worker_concurrency
    job_timeout = settings.job_timeout

    # Health check interval
    health_check_interval = 60
```

### 8. Job Router (apps/api/routers/jobs.py)

```python
from fastapi import APIRouter, HTTPException, status, Header, Depends
from typing import Optional

from ..models.requests import GenerateImageRequest
from ..models.jobs import JobCreateResponse, JobResponse, JobStatus
from ..services.job_queue import job_queue
from ..services.redis_client import redis_client
from ..config import settings

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["jobs"],
    responses={
        503: {"description": "Job queue disabled or unavailable"}
    }
)

async def check_jobs_enabled():
    if not settings.jobs_enabled:
        raise HTTPException(
            status_code=503,
            detail="Job queue is currently disabled"
        )

@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit image generation job",
    responses={
        202: {"description": "Job accepted and queued"},
        413: {"description": "Request too large"},
        429: {"description": "Rate limit exceeded"},
    }
)
async def create_job(
    request: GenerateImageRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    _enabled: None = Depends(check_jobs_enabled)
) -> JobCreateResponse:
    """
    Submit an image generation job for async processing.

    Returns immediately with a job_id. Use GET /jobs/{job_id} to check status.

    **Idempotency:** Include `Idempotency-Key` header to prevent duplicate submissions.
    If the same key is used within 24 hours, the original job_id is returned.
    """
    # TODO: Extract token from auth header (for now use request_id as token)
    token = x_request_id or "anonymous"

    result = await job_queue.submit_job(
        request=request,
        token=token,
        idempotency_key=idempotency_key
    )

    return result

@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    responses={
        404: {"description": "Job not found"}
    }
)
async def get_job(
    job_id: str,
    _enabled: None = Depends(check_jobs_enabled)
) -> JobResponse:
    """
    Get the current status and result of a job.

    **Status values:**
    - `queued`: Waiting to be processed
    - `running`: Currently processing
    - `succeeded`: Completed successfully (result available)
    - `failed`: Failed with error
    - `canceled`: Cancelled by user
    - `expired`: Expired before completion
    """
    job_data = await redis_client.get_job(job_id)

    if not job_data:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found"
        )

    return JobResponse(
        job_id=job_data["job_id"],
        status=JobStatus(job_data["status"]),
        progress=float(job_data.get("progress", 0.0)),
        submitted_by=job_data.get("owner_token"),
        params=job_data.get("params"),
        result=job_data.get("result"),
        error=job_data.get("error"),
        timestamps={
            "queued_at": job_data["queued_at"],
            "started_at": job_data.get("started_at"),
            "finished_at": job_data.get("finished_at")
        }
    )

@router.delete(
    "/{job_id}",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cancel job",
    responses={
        202: {"description": "Cancellation requested"},
        404: {"description": "Job not found"}
    }
)
async def cancel_job(
    job_id: str,
    _enabled: None = Depends(check_jobs_enabled)
) -> dict:
    """
    Cancel a running or queued job.

    - If `queued`: removed immediately
    - If `running`: best-effort cancellation (may take a few seconds)
    - If already finished: no effect

    Returns 202 to indicate cancellation was requested (not guaranteed immediate).
    """
    success = await job_queue.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Job {job_id} not found or cannot be cancelled"
        )

    return {
        "job_id": job_id,
        "message": "Cancellation requested"
    }

@router.get(
    "",
    response_model=dict,
    summary="List jobs",
    responses={
        200: {"description": "List of jobs"}
    }
)
async def list_jobs(
    limit: int = 20,
    offset: int = 0,
    _enabled: None = Depends(check_jobs_enabled)
) -> dict:
    """
    List recent jobs (TODO: implement with auth filtering).

    For now, returns placeholder. In production, filter by authenticated user.
    """
    # TODO: Implement job listing with Redis SCAN
    return {
        "jobs": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "message": "Job listing not yet implemented"
    }
```

### 9. WebSocket Router (apps/api/routers/websocket.py)

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
import json
import logging

from ..services.redis_client import redis_client
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

async def check_websocket_enabled():
    if not settings.websocket_enabled:
        raise HTTPException(
            status_code=503,
            detail="WebSocket support is currently disabled"
        )

@router.websocket("/ws/jobs/{job_id}")
async def job_progress_websocket(
    websocket: WebSocket,
    job_id: str
):
    """
    WebSocket endpoint for real-time job progress updates.

    Sends JSON messages:
    - `{"type": "status", "status": "running", "progress": 0.42}`
    - `{"type": "progress", "progress": 0.5, "message": "step 15/30"}`
    - `{"type": "artifact", "url": "https://..."}`
    - `{"type": "done", "status": "succeeded|failed|canceled"}`
    """
    if not settings.websocket_enabled:
        await websocket.close(code=1008, reason="WebSocket disabled")
        return

    # Check job exists
    job_data = await redis_client.get_job(job_id)
    if not job_data:
        await websocket.close(code=1008, reason=f"Job {job_id} not found")
        return

    await websocket.accept()

    # Send current status immediately
    await websocket.send_json({
        "type": "status",
        "status": job_data["status"],
        "progress": float(job_data.get("progress", 0.0))
    })

    # Subscribe to progress updates
    pubsub = await redis_client.subscribe_progress(job_id)

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)

                # Close after done event
                if data.get("type") == "done":
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")

    except Exception as e:
        logger.exception(f"WebSocket error for job {job_id}: {e}")

    finally:
        await pubsub.unsubscribe()
        await pubsub.close()
        await websocket.close()
```

### 10. Prometheus Metrics (apps/api/routers/metrics.py)

```python
from fastapi import APIRouter
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

router = APIRouter(tags=["observability"])

# Define metrics
jobs_total = Counter(
    "comfyui_jobs_total",
    "Total number of jobs by status",
    ["status"]
)

job_duration = Histogram(
    "comfyui_job_duration_seconds",
    "Job processing duration",
    buckets=[10, 30, 60, 120, 300, 600, 1200]
)

queue_depth = Gauge(
    "comfyui_queue_depth",
    "Number of jobs in queue"
)

active_workers = Gauge(
    "comfyui_active_workers",
    "Number of active worker processes"
)

@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

---

## Implementation Steps

### Day 1: Foundation
1. ✅ Create Sprint 1 plan
2. ⏳ Install dependencies (Poetry)
3. ⏳ Create config.py with settings
4. ⏳ Set up Redis client
5. ⏳ Set up MinIO/storage client
6. ⏳ Create job models

### Day 2: Queue System
7. ⏳ Implement idempotency service
8. ⏳ Implement job queue service
9. ⏳ Create job router endpoints

### Day 3: Workers
10. ⏳ Create ARQ worker
11. ⏳ Integrate ComfyUI client with progress callbacks
12. ⏳ Test worker job processing

### Day 4: Real-time & Observability
13. ⏳ Implement WebSocket progress updates
14. ⏳ Add Prometheus metrics
15. ⏳ Implement crash recovery

### Day 5: Integration & Testing
16. ⏳ Write integration tests
17. ⏳ Test idempotency
18. ⏳ Test cancellation
19. ⏳ Load testing with k6

### Day 6-7: Polish & Deploy
20. ⏳ Update documentation
21. ⏳ Feature flag testing
22. ⏳ Commit Sprint 1
23. ⏳ Celebrate! 🎉

---

## Testing Strategy

### Unit Tests
- Redis operations (job CRUD, idempotency)
- Storage client (upload, presigned URLs)
- Idempotency key generation

### Integration Tests
- Full job lifecycle (submit → process → retrieve)
- Idempotency (duplicate submissions)
- Cancellation (queued vs running)
- WebSocket progress streaming

### Load Tests (k6)
```javascript
import http from 'k6/http';
import { check } from 'k6';

export let options = {
  vus: 10,
  duration: '30s',
};

export default function() {
  const payload = JSON.stringify({
    prompt: 'Test prompt',
    width: 512,
    height: 512,
    steps: 20
  });

  const res = http.post('http://localhost:8000/api/v1/jobs', payload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(res, {
    'status is 202': (r) => r.status === 202,
    'has job_id': (r) => r.json('job_id') !== undefined,
  });
}
```

### Chaos Tests
- Kill worker during job → verify job marked failed or requeued
- Redis disconnect → verify graceful degradation
- MinIO unavailable → verify error handling

---

## Success Criteria

- [ ] Jobs can be submitted and return 202 + job_id
- [ ] Idempotency prevents duplicate GPU work
- [ ] Workers process jobs and update status
- [ ] Progress updates via WebSocket
- [ ] Artifacts stored in MinIO with signed URLs
- [ ] Cancellation works for queued and running jobs
- [ ] Crash recovery requeues stuck jobs
- [ ] Prometheus metrics exposed at /metrics
- [ ] All integration tests pass
- [ ] Load test shows <5s P99 for job submission
- [ ] Documentation updated

---

**Status:** Ready to implement
**Next:** Install dependencies and begin Day 1 tasks
