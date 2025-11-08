"""ComfyUI HTTP client service for API communication."""

import httpx
import json
import uuid
import asyncio
import os
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from prometheus_client import Counter, Histogram, Gauge

from ..models.requests import GenerateImageRequest
from ..models.responses import ImageResponse, JobStatus, ImageMetadata

logger = logging.getLogger(__name__)

# Prometheus metrics
GENERATION_TOTAL = Counter(
    "generation_total",
    "Total image generations",
    ["status", "model"]
)
GENERATION_LATENCY = Histogram(
    "generation_seconds",
    "Image generation latency in seconds",
    buckets=(2, 4, 8, 12, 20, 30, 45, 60, 120, 300)
)
COMFY_QUEUE_DEPTH = Gauge(
    "comfy_queue_depth",
    "Approximate ComfyUI queue depth"
)
COMFY_REQUEST_TOTAL = Counter(
    "comfy_request_total",
    "Total ComfyUI API requests",
    ["endpoint", "status_code"]
)


class ComfyUIClientError(Exception):
    """Base exception for ComfyUI client errors."""
    pass


class ComfyUIConnectionError(ComfyUIClientError):
    """Raised when unable to connect to ComfyUI."""
    pass


class ComfyUITimeoutError(ComfyUIClientError):
    """Raised when ComfyUI request times out."""
    pass


