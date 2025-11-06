"""
ARQ worker for processing image generation jobs.

Run with: arq apps.worker.main.WorkerSettings
"""

import asyncio
import json
import logging
import time
from typing import Any
from datetime import datetime, timezone, timedelta
from functools import partial

from arq import cron
from arq.connections import RedisSettings
from arq.worker import Function

from apps.api.services.redis_client import redis_client
from apps.api.services.storage_client import storage_client
from apps.api.services.comfyui_client import ComfyUIClient
from apps.api.models.requests import GenerateImageRequest
from apps.api.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def generate_task(ctx, job_id: str):
    """
    Main worker task: process a single image generation job.

    Args:
        ctx: ARQ context (contains redis connection, etc.)
        job_id: Job identifier to process

    Flow:
        1. Mark job as in-progress (crash recovery)
        2. Update status to "running"
        3. Parse job parameters
        4. Check for cancellation
        5. Call ComfyUI with progress callbacks
        6. Upload artifacts to storage
        7. Update job with results
        8. Publish completion event
    """
    logger.info(f"[{job_id}] Starting job processing")
    start_time = time.time()

    try:
        # Mark as in-progress for crash recovery
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
        if not job_data:
            raise ValueError(f"Job {job_id} not found in Redis")

        # Parse params (may be stored as "params" or "params_json")
        params_data = job_data.get("params") or job_data.get("params_json")
        if isinstance(params_data, str):
            params_data = json.loads(params_data)

        logger.info(f"[{job_id}] Parsed parameters: prompt='{params_data.get('prompt', '')[:50]}...'")

        request = GenerateImageRequest(**params_data)

        # Check for early cancellation
        if await redis_client.check_cancel_flag(job_id):
            raise asyncio.CancelledError("Job cancelled before processing started")

        # Define progress callback
        async def on_progress(progress: float, message: str = ""):
            """
            Called during image generation to report progress.

            Args:
                progress: 0.0 to 1.0
                message: Optional status message
            """
            # Check cancellation between progress updates
            if await redis_client.check_cancel_flag(job_id):
                logger.info(f"[{job_id}] Cancellation detected during progress update")
                raise asyncio.CancelledError("Job cancelled by user")

            # Update Redis
            await redis_client.update_job_status(job_id, "running", progress=progress)

            # Publish to WebSocket subscribers
            await redis_client.publish_progress(job_id, {
                "type": "progress",
                "progress": progress,
                "message": message
            })

            logger.debug(f"[{job_id}] Progress: {progress:.1%} - {message}")

        # Initialize ComfyUI client
        await on_progress(0.05, "Connecting to ComfyUI")

        async with ComfyUIClient(
            base_url=settings.comfyui_url,
            timeout=settings.comfyui_timeout
        ) as client:
            # Check ComfyUI health
            if not await client.health_check():
                raise RuntimeError("ComfyUI is not available")

            await on_progress(0.1, "Submitting workflow to ComfyUI")

            # Generate image(s)
            logger.info(f"[{job_id}] Calling ComfyUI for image generation")
            result = await client.generate_image(request)

            await on_progress(0.85, "Image generation complete, uploading artifacts")

        # Upload artifacts to storage
        logger.info(f"[{job_id}] Uploading artifacts to storage")

        artifacts = []

        # Handle single or multiple images
        images_data = result.images if hasattr(result, 'images') else [result]

        for idx, image_data in enumerate(images_data):
            object_name = f"jobs/{job_id}/image_{idx}.png"

            # Upload image bytes to MinIO/S3
            try:
                # Assuming image_data is bytes from ComfyUI
                storage_client.upload_bytes(
                    object_name,
                    image_data if isinstance(image_data, bytes) else b"",  # TODO: Handle actual image bytes
                    content_type="image/png"
                )

                # Generate presigned URL (1 hour TTL from settings)
                url = storage_client.get_presigned_url(
                    object_name,
                    expires=timedelta(seconds=settings.artifact_url_ttl)
                )

                artifacts.append({
                    "url": url,
                    "seed": result.seed if hasattr(result, 'seed') else request.seed,
                    "width": request.width,
                    "height": request.height,
                    "meta": {}
                })

                # Publish artifact event
                await redis_client.publish_progress(job_id, {
                    "type": "artifact",
                    "url": url
                })

                logger.info(f"[{job_id}] Uploaded artifact {idx}: {object_name}")

            except Exception as e:
                logger.error(f"[{job_id}] Failed to upload artifact {idx}: {e}")
                # Continue with other artifacts even if one fails

        if not artifacts:
            raise RuntimeError("No artifacts were successfully uploaded")

        # Store metadata alongside artifacts
        metadata_object = f"jobs/{job_id}/metadata.json"
        storage_client.upload_json(metadata_object, {
            "job_id": job_id,
            "params": params_data,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": artifacts
        })

        # Calculate generation time
        generation_time = time.time() - start_time

        # Store result in Redis
        result_data = {
            "artifacts": artifacts,
            "generation_time": generation_time
        }

        await redis_client.update_job_status(
            job_id,
            "succeeded",
            progress=1.0,
            result=result_data
        )

        # Publish completion event
        await redis_client.publish_progress(job_id, {
            "type": "done",
            "status": "succeeded",
            "result": result_data
        })

        # Increment success metric
        await redis_client.increment_metric("jobs_total", {"status": "succeeded"})

        logger.info(f"[{job_id}] Job completed successfully in {generation_time:.1f}s")

    except asyncio.CancelledError:
        # Job was cancelled
        logger.info(f"[{job_id}] Job was cancelled")

        await redis_client.update_job_status(
            job_id,
            "canceled",
            error={"message": "Job was cancelled by user"}
        )

        await redis_client.publish_progress(job_id, {
            "type": "done",
            "status": "canceled"
        })

        await redis_client.increment_metric("jobs_total", {"status": "canceled"})

        # Clear cancel flag
        await redis_client.clear_cancel_flag(job_id)

    except Exception as e:
        # Job failed
        logger.exception(f"[{job_id}] Job failed with error: {e}")

        error_data = {
            "message": str(e),
            "type": type(e).__name__
        }

        await redis_client.update_job_status(
            job_id,
            "failed",
            error=error_data
        )

        await redis_client.publish_progress(job_id, {
            "type": "done",
            "status": "failed",
            "error": error_data
        })

        await redis_client.increment_metric("jobs_total", {"status": "failed"})

    finally:
        # Always unmark from in-progress (for crash recovery)
        await redis_client.unmark_job_in_progress(job_id)

        elapsed = time.time() - start_time
        logger.info(f"[{job_id}] Worker task finished in {elapsed:.1f}s")


