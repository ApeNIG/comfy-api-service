"""
A/B Testing API endpoints.

Provides functionality to run A/B tests comparing different generation parameters.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional, Dict
import logging
import asyncio
import time
import secrets
from datetime import datetime

from ..models.requests import ABTestRequest
from ..models.responses import (
    ABTestResponse,
    ABTestVariantResult,
    ErrorResponse,
    JobStatus,
    ImageMetadata
)
from ..services.job_queue import job_queue
from ..services.redis_client import redis_client
from ..config import settings
from ..services.monitoring import cost_tracker

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/abtest",
    tags=["A/B Testing"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


async def check_jobs_enabled():
    """Dependency to check if jobs feature is enabled."""
    if not settings.jobs_enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "FEATURE_DISABLED",
                    "message": "Job queue is required for A/B testing",
                    "details": {"feature": "jobs"}
                }
            }
        )


@router.post(
    "",
    response_model=ABTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run A/B test",
    description="""
    Run an A/B test comparing different generation parameters.

    Submits multiple variants of the same prompt with different parameters,
    waits for all to complete, and returns a comparison with costs and timing.

    **Use Cases:**
    - Compare different step counts (quality vs speed)
    - Test different samplers
    - Compare CFG scale values
    - Test different image sizes

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/abtest \\
      -H "Content-Type: application/json" \\
      -d '{
        "base_prompt": "A mountain landscape",
        "description": "Testing step counts",
        "variants": [
          {
            "name": "fast",
            "request": {"prompt": "A mountain landscape", "steps": 15}
          },
          {
            "name": "quality",
            "request": {"prompt": "A mountain landscape", "steps": 40}
          }
        ]
      }'
    ```
    """,
    responses={
        201: {
            "description": "A/B test completed successfully",
            "model": ABTestResponse
        },
        400: {
            "description": "Invalid request parameters",
            "model": ErrorResponse
        },
        503: {
            "description": "Job queue unavailable"
        }
    }
)
async def run_ab_test(
    request: ABTestRequest,
    _enabled: None = Depends(check_jobs_enabled)
) -> ABTestResponse:
    """
    Run an A/B test with multiple variants.

    Submits all variants as jobs, waits for completion, and returns
    comprehensive comparison data.
    """
    try:
        logger.info(f"Starting A/B test with {len(request.variants)} variants")

        # Generate test ID
        test_id = f"abtest_{secrets.token_hex(8)}"
        start_time = time.time()

        # Submit all variants as jobs
        variant_jobs: Dict[str, tuple[str, float]] = {}  # variant_name -> (job_id, submit_time)

        for variant in request.variants:
            try:
                # Submit job
                job_response = await job_queue.submit_job(variant.request)
                job_id = job_response.job_id
                variant_jobs[variant.name] = (job_id, time.time())
                logger.info(f"Submitted variant '{variant.name}' as job {job_id}")
            except Exception as e:
                logger.error(f"Failed to submit variant '{variant.name}': {e}")
                # Continue with other variants
                variant_jobs[variant.name] = (None, time.time())

        # Wait for all jobs to complete (with timeout)
        max_wait_time = 600  # 10 minutes max
        poll_interval = 2  # Check every 2 seconds
        elapsed = 0

        while elapsed < max_wait_time:
            all_done = True
            for variant_name, (job_id, _) in variant_jobs.items():
                if job_id:
                    job_data = await redis_client.get_job(job_id)
                    if job_data and job_data.get("status") in ["pending", "queued", "processing"]:
                        all_done = False
                        break

            if all_done:
                break

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Collect results
        variant_results = []
        total_cost = 0.0
        total_time = 0.0
        completed_count = 0
        failed_count = 0

        for variant in request.variants:
            variant_name = variant.name
            job_info = variant_jobs.get(variant_name)

            if not job_info or job_info[0] is None:
                # Submission failed
                variant_results.append(ABTestVariantResult(
                    name=variant_name,
                    job_id="",
                    status=JobStatus.FAILED,
                    error="Failed to submit job"
                ))
                failed_count += 1
                continue

            job_id, submit_time = job_info
            job_data = await redis_client.get_job(job_id)

            if not job_data:
                variant_results.append(ABTestVariantResult(
                    name=variant_name,
                    job_id=job_id,
                    status=JobStatus.FAILED,
                    error="Job not found"
                ))
                failed_count += 1
                continue

            # Calculate generation time
            gen_time = None
            if job_data.get("started_at") and job_data.get("finished_at"):
                from datetime import datetime
                started = datetime.fromisoformat(job_data["started_at"].replace('Z', '+00:00'))
                finished = datetime.fromisoformat(job_data["finished_at"].replace('Z', '+00:00'))
                gen_time = (finished - started).total_seconds()
                total_time += gen_time

            # Estimate cost
            estimated_cost = 0.0
            if gen_time:
                cost_data = cost_tracker.estimate_cost(
                    variant.request.width,
                    variant.request.height,
                    variant.request.steps,
                    1
                )
                estimated_cost = cost_data.get("estimated_cost_usd", 0.0)
                total_cost += estimated_cost

            # Get job status and map to JobStatus enum
            raw_status = job_data.get("status", "failed")
            # Map Redis statuses to JobStatus enum values
            status_mapping = {
                "succeeded": "completed",
                "running": "processing",
                "queued": "queued",
                "pending": "pending",
                "failed": "failed",
                "canceled": "cancelled"
            }
            job_status = status_mapping.get(raw_status, "failed")

            # Build metadata
            metadata = None
            if raw_status == "succeeded":
                metadata = ImageMetadata(
                    prompt=variant.request.prompt,
                    negative_prompt=variant.request.negative_prompt,
                    width=variant.request.width,
                    height=variant.request.height,
                    steps=variant.request.steps,
                    cfg_scale=variant.request.cfg_scale,
                    sampler=variant.request.sampler.value,
                    seed=variant.request.seed or -1,
                    model=variant.request.model,
                    generation_time=gen_time
                )
                completed_count += 1
            elif raw_status == "failed":
                failed_count += 1

            # Get image URL
            image_url = None
            result_data = job_data.get("result")
            if result_data and result_data.get("artifacts"):
                image_url = result_data["artifacts"][0]["url"]

            variant_results.append(ABTestVariantResult(
                name=variant_name,
                job_id=job_id,
                status=JobStatus(job_status),
                image_url=image_url,
                error=job_data.get("error", {}).get("message") if job_data.get("error") else None,
                metadata=metadata,
                generation_time=gen_time,
                estimated_cost=estimated_cost
            ))

        # Build response
        response = ABTestResponse(
            test_id=test_id,
            base_prompt=request.base_prompt,
            description=request.description,
            variants=variant_results,
            total_variants=len(request.variants),
            completed_variants=completed_count,
            failed_variants=failed_count,
            total_cost=total_cost,
            total_time=total_time,
            created_at=datetime.utcnow()
        )

        logger.info(
            f"A/B test {test_id} completed: {completed_count}/{len(request.variants)} successful, "
            f"total cost ${total_cost:.6f}, total time {total_time:.1f}s"
        )

        return response

    except Exception as e:
        logger.error(f"Error running A/B test: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "AB_TEST_ERROR",
                    "message": f"Failed to run A/B test: {str(e)}"
                }
            }
        )
