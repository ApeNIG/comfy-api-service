"""
Monitoring and cost tracking endpoints.
"""

from fastapi import APIRouter, Query
from typing import Optional
from apps.api.services.monitoring import cost_tracker, metrics_collector

router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring"])


@router.get("/stats")
async def get_stats():
    """
    Get current statistics and metrics.

    Returns overall stats including total jobs, costs, and performance.
    """
    return metrics_collector.get_stats()


@router.get("/recent-jobs")
async def get_recent_jobs(limit: int = Query(default=10, ge=1, le=100)):
    """
    Get recent job history.

    Args:
        limit: Number of recent jobs to return (1-100)

    Returns:
        List of recent jobs with their metrics
    """
    return {
        "jobs": metrics_collector.get_recent_jobs(limit=limit),
        "total_tracked": len(metrics_collector.metrics["job_history"]),
    }


@router.post("/estimate-cost")
async def estimate_cost(
    width: int = Query(default=512, ge=64, le=2048),
    height: int = Query(default=512, ge=64, le=2048),
    steps: int = Query(default=20, ge=1, le=150),
    num_images: int = Query(default=1, ge=1, le=10),
):
    """
    Estimate cost for image generation.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        steps: Number of diffusion steps
        num_images: Number of images to generate

    Returns:
        Cost estimation details
    """
    return cost_tracker.estimate_cost(
        width=width,
        height=height,
        steps=steps,
        num_images=num_images,
    )


@router.get("/project-monthly-cost")
async def project_monthly_cost(
    images_per_day: int = Query(default=10, ge=1, le=10000),
    avg_time_seconds: float = Query(default=3.0, ge=0.1, le=3600),
):
    """
    Project monthly costs based on usage patterns.

    Args:
        images_per_day: Average number of images generated per day
        avg_time_seconds: Average generation time per image

    Returns:
        Monthly cost projection
    """
    return cost_tracker.project_monthly_cost(
        images_per_day=images_per_day,
        avg_time_seconds=avg_time_seconds,
    )


@router.get("/gpu-pricing")
async def get_gpu_pricing():
    """
    Get GPU pricing information for different providers.

    Returns:
        Pricing details for various GPU types
    """
    return {
        "pricing": cost_tracker.GPU_PRICING,
        "current_gpu": cost_tracker.gpu_type,
        "current_hourly_rate": cost_tracker.hourly_rate,
        "generation_times": cost_tracker.generation_times,
    }


@router.post("/configure-gpu")
async def configure_gpu(gpu_type: str = Query(default="rtx_4000_ada")):
    """
    Configure GPU type for cost estimation.

    Args:
        gpu_type: GPU type (cpu, rtx_3060, rtx_4000_ada, rtx_4090, a40, local_gpu)

    Returns:
        Updated configuration
    """
    if gpu_type not in cost_tracker.GPU_PRICING:
        return {
            "error": f"Unknown GPU type: {gpu_type}",
            "available_types": list(cost_tracker.GPU_PRICING.keys()),
        }

    cost_tracker.gpu_type = gpu_type
    cost_tracker.hourly_rate = cost_tracker.GPU_PRICING[gpu_type]
    cost_tracker.generation_times = cost_tracker.GENERATION_TIMES.get(gpu_type, {})

    return {
        "gpu_type": cost_tracker.gpu_type,
        "hourly_rate": cost_tracker.hourly_rate,
        "message": f"Cost tracker configured for {gpu_type}",
    }
