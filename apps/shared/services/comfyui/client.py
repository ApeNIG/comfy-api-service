"""
ComfyUI service client

Handles all communication with ComfyUI backend:
- Submit workflows
- Track job progress via WebSocket
- Download results
- Handle errors gracefully

This is the bridge between our Creator product and ComfyUI's image generation.
"""

import asyncio
import json
import uuid
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

import aiohttp
import websockets
from websockets.exceptions import ConnectionClosed

from apps.shared.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)


class ComfyUIStatus(str, Enum):
    """ComfyUI job status."""
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ComfyUIResult:
    """Result from ComfyUI execution."""
    prompt_id: str
    status: ComfyUIStatus
    images: list[str] = None  # List of output image filenames
    error: Optional[str] = None
    node_errors: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None


class ComfyUIClient:
    """
    Client for interacting with ComfyUI API.

    Supports:
    - Submitting workflows (prompt queue)
    - Real-time progress tracking (WebSocket)
    - Result retrieval
    - Error handling

    Usage:
        client = ComfyUIClient()

        # Submit workflow
        result = await client.execute_workflow(workflow_json, {"image_url": "..."})

        # Stream progress updates
        async for progress in client.stream_progress(prompt_id):
            print(f"Progress: {progress['value']}%")

        # Get result
        images = await client.get_output_images(prompt_id)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        """
        Initialize ComfyUI client.

        Args:
            base_url: ComfyUI server URL (defaults to settings.COMFYUI_URL)
            timeout: Request timeout in seconds (defaults to settings.COMFYUI_TIMEOUT)
        """
        self.base_url = (base_url or settings.COMFYUI_URL).rstrip("/")
        self.timeout = timeout or settings.COMFYUI_TIMEOUT

        # Convert http(s) to ws(s) for WebSocket
        self.ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")

        logger.info(
            "comfyui_client_initialized",
            base_url=self.base_url,
            timeout=self.timeout,
        )

    async def queue_prompt(
        self,
        workflow: Dict[str, Any],
        client_id: Optional[str] = None,
    ) -> str:
        """
        Queue a workflow for execution.

        Args:
            workflow: ComfyUI workflow JSON (nodes and connections)
            client_id: Optional client ID for WebSocket tracking

        Returns:
            Prompt ID (job ID) for tracking

        Example:
            >>> workflow = {...}  # ComfyUI workflow JSON
            >>> prompt_id = await client.queue_prompt(workflow)
            >>> print(f"Job queued: {prompt_id}")
        """
        client_id = client_id or str(uuid.uuid4())

        payload = {
            "prompt": workflow,
            "client_id": client_id,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/prompt",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    prompt_id = data.get("prompt_id")

                    logger.info(
                        "comfyui_prompt_queued",
                        prompt_id=prompt_id,
                        client_id=client_id,
                    )

                    return prompt_id

        except aiohttp.ClientError as e:
            logger.error(
                "comfyui_queue_failed",
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_history(self, prompt_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution history for a prompt.

        Args:
            prompt_id: Prompt ID to query

        Returns:
            History data or None if not found

        Example:
            >>> history = await client.get_history(prompt_id)
            >>> print(history['status'])
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/history/{prompt_id}",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 404:
                        return None

                    response.raise_for_status()
                    data = await response.json()

                    # History is keyed by prompt_id
                    return data.get(prompt_id)

        except aiohttp.ClientError as e:
            logger.error(
                "comfyui_get_history_failed",
                prompt_id=prompt_id,
                error=str(e),
            )
            return None

    async def get_output_images(self, prompt_id: str) -> list[bytes]:
        """
        Download output images from completed job.

        Args:
            prompt_id: Prompt ID of completed job

        Returns:
            List of image bytes

        Example:
            >>> images = await client.get_output_images(prompt_id)
            >>> for i, img_data in enumerate(images):
            ...     with open(f"output_{i}.png", "wb") as f:
            ...         f.write(img_data)
        """
        history = await self.get_history(prompt_id)

        if not history:
            logger.warning("comfyui_no_history", prompt_id=prompt_id)
            return []

        # Extract output images from history
        images = []
        outputs = history.get("outputs", {})

        for node_id, node_output in outputs.items():
            if "images" in node_output:
                for image_info in node_output["images"]:
                    filename = image_info.get("filename")
                    subfolder = image_info.get("subfolder", "")
                    folder_type = image_info.get("type", "output")

                    # Download image
                    image_data = await self.download_image(
                        filename=filename,
                        subfolder=subfolder,
                        folder_type=folder_type,
                    )

                    if image_data:
                        images.append(image_data)

        logger.info(
            "comfyui_images_downloaded",
            prompt_id=prompt_id,
            count=len(images),
        )

        return images

    async def download_image(
        self,
        filename: str,
        subfolder: str = "",
        folder_type: str = "output",
    ) -> Optional[bytes]:
        """
        Download a single image from ComfyUI.

        Args:
            filename: Image filename
            subfolder: Optional subfolder
            folder_type: Folder type (output, input, temp)

        Returns:
            Image bytes or None if failed
        """
        params = {
            "filename": filename,
            "type": folder_type,
        }

        if subfolder:
            params["subfolder"] = subfolder

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/view",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    return await response.read()

        except aiohttp.ClientError as e:
            logger.error(
                "comfyui_download_image_failed",
                filename=filename,
                error=str(e),
            )
            return None

    async def stream_progress(
        self,
        prompt_id: str,
        client_id: Optional[str] = None,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Stream real-time progress updates via WebSocket.

        Args:
            prompt_id: Prompt ID to track
            client_id: Client ID used when queuing
            callback: Optional callback for each progress update

        Yields:
            Progress updates as dictionaries

        Example:
            >>> async for update in client.stream_progress(prompt_id):
            ...     print(f"Node: {update['node']}, Progress: {update['value']}%")
        """
        client_id = client_id or str(uuid.uuid4())

        ws_url = f"{self.ws_url}/ws?clientId={client_id}"

        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info(
                    "comfyui_websocket_connected",
                    prompt_id=prompt_id,
                    client_id=client_id,
                )

                while True:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=self.timeout,
                        )

                        data = json.loads(message)
                        msg_type = data.get("type")

                        # Filter for progress updates related to our prompt
                        if msg_type == "progress" and data.get("data", {}).get("prompt_id") == prompt_id:
                            progress_data = {
                                "type": "progress",
                                "node": data["data"].get("node"),
                                "value": data["data"].get("value"),
                                "max": data["data"].get("max"),
                            }

                            if callback:
                                callback(progress_data)

                            yield progress_data

                        # Job completed
                        elif msg_type == "executed" and data.get("data", {}).get("prompt_id") == prompt_id:
                            completion_data = {
                                "type": "completed",
                                "node": data["data"].get("node"),
                            }

                            if callback:
                                callback(completion_data)

                            yield completion_data

                        # Job failed
                        elif msg_type == "execution_error" and data.get("data", {}).get("prompt_id") == prompt_id:
                            error_data = {
                                "type": "error",
                                "node": data["data"].get("node"),
                                "error": data["data"].get("exception_message"),
                            }

                            if callback:
                                callback(error_data)

                            yield error_data
                            break

                    except asyncio.TimeoutError:
                        logger.warning(
                            "comfyui_websocket_timeout",
                            prompt_id=prompt_id,
                        )
                        break

        except ConnectionClosed:
            logger.info(
                "comfyui_websocket_closed",
                prompt_id=prompt_id,
            )

        except Exception as e:
            logger.error(
                "comfyui_websocket_error",
                prompt_id=prompt_id,
                error=str(e),
                exc_info=True,
            )

    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        wait_for_completion: bool = True,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> ComfyUIResult:
        """
        Execute a workflow and optionally wait for completion.

        This is the high-level method that handles the full lifecycle:
        1. Queue the workflow
        2. Stream progress updates (if wait_for_completion=True)
        3. Download results
        4. Return structured result

        Args:
            workflow: ComfyUI workflow JSON
            wait_for_completion: Wait for job to finish
            progress_callback: Optional callback for progress updates

        Returns:
            ComfyUIResult with status and outputs

        Example:
            >>> workflow = load_workflow("thumbnail.json")
            >>> result = await client.execute_workflow(workflow)
            >>> if result.status == ComfyUIStatus.COMPLETED:
            ...     print(f"Generated {len(result.images)} images")
        """
        client_id = str(uuid.uuid4())

        # Queue the workflow
        prompt_id = await self.queue_prompt(workflow, client_id)

        if not wait_for_completion:
            return ComfyUIResult(
                prompt_id=prompt_id,
                status=ComfyUIStatus.QUEUED,
            )

        # Stream progress and wait for completion
        final_status = ComfyUIStatus.EXECUTING
        error_message = None

        try:
            async for update in self.stream_progress(prompt_id, client_id, progress_callback):
                if update["type"] == "completed":
                    final_status = ComfyUIStatus.COMPLETED
                elif update["type"] == "error":
                    final_status = ComfyUIStatus.FAILED
                    error_message = update.get("error")
                    break

        except Exception as e:
            final_status = ComfyUIStatus.FAILED
            error_message = str(e)

        # Get history for node errors
        history = await self.get_history(prompt_id)
        node_errors = history.get("status", {}).get("messages", []) if history else None

        # Download images if completed
        images = []
        if final_status == ComfyUIStatus.COMPLETED:
            images = await self.get_output_images(prompt_id)

        return ComfyUIResult(
            prompt_id=prompt_id,
            status=final_status,
            images=[f"{prompt_id}_{i}.png" for i in range(len(images))],  # Placeholder names
            error=error_message,
            node_errors=node_errors,
        )

    async def health_check(self) -> bool:
        """
        Check if ComfyUI server is healthy.

        Returns:
            True if server is reachable and responding

        Example:
            >>> is_healthy = await client.health_check()
            >>> print(f"ComfyUI healthy: {is_healthy}")
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/system_stats",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(
                "comfyui_health_check_failed",
                error=str(e),
            )
            return False


# Singleton instance
_client: Optional[ComfyUIClient] = None


def get_comfyui_client() -> ComfyUIClient:
    """
    Get singleton ComfyUI client instance.

    Returns:
        ComfyUIClient instance

    Usage:
        from apps.shared.services.comfyui import get_comfyui_client

        client = get_comfyui_client()
        result = await client.execute_workflow(workflow)
    """
    global _client

    if _client is None:
        _client = ComfyUIClient()

    return _client
