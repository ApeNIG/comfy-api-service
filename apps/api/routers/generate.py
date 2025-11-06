"""Image generation endpoints."""

import logging
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from ..models.requests import GenerateImageRequest, BatchGenerateRequest
from ..models.responses import ImageResponse, BatchImageResponse, ErrorResponse
from ..services.comfyui_client import (
    ComfyUIClient,
    get_comfyui_client,
    ComfyUIConnectionError,
    ComfyUITimeoutError,
    ComfyUIClientError
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/generate",
    tags=["Image Generation"],
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "ComfyUI service unavailable"}
    }
)


@router.post(
    "/",
    response_model=ImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a single image",
    description="Generate an image using ComfyUI with the provided parameters. "
                "This is a synchronous operation that waits for the image to be generated.",
    responses={
        201: {
            "description": "Image generated successfully",
            "model": ImageResponse
        },
        400: {
            "description": "Invalid request parameters",
            "model": ErrorResponse
        },
        503: {
            "description": "ComfyUI service is unavailable"
        }
    }
)
async def generate_image(
    request: GenerateImageRequest,
    client: ComfyUIClient = Depends(get_comfyui_client)
) -> ImageResponse:
    """
    Generate a single image.

    This endpoint accepts a prompt and generation parameters, submits the request
    to ComfyUI, waits for completion, and returns the result.

    **Parameters:**
    - **prompt**: Text description of the image to generate (required)
    - **negative_prompt**: Features to avoid in the image (optional)
    - **width**: Image width in pixels, must be divisible by 8 (default: 512)
    - **height**: Image height in pixels, must be divisible by 8 (default: 512)
    - **steps**: Number of sampling steps (default: 20, range: 1-150)
    - **cfg_scale**: Guidance scale (default: 7.0, range: 1.0-30.0)
    - **sampler**: Sampling algorithm (default: "euler_a")
    - **seed**: Random seed for reproducibility, -1 for random (optional)
    - **model**: Model checkpoint to use (default: "sd_xl_base_1.0.safetensors")
    - **batch_size**: Number of images to generate (default: 1, max: 4)

    **Returns:**
    - **job_id**: Unique identifier for this generation
    - **status**: "completed" or "failed"
    - **image_url**: URL to download the generated image
    - **metadata**: Generation parameters and timing information
    """
    try:
        logger.info(f"Generating image with prompt: {request.prompt[:100]}...")

        async with client:
            # Check if ComfyUI is available
            is_healthy = await client.health_check()
            if not is_healthy:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="ComfyUI service is not available"
                )

            # Generate image
            response = await client.generate_image(request)

            if response.status == "failed":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Image generation failed: {response.error}"
                )

            return response

    except ComfyUIConnectionError as e:
        logger.error(f"Connection error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot connect to ComfyUI service: {str(e)}"
        )

    except ComfyUITimeoutError as e:
        logger.error(f"Timeout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Image generation timed out: {str(e)}"
        )

    except ComfyUIClientError as e:
        logger.error(f"Client error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error communicating with ComfyUI: {str(e)}"
        )

    except Exception as e:
        logger.exception(f"Unexpected error during image generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=BatchImageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate multiple images",
    description="Generate multiple images in a batch. Each request is processed sequentially.",
    responses={
        201: {
            "description": "Batch generation initiated",
            "model": BatchImageResponse
        },
        400: {
            "description": "Invalid request parameters"
        }
    }
)
async def generate_batch(
    batch_request: BatchGenerateRequest,
    client: ComfyUIClient = Depends(get_comfyui_client)
) -> BatchImageResponse:
    """
    Generate multiple images in a batch.

    This endpoint processes multiple generation requests sequentially.
    Each request is independent and failures in one request don't affect others.

    **Note:** This is a synchronous operation that waits for all images to be generated.
    For large batches, consider using individual requests instead.

    **Parameters:**
    - **requests**: List of generation requests (max 10)

    **Returns:**
    - **batch_id**: Unique identifier for this batch
    - **jobs**: List of individual job responses
    - **total**: Total number of jobs
    - **completed**: Number of successfully completed jobs
    - **failed**: Number of failed jobs
    """
    import uuid

    batch_id = str(uuid.uuid4())
    jobs: List[ImageResponse] = []
    completed_count = 0
    failed_count = 0

    logger.info(f"Processing batch {batch_id} with {len(batch_request.requests)} requests")

    async with client:
        # Check if ComfyUI is available
        is_healthy = await client.health_check()
        if not is_healthy:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ComfyUI service is not available"
            )

        # Process each request
        for idx, request in enumerate(batch_request.requests, 1):
            logger.info(f"Processing batch item {idx}/{len(batch_request.requests)}")

            try:
                response = await client.generate_image(request)
                jobs.append(response)

                if response.status == "completed":
                    completed_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error processing batch item {idx}: {e}")
                # Create a failed response for this item
                failed_response = ImageResponse(
                    job_id=f"batch_{batch_id}_item_{idx}",
                    status="failed",
                    error=str(e)
                )
                jobs.append(failed_response)
                failed_count += 1

    return BatchImageResponse(
        batch_id=batch_id,
        jobs=jobs,
        total=len(batch_request.requests),
        completed=completed_count,
        failed=failed_count
    )