async def startup(ctx):
    """
    Worker startup hook.

    Connects to Redis and performs any initialization.
    """
    await redis_client.connect()
    logger.info("Worker started and connected to Redis")

    # TODO: Implement crash recovery
    # Check for jobs left in "inprogress" state and requeue them


async def shutdown(ctx):
    """
    Worker shutdown hook.

    Disconnects from Redis gracefully.
    """
    await redis_client.disconnect()
    logger.info("Worker shutting down")


class WorkerSettings:
    """
    ARQ worker configuration.

    This class is used by ARQ to configure the worker process.

    Usage:
        arq apps.worker.main.WorkerSettings
    """

    # Functions to register
    functions = [
        Function(generate_task, name="generate_task")
    ]

    # Redis connection
    redis_settings = None  # Will be set dynamically below

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Worker configuration
    max_jobs = settings.arq_worker_concurrency  # Max concurrent jobs
    job_timeout = settings.job_timeout  # Max time per job (seconds)

    # Health check interval
    health_check_interval = 60  # seconds

    # Queue name
    queue_name = settings.arq_queue_name


# Parse Redis URL for ARQ
redis_url = settings.redis_url
if "://" in redis_url:
    redis_url = redis_url.split("://")[1]

if ":" in redis_url:
    redis_host, port_str = redis_url.split(":")
    redis_port = int(port_str.split("/")[0])
else:
    redis_host = redis_url
    redis_port = 6379

WorkerSettings.redis_settings = RedisSettings(
    host=redis_host,
    port=redis_port
)

logger.info(f"Worker configured: Redis={redis_host}:{redis_port}, concurrency={settings.arq_worker_concurrency}")
