"""
WebSocket endpoints for real-time job progress updates.

Provides live streaming of job status, progress, and completion events.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
import json
import logging
import asyncio

from ..services.redis_client import redis_client
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


async def check_websocket_enabled():
    """Dependency to check if WebSocket feature is enabled."""
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

    **Connection:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/jobs/j_abc123def456');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Progress:', data);
    };
    ```

    **Message Types:**

    1. **Status Update:**
    ```json
    {
      "type": "status",
      "status": "running",
      "progress": 0.0
    }
    ```

    2. **Progress Update:**
    ```json
    {
      "type": "progress",
      "progress": 0.42,
      "message": "Denoising step 12/28"
    }
    ```

    3. **Log Message:**
    ```json
    {
      "type": "log",
      "message": "Uploading artifacts to storage"
    }
    ```

    4. **Artifact Available:**
    ```json
    {
      "type": "artifact",
      "url": "https://storage.example.com/jobs/j_abc/image_0.png"
    }
    ```

    5. **Job Complete:**
    ```json
    {
      "type": "done",
      "status": "succeeded",
      "result": {
        "artifacts": [
          {
            "url": "https://...",
            "seed": 42
          }
        ]
      }
    }
    ```

    **Connection closes automatically after job completion.**
    """
    # Check if WebSocket is enabled
    if not settings.websocket_enabled:
        await websocket.close(code=1008, reason="WebSocket support disabled")
        return

    # Check if job exists
    job_data = await redis_client.get_job(job_id)
    if not job_data:
        await websocket.close(code=1008, reason=f"Job {job_id} not found")
        logger.warning(f"WebSocket connection rejected: job {job_id} not found")
        return

    # Accept WebSocket connection
    await websocket.accept()
    logger.info(f"WebSocket connected for job {job_id}")

    # Send current status immediately
    try:
        await websocket.send_json({
            "type": "status",
            "status": job_data["status"],
            "progress": float(job_data.get("progress", 0.0))
        })
    except Exception as e:
        logger.error(f"Failed to send initial status for job {job_id}: {e}")
        await websocket.close()
        return

    # If job is already finished, send final message and close
    if job_data["status"] in ["succeeded", "failed", "canceled", "expired"]:
        try:
            done_message = {
                "type": "done",
                "status": job_data["status"]
            }

            if job_data.get("result"):
                done_message["result"] = job_data["result"]

            if job_data.get("error"):
                done_message["error"] = job_data["error"]

            await websocket.send_json(done_message)
            logger.info(f"Job {job_id} already finished, sent final message")
        except Exception as e:
            logger.error(f"Failed to send final message for job {job_id}: {e}")
        finally:
            await websocket.close()
            return

    # Subscribe to Redis pub/sub for progress updates
    pubsub = await redis_client.subscribe_progress(job_id)

    try:
        # Listen for messages from Redis pub/sub
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # Parse and forward message to WebSocket client
                    data = json.loads(message["data"])

                    await websocket.send_json(data)

                    logger.debug(f"Forwarded progress update for job {job_id}: {data.get('type')}")

                    # Close connection after "done" event
                    if data.get("type") == "done":
                        logger.info(f"Job {job_id} completed, closing WebSocket")
                        break

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse message for job {job_id}: {e}")
                    continue

                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for job {job_id}")
                    break

                except Exception as e:
                    logger.error(f"Error forwarding message for job {job_id}: {e}")
                    break

    except WebSocketDisconnect:
        logger.info(f"Client disconnected WebSocket for job {job_id}")

    except Exception as e:
        logger.exception(f"WebSocket error for job {job_id}: {e}")

    finally:
        # Clean up pub/sub subscription
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
            logger.debug(f"Unsubscribed from Redis channel for job {job_id}")
        except Exception as e:
            logger.error(f"Error unsubscribing from Redis for job {job_id}: {e}")

        # Close WebSocket if still open
        try:
            await websocket.close()
        except Exception:
            pass  # Already closed

        logger.info(f"WebSocket connection closed for job {job_id}")
