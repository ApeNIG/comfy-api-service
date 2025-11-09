"""Health check and monitoring endpoints."""

import logging
import asyncio
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from datetime import datetime

from ..models.responses import HealthResponse, ModelsListResponse, ModelInfo
from ..services.comfyui_client import ComfyUIClient, get_comfyui_client

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Health & Monitoring"]
)


@router.get(
    "/healthz",
    summary="Liveness check",
    description="Simple liveness check with no external dependencies (for Docker healthcheck)",
    status_code=status.HTTP_200_OK,
    response_model=dict
)
async def liveness_check():
    """
    Liveness check - returns immediately with no external calls.

    This endpoint is designed for Docker healthcheck and load balancers.
    It only verifies the API process is running and responsive.
    """
    return {"status": "alive"}


@router.get(
    "/readyz",
    summary="Readiness check",
    description="Readiness check with bounded timeout to external dependencies",
    status_code=status.HTTP_200_OK
)
async def readiness_check(
    client: ComfyUIClient = Depends(get_comfyui_client)
):
    """
    Readiness check - verifies service can handle requests.

    Performs bounded checks (~250ms max) to external dependencies.
    Returns 503 if not ready to handle traffic.
    """
    comfyui_ready = False

    try:
        # Bounded timeout for ComfyUI check (250ms)
        async with client:
            comfyui_ready = await asyncio.wait_for(
                client.health_check(),
                timeout=0.25
            )
    except asyncio.TimeoutError:
        logger.warning("ComfyUI readiness check timed out (>250ms)")
    except Exception as e:
        logger.warning(f"ComfyUI readiness check failed: {e}")

    if comfyui_ready:
        return {
            "status": "ready",
            "comfyui": "connected"
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "comfyui": "disconnected"
            }
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Check the health status of the API service and ComfyUI backend",
    status_code=status.HTTP_200_OK
)
async def health_check(
    client: ComfyUIClient = Depends(get_comfyui_client)
) -> HealthResponse:
    """
    Check service health.

    Returns the health status of both the API service and the ComfyUI backend.

    **Returns:**
    - **status**: Overall service status ("healthy" or "degraded")
    - **api_version**: Current API version
    - **comfyui_status**: ComfyUI connection status ("connected" or "disconnected")
    - **comfyui_url**: ComfyUI service URL
    - **timestamp**: Current server time
    """
    comfyui_status = "disconnected"

    try:
        async with client:
            is_healthy = await client.health_check()
            comfyui_status = "connected" if is_healthy else "disconnected"
    except Exception as e:
        logger.error(f"Health check error: {e}")
        comfyui_status = "error"

    overall_status = "healthy" if comfyui_status == "connected" else "degraded"

    return HealthResponse(
        status=overall_status,
        api_version="1.0.0",
        comfyui_status=comfyui_status,
        comfyui_url=client.base_url,
        timestamp=datetime.utcnow()
    )


@router.get(
    "/models",
    response_model=ModelsListResponse,
    summary="List available models",
    description="Get a list of all available models in ComfyUI",
    status_code=status.HTTP_200_OK
)
async def list_models(
    client: ComfyUIClient = Depends(get_comfyui_client)
) -> ModelsListResponse:
    """
    List available models.

    Retrieves a list of all models available in the ComfyUI instance.
    This includes checkpoint models that can be used for image generation.

    **Returns:**
    - **models**: List of available models with metadata
    - **total**: Total number of models found
    """
    try:
        async with client:
            model_names = await client.get_models()

            models = [
                ModelInfo(
                    name=name,
                    path=name,  # ComfyUI uses relative paths
                    type="checkpoint"
                )
                for name in model_names
            ]

            return ModelsListResponse(
                models=models,
                total=len(models)
            )

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        # Return empty list on error
        return ModelsListResponse(
            models=[],
            total=0
        )


@router.get(
    "/",
    summary="Root endpoint",
    description="Simple health check endpoint",
    status_code=status.HTTP_200_OK
)
async def root():
    """
    Root endpoint.

    Returns a simple status message indicating the API is running.
    """
    return {
        "service": "ComfyUI API Service",
        "status": "online",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }
