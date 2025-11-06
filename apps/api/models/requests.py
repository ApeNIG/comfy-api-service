"""Request models for API endpoints."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class SamplerType(str, Enum):
    """Available sampler types in ComfyUI."""
    EULER = "euler"
    EULER_A = "euler_a"
    HEUN = "heun"
    DPM_2 = "dpm_2"
    DPM_2_A = "dpm_2_a"
    DPM_PLUS_PLUS_2S_A = "dpm_plus_plus_2s_a"
    DPM_PLUS_PLUS_2M = "dpm_plus_plus_2m"
    DPM_PLUS_PLUS_SDE = "dpm_plus_plus_sde"
    DPM_FAST = "dpm_fast"
    DPM_ADAPTIVE = "dpm_adaptive"
    LMS = "lms"
    DDIM = "ddim"
    UNI_PC = "uni_pc"


class GenerateImageRequest(BaseModel):
    """Request model for image generation."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text prompt describing the image to generate",
        examples=["A beautiful sunset over mountains, high quality, detailed"]
    )

    negative_prompt: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Negative prompt to avoid certain features",
        examples=["blurry, low quality, distorted"]
    )

    width: int = Field(
        default=512,
        ge=64,
        le=2048,
        description="Image width in pixels (must be divisible by 8)",
        examples=[512, 1024]
    )

    height: int = Field(
        default=512,
        ge=64,
        le=2048,
        description="Image height in pixels (must be divisible by 8)",
        examples=[512, 1024]
    )

    steps: int = Field(
        default=20,
        ge=1,
        le=150,
        description="Number of sampling steps (more steps = better quality but slower)",
        examples=[20, 30, 50]
    )

    cfg_scale: float = Field(
        default=7.0,
        ge=1.0,
        le=30.0,
        description="Classifier-free guidance scale (how closely to follow the prompt)",
        examples=[7.0, 8.5, 12.0]
    )

    sampler: SamplerType = Field(
        default=SamplerType.EULER_A,
        description="Sampling algorithm to use",
        examples=["euler_a", "dpm_plus_plus_2m"]
    )

    seed: Optional[int] = Field(
        default=None,
        ge=-1,
        description="Random seed for reproducibility (-1 for random)",
        examples=[42, 12345, -1]
    )

    model: str = Field(
        default="sd_xl_base_1.0.safetensors",
        description="Model checkpoint to use",
        examples=["sd_xl_base_1.0.safetensors", "v1-5-pruned-emaonly.safetensors"]
    )

    batch_size: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate in one batch",
        examples=[1, 2, 4]
    )

    @field_validator("width", "height")
    @classmethod
    def validate_dimensions(cls, v: int) -> int:
        """Ensure dimensions are divisible by 8 (required by Stable Diffusion)."""
        if v % 8 != 0:
            raise ValueError(f"Dimension must be divisible by 8, got {v}")
        return v

    @field_validator("prompt", "negative_prompt")
    @classmethod
    def validate_prompt(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize prompts."""
        if v is None:
            return v
        # Strip whitespace
        v = v.strip()
        if len(v) == 0:
            return None
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prompt": "A majestic lion in the savanna, golden hour lighting, photorealistic",
                    "negative_prompt": "blurry, low quality, cartoon",
                    "width": 1024,
                    "height": 1024,
                    "steps": 30,
                    "cfg_scale": 7.5,
                    "sampler": "euler_a",
                    "seed": -1,
                    "model": "sd_xl_base_1.0.safetensors",
                    "batch_size": 1
                }
            ]
        }
    }


class BatchGenerateRequest(BaseModel):
    """Request model for batch image generation with multiple prompts."""

    requests: list[GenerateImageRequest] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of generation requests to process"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "requests": [
                        {
                            "prompt": "A cat sitting on a windowsill",
                            "width": 512,
                            "height": 512
                        },
                        {
                            "prompt": "A dog playing in a park",
                            "width": 512,
                            "height": 512
                        }
                    ]
                }
            ]
        }
    }