class ComfyUIClient:
    """
    Async HTTP client for ComfyUI API.

    This service handles all communication with the ComfyUI backend,
    including workflow submission, status checking, and image retrieval.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        timeout: float = 300.0,
        poll_interval: float = 1.0,
        workflow_path: Optional[str] = None
    ):
        """
        Initialize ComfyUI client.

        Args:
            base_url: Base URL for ComfyUI service
            timeout: Request timeout in seconds
            poll_interval: Interval between status checks in seconds
            workflow_path: Path to workflow JSON template (optional)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.client_id = str(uuid.uuid4())
        self.workflow_path = workflow_path or os.path.join(
            os.path.dirname(__file__), "../../../workflows/t2i_basic.json"
        )

        # Configure httpx client
        self._client: Optional[httpx.AsyncClient] = None

        # Load workflow template
        self._workflow_template: Optional[Dict[str, Any]] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client instance."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with ComfyUIClient()' context manager.")
        return self._client

    async def health_check(self) -> bool:
        """
        Check if ComfyUI service is available.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = await self.client.get("/system_stats")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_models(self) -> list[str]:
        """
        Get list of available models from ComfyUI.

        Returns:
            List of model filenames

        Raises:
            ComfyUIConnectionError: If unable to connect to ComfyUI
        """
        try:
            response = await self.client.get("/object_info")
            response.raise_for_status()

            data = response.json()

            # Extract model names from object_info
            # ComfyUI stores models under different node types
            models = []
            if "CheckpointLoaderSimple" in data:
                checkpoint_info = data["CheckpointLoaderSimple"]
                if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                    if "ckpt_name" in checkpoint_info["input"]["required"]:
                        model_list = checkpoint_info["input"]["required"]["ckpt_name"]
                        if isinstance(model_list, list) and len(model_list) > 0:
                            models = model_list[0]

            return models if isinstance(models, list) else []

        except httpx.ConnectError as e:
            raise ComfyUIConnectionError(f"Cannot connect to ComfyUI at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise ComfyUITimeoutError("Request to ComfyUI timed out") from e
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            raise ComfyUIClientError(f"Failed to get models: {str(e)}") from e

    def _load_workflow_template(self) -> Dict[str, Any]:
        """
        Load workflow template from JSON file.

        Returns:
            Workflow template dictionary
        """
        if self._workflow_template is None:
            try:
                with open(self.workflow_path, 'r') as f:
                    self._workflow_template = json.load(f)
                logger.info(f"Loaded workflow template from {self.workflow_path}")
            except FileNotFoundError:
                logger.warning(f"Workflow template not found at {self.workflow_path}, using built-in")
                # Fallback to built-in workflow
                self._workflow_template = self._get_default_workflow()
        return json.loads(json.dumps(self._workflow_template))  # Deep copy

    def _get_default_workflow(self) -> Dict[str, Any]:
        """
        Get default built-in workflow template.

        Returns:
            Default workflow dictionary
        """
        return {
            "3": {"inputs": {"seed": 42, "steps": 20, "cfg": 7.0, "sampler_name": "euler_a", "scheduler": "normal", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}, "class_type": "KSampler"},
            "4": {"inputs": {"ckpt_name": "v1-5-pruned-emaonly.safetensors"}, "class_type": "CheckpointLoaderSimple"},
            "5": {"inputs": {"width": 512, "height": 512, "batch_size": 1}, "class_type": "EmptyLatentImage"},
            "6": {"inputs": {"text": "beautiful scenery", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
            "7": {"inputs": {"text": "", "clip": ["4", 1]}, "class_type": "CLIPTextEncode"},
            "8": {"inputs": {"samples": ["3", 0], "vae": ["4", 2]}, "class_type": "VAEDecode"},
            "9": {"inputs": {"filename_prefix": "ComfyUI", "images": ["8", 0]}, "class_type": "SaveImage"}
        }

    def _build_workflow(self, request: GenerateImageRequest) -> Dict[str, Any]:
        """
        Build ComfyUI workflow from generation request.

        Loads workflow template and injects parameters.

        Args:
            request: Image generation request

        Returns:
            ComfyUI workflow dictionary
        """
        # Load template
        workflow = self._load_workflow_template()

        # Generate a random seed if not provided
        seed = request.seed if request.seed is not None and request.seed >= 0 else \
               int(datetime.utcnow().timestamp() * 1000000) % (2**32)

        # Inject parameters into workflow nodes
        # Node 3: KSampler
        if "3" in workflow:
            workflow["3"]["inputs"]["seed"] = seed
            workflow["3"]["inputs"]["steps"] = request.steps
            workflow["3"]["inputs"]["cfg"] = request.cfg_scale
            workflow["3"]["inputs"]["sampler_name"] = request.sampler.value

        # Node 4: Checkpoint Loader
        if "4" in workflow:
            workflow["4"]["inputs"]["ckpt_name"] = request.model

        # Node 5: Empty Latent Image
        if "5" in workflow:
            workflow["5"]["inputs"]["width"] = request.width
            workflow["5"]["inputs"]["height"] = request.height
            workflow["5"]["inputs"]["batch_size"] = request.batch_size

        # Node 6: Positive Prompt
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = request.prompt

        # Node 7: Negative Prompt
        if "7" in workflow:
            workflow["7"]["inputs"]["text"] = request.negative_prompt or ""

        # Node 9: Save Image
        if "9" in workflow:
            workflow["9"]["inputs"]["filename_prefix"] = f"api_generated_{uuid.uuid4().hex[:8]}"

        return workflow

    async def submit_prompt(self, request: GenerateImageRequest) -> str:
        """
        Submit a generation request to ComfyUI.

        Args:
            request: Image generation request

        Returns:
            Prompt ID (job ID)

        Raises:
            ComfyUIClientError: If submission fails
        """
        try:
            workflow = self._build_workflow(request)

            payload = {
                "prompt": workflow,
                "client_id": self.client_id
            }

            logger.info(f"Submitting prompt to ComfyUI: {request.prompt[:50]}...")

            response = await self.client.post(
                "/prompt",
                json=payload
            )
            response.raise_for_status()

            result = response.json()

            if "prompt_id" not in result:
                raise ComfyUIClientError("No prompt_id in response")

            prompt_id = result["prompt_id"]
            logger.info(f"Prompt submitted successfully. Job ID: {prompt_id}")

            return prompt_id

        except httpx.ConnectError as e:
            raise ComfyUIConnectionError(f"Cannot connect to ComfyUI at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise ComfyUITimeoutError("Request to ComfyUI timed out") from e
        except Exception as e:
            logger.error(f"Error submitting prompt: {e}")
            raise ComfyUIClientError(f"Failed to submit prompt: {str(e)}") from e

    async def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution history for a prompt.

        Args:
            prompt_id: The prompt ID to check

        Returns:
            History data or None if not found

        Raises:
            ComfyUIClientError: If request fails
        """
        try:
            response = await self.client.get(f"/history/{prompt_id}")
            response.raise_for_status()

            data = response.json()

            if prompt_id in data:
                return data[prompt_id]

            return None

        except httpx.ConnectError as e:
            raise ComfyUIConnectionError(f"Cannot connect to ComfyUI at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise ComfyUITimeoutError("Request to ComfyUI timed out") from e
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            raise ComfyUIClientError(f"Failed to get history: {str(e)}") from e

    async def get_queue(self) -> Dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Queue information

        Raises:
            ComfyUIClientError: If request fails
        """
        try:
            response = await self.client.get("/queue")
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error getting queue: {e}")
            raise ComfyUIClientError(f"Failed to get queue: {str(e)}") from e

    async def wait_for_completion(
        self,
        prompt_id: str,
        max_wait_time: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Wait for a prompt to complete execution.

        Args:
            prompt_id: The prompt ID to wait for
            max_wait_time: Maximum time to wait in seconds (None = use default timeout)

        Returns:
            History data when completed

        Raises:
            ComfyUITimeoutError: If max wait time exceeded
            ComfyUIClientError: If execution fails
        """
        max_wait = max_wait_time or self.timeout
        start_time = asyncio.get_event_loop().time()

        logger.info(f"Waiting for job {prompt_id} to complete...")

        while True:
            # Check if we've exceeded max wait time
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                raise ComfyUITimeoutError(f"Job {prompt_id} did not complete within {max_wait}s")

            # Get history
            history = await self.get_history(prompt_id)

            if history is not None:
                # Check if execution completed
                status = history.get("status", {})

                if status.get("completed", False):
                    logger.info(f"Job {prompt_id} completed successfully")
                    return history

                # Check for errors
                if "error" in status or status.get("status_str") == "error":
                    error_msg = status.get("error", "Unknown error")
                    logger.error(f"Job {prompt_id} failed: {error_msg}")
                    raise ComfyUIClientError(f"Execution failed: {error_msg}")

            # Wait before next check
            await asyncio.sleep(self.poll_interval)

    async def get_image_url(self, prompt_id: str, history: Dict[str, Any]) -> Optional[str]:
        """
        Extract image URL from history data.

        Args:
            prompt_id: The prompt ID
            history: History data from ComfyUI

        Returns:
            Image URL or None if not found
        """
        try:
            # Navigate through history structure to find saved images
            outputs = history.get("outputs", {})

            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    images = node_output["images"]
                    if len(images) > 0:
                        image_info = images[0]
                        filename = image_info.get("filename")
                        subfolder = image_info.get("subfolder", "")
                        image_type = image_info.get("type", "output")

                        # Construct URL to view the image
                        if filename:
                            url = f"/view?filename={filename}&type={image_type}"
                            if subfolder:
                                url += f"&subfolder={subfolder}"
                            return url

            return None

        except Exception as e:
            logger.error(f"Error extracting image URL: {e}")
            return None

    async def generate_image(self, request: GenerateImageRequest) -> ImageResponse:
        """
        Generate an image (full workflow: submit, wait, get result).

        This is the main method that combines all steps into one call.

        Args:
            request: Image generation request

        Returns:
            ImageResponse with generation results

        Raises:
            ComfyUIClientError: If generation fails
        """
        job_id = None
        created_at = datetime.utcnow()
        started_at = None
        completed_at = None
        model = request.model or "default"

        try:
            # Submit prompt
            job_id = await self.submit_prompt(request)
            started_at = datetime.utcnow()

            # Wait for completion
            history = await self.wait_for_completion(job_id)
            completed_at = datetime.utcnow()

            # Get image URL
            image_url = await self.get_image_url(job_id, history)

            # Calculate generation time
            generation_time = (completed_at - started_at).total_seconds() if started_at else None

            # Track metrics
            GENERATION_TOTAL.labels(status="success", model=model).inc()
            if generation_time:
                GENERATION_LATENCY.observe(generation_time)

            # Build metadata
            metadata = ImageMetadata(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                width=request.width,
                height=request.height,
                steps=request.steps,
                cfg_scale=request.cfg_scale,
                sampler=request.sampler.value,
                seed=request.seed or -1,
                model=request.model,
                generation_time=generation_time
            )

            return ImageResponse(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                image_url=image_url,
                metadata=metadata,
                created_at=created_at,
                started_at=started_at,
                completed_at=completed_at
            )

        except Exception as e:
            logger.error(f"Image generation failed: {e}")

            # Track failure
            GENERATION_TOTAL.labels(status="error", model=model).inc()

            return ImageResponse(
                job_id=job_id or "unknown",
                status=JobStatus.FAILED,
                error=str(e),
                created_at=created_at,
                started_at=started_at,
                completed_at=datetime.utcnow()
            )


# Dependency injection for FastAPI
async def get_comfyui_client() -> ComfyUIClient:
    """
    FastAPI dependency for ComfyUI client.

    Usage:
        @router.post("/generate")
        async def generate(
            request: GenerateImageRequest,
            client: ComfyUIClient = Depends(get_comfyui_client)
        ):
            async with client:
                return await client.generate_image(request)
    """
    return ComfyUIClient()
