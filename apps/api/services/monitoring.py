"""
Monitoring and cost tracking service.

Tracks metrics for image generation, costs, and performance.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class CostTracker:
    """Track and estimate costs for image generation."""

    # GPU pricing (per hour)
    GPU_PRICING = {
        "cpu": 0.0,  # Local CPU - free
        "rtx_3060": 0.10,  # RunPod Spot
        "rtx_4000_ada": 0.15,  # RunPod Spot
        "rtx_4090": 0.40,  # RunPod On-Demand
        "a40": 0.50,  # RunPod On-Demand
        "local_gpu": 0.0,  # Local GPU - free (electricity ignored)
    }

    # Average generation times (seconds) by GPU type
    GENERATION_TIMES = {
        "cpu": {
            "512x512_10steps": 540,  # 9 minutes
            "512x512_20steps": 1080,  # 18 minutes
            "1024x1024_20steps": 3600,  # 60 minutes
        },
        "rtx_3060": {
            "512x512_10steps": 2,
            "512x512_20steps": 4,
            "1024x1024_20steps": 15,
        },
        "rtx_4000_ada": {
            "512x512_10steps": 1.5,
            "512x512_20steps": 3,
            "1024x1024_20steps": 10,
        },
        "rtx_4090": {
            "512x512_10steps": 0.8,
            "512x512_20steps": 1.5,
            "1024x1024_20steps": 5,
        },
        "local_gpu": {
            "512x512_10steps": 3,
            "512x512_20steps": 5,
            "1024x1024_20steps": 15,
        },
    }

    def __init__(self, gpu_type: str = "rtx_4000_ada"):
        """
        Initialize cost tracker.

        Args:
            gpu_type: Type of GPU being used (for cost estimation)
        """
        self.gpu_type = gpu_type
        self.hourly_rate = self.GPU_PRICING.get(gpu_type, 0.0)
        self.generation_times = self.GENERATION_TIMES.get(gpu_type, {})

    def estimate_cost(self, width: int, height: int, steps: int, num_images: int = 1) -> Dict:
        """
        Estimate cost for image generation.

        Args:
            width: Image width in pixels
            height: Image height in pixels
            steps: Number of diffusion steps
            num_images: Number of images to generate

        Returns:
            Dict with cost estimation details
        """
        # Categorize image size
        if width <= 512 and height <= 512:
            if steps <= 10:
                size_key = "512x512_10steps"
            else:
                size_key = "512x512_20steps"
        else:
            size_key = "1024x1024_20steps"

        # Get estimated time
        estimated_time_seconds = self.generation_times.get(size_key, 5.0)

        # Adjust for actual steps (rough approximation)
        if "10steps" in size_key and steps > 10:
            estimated_time_seconds *= (steps / 10)
        elif "20steps" in size_key and steps != 20:
            estimated_time_seconds *= (steps / 20)

        # Total time for batch
        total_time_seconds = estimated_time_seconds * num_images
        total_time_hours = total_time_seconds / 3600

        # Cost calculation
        estimated_cost = total_time_hours * self.hourly_rate

        return {
            "gpu_type": self.gpu_type,
            "hourly_rate": self.hourly_rate,
            "estimated_time_seconds": round(estimated_time_seconds, 2),
            "total_time_seconds": round(total_time_seconds, 2),
            "estimated_cost_usd": round(estimated_cost, 6),
            "cost_per_image": round(estimated_cost / num_images, 6) if num_images > 0 else 0,
            "num_images": num_images,
        }

    def calculate_actual_cost(self, duration_seconds: float) -> float:
        """
        Calculate actual cost based on generation duration.

        Args:
            duration_seconds: Actual time taken to generate image

        Returns:
            Cost in USD
        """
        hours = duration_seconds / 3600
        return hours * self.hourly_rate

    def project_monthly_cost(self, images_per_day: int, avg_time_seconds: float) -> Dict:
        """
        Project monthly costs based on usage patterns.

        Args:
            images_per_day: Average images generated per day
            avg_time_seconds: Average generation time per image

        Returns:
            Monthly cost projection
        """
        # Daily stats
        daily_time_seconds = images_per_day * avg_time_seconds
        daily_time_hours = daily_time_seconds / 3600
        daily_cost = daily_time_hours * self.hourly_rate

        # Monthly stats (30 days)
        monthly_images = images_per_day * 30
        monthly_hours = daily_time_hours * 30
        monthly_cost = daily_cost * 30

        return {
            "gpu_type": self.gpu_type,
            "hourly_rate": self.hourly_rate,
            "images_per_day": images_per_day,
            "daily_runtime_hours": round(daily_time_hours, 2),
            "daily_cost_usd": round(daily_cost, 2),
            "monthly_images": monthly_images,
            "monthly_runtime_hours": round(monthly_hours, 2),
            "monthly_cost_usd": round(monthly_cost, 2),
            "cost_per_image": round(monthly_cost / monthly_images, 4) if monthly_images > 0 else 0,
        }


class MetricsCollector:
    """Collect and aggregate metrics for monitoring."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "total_images": 0,
            "total_cost_usd": 0.0,
            "total_time_seconds": 0.0,
            "job_history": [],  # Last 100 jobs
        }

    def record_job(
        self,
        job_id: str,
        status: str,
        duration_seconds: Optional[float] = None,
        num_images: int = 0,
        cost_usd: float = 0.0,
        width: int = 0,
        height: int = 0,
        steps: int = 0,
    ):
        """
        Record a completed job.

        Args:
            job_id: Job identifier
            status: Job status (succeeded, failed, etc.)
            duration_seconds: How long the job took
            num_images: Number of images generated
            cost_usd: Estimated cost
            width: Image width
            height: Image height
            steps: Number of diffusion steps
        """
        self.metrics["total_jobs"] += 1

        if status == "succeeded":
            self.metrics["successful_jobs"] += 1
            self.metrics["total_images"] += num_images
            if duration_seconds:
                self.metrics["total_time_seconds"] += duration_seconds
            self.metrics["total_cost_usd"] += cost_usd
        else:
            self.metrics["failed_jobs"] += 1

        # Add to history (keep last 100)
        job_record = {
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "duration_seconds": duration_seconds,
            "num_images": num_images,
            "cost_usd": cost_usd,
            "width": width,
            "height": height,
            "steps": steps,
        }

        self.metrics["job_history"].append(job_record)
        if len(self.metrics["job_history"]) > 100:
            self.metrics["job_history"].pop(0)

    def get_stats(self) -> Dict:
        """
        Get current statistics.

        Returns:
            Current metrics and statistics
        """
        success_rate = 0.0
        if self.metrics["total_jobs"] > 0:
            success_rate = (self.metrics["successful_jobs"] / self.metrics["total_jobs"]) * 100

        avg_time = 0.0
        if self.metrics["successful_jobs"] > 0:
            avg_time = self.metrics["total_time_seconds"] / self.metrics["successful_jobs"]

        avg_cost = 0.0
        if self.metrics["total_images"] > 0:
            avg_cost = self.metrics["total_cost_usd"] / self.metrics["total_images"]

        return {
            "total_jobs": self.metrics["total_jobs"],
            "successful_jobs": self.metrics["successful_jobs"],
            "failed_jobs": self.metrics["failed_jobs"],
            "success_rate_percent": round(success_rate, 2),
            "total_images_generated": self.metrics["total_images"],
            "total_cost_usd": round(self.metrics["total_cost_usd"], 4),
            "total_runtime_seconds": round(self.metrics["total_time_seconds"], 2),
            "total_runtime_hours": round(self.metrics["total_time_seconds"] / 3600, 2),
            "avg_time_per_image_seconds": round(avg_time, 2),
            "avg_cost_per_image_usd": round(avg_cost, 4),
        }

    def get_recent_jobs(self, limit: int = 10) -> List[Dict]:
        """
        Get recent job history.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of recent jobs
        """
        return self.metrics["job_history"][-limit:][::-1]  # Most recent first


# Global instances
cost_tracker = CostTracker(gpu_type="rtx_4000_ada")  # Default to RTX 4000 Ada
metrics_collector = MetricsCollector()
