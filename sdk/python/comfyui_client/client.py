"""
ComfyUI API Client - Main implementation.
"""

import requests
import time
from typing import Optional, Dict, List, Any
from .exceptions import (
    APIError,
    JobNotFoundError,
    JobFailedError,
    TimeoutError,
    ConnectionError,
    AuthenticationError,
    RateLimitError,
)


class GenerationResult:
    """Represents a completed image generation job."""

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize generation result.

        Args:
            data: Raw job data from API
        """
        self.data = data
        self.job_id = data["job_id"]
        self.status = data["status"]
        self.result = data.get("result", {})
        self.artifacts = self.result.get("artifacts", [])
        self.error = data.get("error")

    def download_image(self, index: int = 0, save_path: str = "image.png") -> str:
        """
        Download a generated image.

        Args:
            index: Index of the artifact to download (default: 0)
            save_path: Path to save the image (default: "image.png")

        Returns:
            Path to the saved image

        Raises:
            ValueError: If no artifacts are available or index is out of range
            requests.HTTPError: If download fails
        """
        if not self.artifacts:
            raise ValueError(f"No artifacts available for job {self.job_id}")

        if index >= len(self.artifacts):
            raise ValueError(
                f"Artifact index {index} out of range (available: 0-{len(self.artifacts)-1})"
            )

        url = self.artifacts[index]["url"]
        response = requests.get(url)
        response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        return save_path

    def __repr__(self) -> str:
        return f"GenerationResult(job_id='{self.job_id}', status='{self.status}', artifacts={len(self.artifacts)})"


class Job:
    """Represents an image generation job."""

    def __init__(self, client: 'ComfyUIClient', job_id: str):
        """
        Initialize job.

        Args:
            client: ComfyUIClient instance
            job_id: Job identifier
        """
        self.client = client
        self.job_id = job_id
        self._last_status = None

    def status(self) -> Dict[str, Any]:
        """
        Get current job status.

        Returns:
            Job status data

        Raises:
            JobNotFoundError: If job doesn't exist
            APIError: If API request fails
        """
        self._last_status = self.client.get_job(self.job_id)
        return self._last_status

    def wait_for_completion(
        self,
        timeout: int = 600,
        poll_interval: int = 2,
        progress_callback: Optional[callable] = None
    ) -> GenerationResult:
        """
        Wait for job to complete.

        Args:
            timeout: Maximum time to wait in seconds (default: 600)
            poll_interval: Time between status checks in seconds (default: 2)
            progress_callback: Optional callback function called with status data

        Returns:
            GenerationResult when job completes successfully

        Raises:
            JobFailedError: If job fails
            TimeoutError: If job doesn't complete within timeout
            APIError: If API request fails
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time

            if elapsed >= timeout:
                raise TimeoutError(
                    f"Job {self.job_id} did not complete within {timeout}s",
                    job_id=self.job_id,
                    elapsed_time=elapsed
                )

            status_data = self.status()

            if progress_callback:
                progress_callback(status_data)

            job_status = status_data["status"]

            if job_status == "succeeded":
                return GenerationResult(status_data)

            elif job_status == "failed":
                error_msg = status_data.get("error", "Unknown error")
                raise JobFailedError(
                    f"Job {self.job_id} failed: {error_msg}",
                    job_id=self.job_id,
                    error_details=error_msg
                )

            # Job still running, wait and retry
            time.sleep(poll_interval)

    def cancel(self) -> Dict[str, Any]:
        """
        Cancel the job (if supported by API).

        Returns:
            Cancellation response

        Raises:
            APIError: If cancellation fails
        """
        # Note: Cancel endpoint may not be implemented yet
        return self.client._request("DELETE", f"/api/v1/jobs/{self.job_id}")

    def __repr__(self) -> str:
        status = self._last_status["status"] if self._last_status else "unknown"
        return f"Job(job_id='{self.job_id}', status='{status}')"


