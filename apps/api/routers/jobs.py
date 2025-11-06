"""
Job management API endpoints.

Provides async job submission, status checking, and cancellation.
"""

from fastapi import APIRouter, HTTPException, status, Header, Depends
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from ..models.requests import GenerateImageRequest
from ..models.jobs import (
    JobCreateResponse,
    JobResponse,
    JobStatus,
    JobCancelResponse,
    JobListResponse,
    JobTimestamps,
    JobResult,
    JobError
)
from ..services.job_queue import job_queue
from ..services.redis_client import redis_client
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["jobs"],
    responses={
        503: {"description": "Job queue disabled or unavailable"}
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
                    "message": "Job queue is currently disabled",
                    "details": {"feature": "jobs"}
                }
            }
        )


@router.post(
    "",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit image generation job",
    description="""
    Submit an image generation job for asynchronous processing.

    Returns immediately with a `job_id`. Use `GET /api/v1/jobs/{job_id}`
    to check status or `WS /ws/jobs/{job_id}` for real-time updates.

    **Idempotency:** Include `Idempotency-Key` header to prevent duplicate
    submissions. If the same key is used within 24 hours, the original
    job_id will be returned.

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/jobs \\
      -H "Content-Type: application/json" \\
      -H "Idempotency-Key: my-unique-key-123" \\
      -d '{"prompt": "A sunset", "width": 1024, "height": 1024}'
    ```
    """,
    responses={
        202: {
            "description": "Job accepted and queued for processing",
            "headers": {
                "Location": {
                    "description": "URL to check job status",
                    "schema": {"type": "string"}
                },
                "X-Request-ID": {
                    "description": "Request tracking ID",
                    "schema": {"type": "string"}
                }
            }
        },
        413: {"description": "Request body too large"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Job queue unavailable"}
    }
)
async def create_job(
    request: GenerateImageRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    _enabled: None = Depends(check_jobs_enabled)
) -> JSONResponse:
    """
    Submit a new image generation job.

    The job will be processed asynchronously by background workers.
    """
    # Extract token from auth header (for now, use request_id as token)
    # TODO: Implement proper authentication and extract real token
    token = x_request_id or "anonymous"

    logger.info(
        f"Job submission request",
        extra={
            "token": token,
            "idempotency_key": idempotency_key,
            "prompt": request.prompt[:50] + "..." if len(request.prompt) > 50 else request.prompt
        }
    )

    try:
        result = await job_queue.submit_job(
            request=request,
            token=token,
            idempotency_key=idempotency_key
        )

        logger.info(f"Job {result.job_id} created successfully")

        # Return 202 Accepted with Location header
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=result.model_dump(mode='json'),
            headers={
                "Location": result.location,
                "X-Request-ID": x_request_id or "unknown"
            }
        )

    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "JOB_SUBMISSION_FAILED",
                    "message": "Failed to submit job",
                    "details": {"reason": str(e)}
                }
            }
        )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job status",
    description="""
    Get the current status and result of a job.

    **Status values:**
    - `queued`: Waiting in queue to be processed
    - `running`: Currently being processed
    - `succeeded`: Completed successfully (result available)
    - `failed`: Failed with error (error details available)
    - `canceled`: Cancelled by user
    - `expired`: Expired before completion

    **Example:**
    ```bash
    curl http://localhost:8000/api/v1/jobs/j_abc123def456
    ```
    """,
    responses={
        200: {"description": "Job status returned"},
        404: {"description": "Job not found"}
    }
)
async def get_job(
    job_id: str,
    _enabled: None = Depends(check_jobs_enabled)
) -> JobResponse:
    """
    Get job status and result.

    Returns complete job information including:
    - Current status and progress
    - Generated artifacts (if succeeded)
    - Error details (if failed)
    - Timestamps
    """
    job_data = await redis_client.get_job(job_id)

    if not job_data:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job {job_id} not found",
                    "details": {"job_id": job_id}
                }
            }
        )

    # Parse timestamps
    timestamps = JobTimestamps(
        queued_at=job_data["queued_at"],
        started_at=job_data.get("started_at"),
        finished_at=job_data.get("finished_at")
    )

    # Parse result if present
    result = None
    if job_data.get("result"):
        result = JobResult(**job_data["result"])

    # Parse error if present
    error = None
    if job_data.get("error"):
        error_data = job_data["error"]
        if isinstance(error_data, dict):
            error = JobError(**error_data)

    response = JobResponse(
        job_id=job_data["job_id"],
        status=JobStatus(job_data["status"]),
        progress=float(job_data.get("progress", 0.0)),
        submitted_by=job_data.get("owner_token"),
        params=job_data.get("params"),
        result=result,
        error=error,
        timestamps=timestamps
    )

    logger.debug(f"Returning status for job {job_id}: {response.status}")

    return response


@router.delete(
    "/{job_id}",
    response_model=JobCancelResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Cancel job",
    description="""
    Cancel a running or queued job.

    **Behavior:**
    - If `queued`: Job is removed from queue immediately
    - If `running`: Cancellation request sent to worker (best-effort, may take a few seconds)
    - If already finished: No effect, returns current status

    Returns `202 Accepted` because cancellation is asynchronous.

    **Example:**
    ```bash
    curl -X DELETE http://localhost:8000/api/v1/jobs/j_abc123def456
    ```
    """,
    responses={
        202: {"description": "Cancellation requested"},
        404: {"description": "Job not found"}
    }
)
async def cancel_job(
    job_id: str,
    _enabled: None = Depends(check_jobs_enabled)
) -> JobCancelResponse:
    """
    Cancel a job.

    Sends cancellation signal to worker if job is running.
    """
    logger.info(f"Cancellation requested for job {job_id}")

    success, new_status = await job_queue.cancel_job(job_id)

    if not success and new_status is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": f"Job {job_id} not found",
                    "details": {"job_id": job_id}
                }
            }
        )

    if not success:
        # Job exists but can't be cancelled (already finished)
        message = f"Job cannot be cancelled (current status: {new_status.value})"
    else:
        message = "Cancellation requested" if new_status == JobStatus.CANCELED else f"Job status: {new_status.value}"

    return JobCancelResponse(
        job_id=job_id,
        message=message,
        status=new_status
    )


@router.get(
    "",
    response_model=JobListResponse,
    summary="List jobs",
    description="""
    List recent jobs (filtered by authenticated user).

    **Note:** This endpoint requires authentication to prevent listing
    all jobs. In the current version, it returns a placeholder response.

    **Query Parameters:**
    - `limit`: Number of jobs per page (default: 20, max: 100)
    - `offset`: Page offset (default: 0)

    **Example:**
    ```bash
    curl "http://localhost:8000/api/v1/jobs?limit=10&offset=0"
    ```
    """,
    responses={
        200: {"description": "List of jobs"},
        401: {"description": "Authentication required"}
    }
)
async def list_jobs(
    limit: int = 20,
    offset: int = 0,
    _enabled: None = Depends(check_jobs_enabled)
) -> JobListResponse:
    """
    List jobs for the authenticated user.

    **TODO:** Implement with proper authentication and Redis SCAN.

    For now, returns empty list with note that feature is pending.
    """
    # TODO: Implement job listing
    # - Authenticate user
    # - Query Redis for user's jobs (use SCAN with pattern)
    # - Apply pagination
    # - Return results

    logger.info(f"Job list requested (limit={limit}, offset={offset})")

    return JobListResponse(
        jobs=[],
        total=0,
        limit=min(limit, 100),  # Cap at 100
        offset=offset
    )
