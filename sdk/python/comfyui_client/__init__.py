"""
ComfyUI API Client

A Python SDK for the ComfyUI API Service.

Example usage:
    from comfyui_client import ComfyUIClient

    client = ComfyUIClient("http://localhost:8000")

    # Generate an image
    job = client.generate(
        prompt="A beautiful sunset over mountains",
        width=512,
        height=512
    )

    # Wait for completion
    result = job.wait_for_completion()
    print(f"Image URL: {result.artifacts[0]['url']}")
"""

from .client import ComfyUIClient, Job, GenerationResult
from .exceptions import (
    ComfyUIClientError,
    APIError,
    JobNotFoundError,
    JobFailedError,
    TimeoutError as JobTimeoutError,
)

__version__ = "1.0.0"
__all__ = [
    "ComfyUIClient",
    "Job",
    "GenerationResult",
    "ComfyUIClientError",
    "APIError",
    "JobNotFoundError",
    "JobFailedError",
    "JobTimeoutError",
]