class ComfyUIClient:
    """
    Client for the ComfyUI API Service.

    Example:
        client = ComfyUIClient("http://localhost:8000", api_key="your-key")

        # Generate an image
        job = client.generate(
            prompt="A sunset over mountains",
            width=512,
            height=512
        )

        # Wait for completion
        result = job.wait_for_completion()
        result.download_image(save_path="sunset.png")
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize ComfyUI client.

        Args:
            base_url: Base URL of the API (e.g., "http://localhost:8000")
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

        if api_key:
            self.session.headers["X-API-Key"] = api_key

    def _request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            **kwargs: Additional request arguments

        Returns:
            Response data as dict

        Raises:
            ConnectionError: If connection fails
            AuthenticationError: If authentication fails (401)
            RateLimitError: If rate limit exceeded (429)
            APIError: For other API errors
        """
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)

            # Handle specific status codes
            if response.status_code == 401:
                raise AuthenticationError("Invalid API key")

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    "Rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None
                )

            if response.status_code == 404:
                # Check if it's a job not found error
                if "/jobs/" in path:
                    raise JobNotFoundError(f"Job not found: {path}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to {url}: {e}")

        except requests.exceptions.HTTPError as e:
            try:
                error_data = response.json()
                message = error_data.get("detail", str(e))
            except:
                message = str(e)

            raise APIError(
                message,
                status_code=response.status_code,
                response_data=error_data if 'error_data' in locals() else None
            )

    def health(self) -> Dict[str, Any]:
        """
        Check API health.

        Returns:
            Health status data
        """
        return self._request("GET", "/health")

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler: str = "euler_ancestral",
        scheduler: str = "normal",
        seed: Optional[int] = None,
        num_images: int = 1,
        model: str = "v1-5-pruned-emaonly.ckpt",
        **kwargs
    ) -> Job:
        """
        Submit an image generation job.

        Args:
            prompt: Text prompt describing the image
            negative_prompt: What to avoid in the image (default: "")
            width: Image width in pixels (default: 512)
            height: Image height in pixels (default: 512)
            steps: Number of diffusion steps (default: 20)
            cfg_scale: Classifier-free guidance scale (default: 7.0)
            sampler: Sampling method (default: "euler_ancestral")
            scheduler: Scheduler type (default: "normal")
            seed: Random seed for reproducibility (optional)
            num_images: Number of images to generate (default: 1)
            model: Model filename (default: "v1-5-pruned-emaonly.ckpt")
            **kwargs: Additional parameters

        Returns:
            Job object for tracking the generation

        Raises:
            APIError: If job submission fails
        """
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler": sampler,
            "scheduler": scheduler,
            "num_images": num_images,
            "model": model,
            **kwargs
        }

        if seed is not None:
            payload["seed"] = seed

        response = self._request("POST", "/api/v1/jobs", json=payload)
        return Job(self, response["job_id"])

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status and results.

        Args:
            job_id: Job identifier

        Returns:
            Job data including status and results

        Raises:
            JobNotFoundError: If job doesn't exist
            APIError: If request fails
        """
        return self._request("GET", f"/api/v1/jobs/{job_id}")

    def list_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent jobs (if supported by API).

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job data dicts
        """
        # Note: This endpoint may not be implemented yet
        return self._request("GET", f"/api/v1/jobs?limit={limit}")

    # Monitoring endpoints

    def estimate_cost(
        self,
        width: int,
        height: int,
        steps: int,
        num_images: int = 1
    ) -> Dict[str, Any]:
        """
        Estimate cost for image generation.

        Args:
            width: Image width
            height: Image height
            steps: Number of diffusion steps
            num_images: Number of images (default: 1)

        Returns:
            Cost estimation data including time and cost in USD
        """
        return self._request(
            "POST",
            "/api/v1/monitoring/estimate-cost",
            params={
                "width": width,
                "height": height,
                "steps": steps,
                "num_images": num_images
            }
        )

    def get_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics.

        Returns:
            Statistics including total jobs, costs, and performance metrics
        """
        return self._request("GET", "/api/v1/monitoring/stats")

    def project_monthly_cost(
        self,
        images_per_day: int,
        avg_time_seconds: float
    ) -> Dict[str, Any]:
        """
        Project monthly costs based on usage.

        Args:
            images_per_day: Average images generated per day
            avg_time_seconds: Average generation time per image

        Returns:
            Monthly cost projection
        """
        return self._request(
            "GET",
            "/api/v1/monitoring/project-monthly-cost",
            params={
                "images_per_day": images_per_day,
                "avg_time_seconds": avg_time_seconds
            }
        )

    def configure_gpu(self, gpu_type: str) -> Dict[str, Any]:
        """
        Configure GPU type for cost estimation.

        Args:
            gpu_type: GPU type (e.g., "rtx_4000_ada", "rtx_3060", "cpu")

        Returns:
            Configuration confirmation
        """
        return self._request(
            "POST",
            "/api/v1/monitoring/configure-gpu",
            params={"gpu_type": gpu_type}
        )

    def __repr__(self) -> str:
        return f"ComfyUIClient(base_url='{self.base_url}')"
