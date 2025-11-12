"""
Generate hero images for Creator platform using ComfyUI

This script generates beautiful background assets for the Creator platform
using the existing ComfyUI integration.

Usage:
    python scripts/generate_hero_images.py --count 5 --theme dark-coral

Prerequisites:
    - ComfyUI server running on http://localhost:8188
    - SDXL or SD1.5 model loaded in ComfyUI
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.shared.services.comfyui.client import get_comfyui_client, ComfyUIStatus


# Simple text-to-image workflow for SDXL
# This is a basic workflow - you'll need to export your actual workflow from ComfyUI
HERO_IMAGE_WORKFLOW = {
    "3": {
        "inputs": {
            "seed": 42,
            "steps": 25,
            "cfg": 7.5,
            "sampler_name": "dpmpp_2m",
            "scheduler": "karras",
            "denoise": 1,
            "model": ["4", 0],
            "positive": ["6", 0],
            "negative": ["7", 0],
            "latent_image": ["5", 0]
        },
        "class_type": "KSampler",
        "_meta": {
            "title": "KSampler"
        }
    },
    "4": {
        "inputs": {
            "ckpt_name": "v1-5-pruned-emaonly.ckpt"
        },
        "class_type": "CheckpointLoaderSimple",
        "_meta": {
            "title": "Load Checkpoint"
        }
    },
    "5": {
        "inputs": {
            "width": 1920,
            "height": 1080,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage",
        "_meta": {
            "title": "Empty Latent Image"
        }
    },
    "6": {
        "inputs": {
            "text": "REPLACE_WITH_PROMPT",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
            "title": "CLIP Text Encode (Prompt)"
        }
    },
    "7": {
        "inputs": {
            "text": "text, watermark, signature, blurry, low quality, worst quality",
            "clip": ["4", 1]
        },
        "class_type": "CLIPTextEncode",
        "_meta": {
            "title": "CLIP Text Encode (Prompt)"
        }
    },
    "8": {
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        },
        "class_type": "VAEDecode",
        "_meta": {
            "title": "VAE Decode"
        }
    },
    "9": {
        "inputs": {
            "filename_prefix": "creator_hero",
            "images": ["8", 0]
        },
        "class_type": "SaveImage",
        "_meta": {
            "title": "Save Image"
        }
    }
}


# Professional hero background prompts - Formula-based approach
# Based on proven SaaS design patterns (Stripe, Vercel, Linear)
HERO_PROMPTS = [
    # === BASE HERO BACKGROUNDS (Coral/Salmon theme) ===

    # Base Hero - Coral theme, subtle
    "Clean dark gradient background with subtle ambient light falloff, soft vignette edges, "
    "minimal glowing particles in coral and salmon tones, modern UI aesthetic, "
    "cinematic SaaS hero background, professional landing page lighting, 3D sense of depth, "
    "no objects, no clutter, matte finish, ultra high resolution, out of focus depth of field",

    # Base Hero - Coral theme, moderate
    "Clean dark gradient background with moderate ambient light falloff, soft vignette edges, "
    "moderate glowing particles in coral #FF6E6B and salmon #FF8E53 tones, modern UI aesthetic, "
    "cinematic SaaS hero background, professional landing page lighting, volumetric depth, "
    "no objects, no clutter, matte finish, ultra high resolution, depth of field blur",

    # Base Hero - Coral theme, strong
    "Clean dark gradient background with strong ambient light falloff, soft vignette edges, "
    "prominent glowing particles in coral and salmon gradient, modern UI aesthetic, "
    "cinematic SaaS hero background, professional landing page lighting, deep 3D sense of depth, "
    "no objects, no clutter, semi-gloss finish, ultra high resolution, shallow depth of field",

    # === MINIMAL GEOMETRIC BACKGROUNDS ===

    # Geometric - Matte finish
    "Modern minimal geometric gradient background with subtle depth, soft 3D polygons or glass layers, "
    "faint reflections in coral and salmon hues, muted contrast, dark tech aesthetic, "
    "product UI environment, volumetric light haze, abstract but controlled composition, "
    "clean and professional, no sharp edges, matte surface, out of focus",

    # Geometric - Glossy finish
    "Modern minimal geometric gradient background with moderate depth, soft glass layers, "
    "subtle reflections in coral #FF6E6B tones, controlled contrast, dark tech aesthetic, "
    "product UI environment, volumetric light haze, abstract composition, "
    "clean and professional, no sharp edges, glossy finish, depth blur",

    # Geometric - Glass-like
    "Modern minimal geometric gradient background with deep depth, translucent glass layers, "
    "prominent reflections in coral and salmon gradient, soft contrast, dark tech aesthetic, "
    "product UI environment, volumetric light haze, abstract controlled composition, "
    "clean and professional, no sharp edges, glass-like finish, depth of field",

    # === DEPTH LIGHTING / COSMIC BLUR ===

    # Cosmic - Cyan/Magenta mix
    "High-end dark SaaS background with soft lighting gradients, cyan and magenta glow blending, "
    "smooth volumetric haze, subtle energy field texture, minimal contrast, "
    "futuristic lighting ambiance, cinematic lighting on dark surface, no visible shapes or objects, "
    "out of focus, depth of field blur, ultra high resolution",

    # Cosmic - Coral/Purple mix
    "High-end dark SaaS background with soft lighting gradients, coral #FF6E6B and purple glow blending, "
    "smooth volumetric haze, subtle energy field texture, minimal contrast, "
    "futuristic lighting ambiance, cinematic lighting on dark surface, no visible shapes or objects, "
    "depth of field blur, shallow focus, ultra high resolution",

    # Cosmic - Full coral theme
    "High-end dark SaaS background with soft lighting gradients, coral #FF6E6B and salmon #FF8E53 glow blending, "
    "smooth volumetric haze, subtle energy field texture, minimal contrast, "
    "futuristic lighting ambiance, cinematic lighting on dark surface, no visible shapes or objects, "
    "out of focus background, depth of field, ultra high resolution"
]


async def generate_hero_image(client, prompt: str, seed: int = None) -> tuple[str, list[bytes]]:
    """
    Generate a single hero image.

    Args:
        client: ComfyUI client instance
        prompt: Text prompt for generation
        seed: Random seed (None for random)

    Returns:
        Tuple of (prompt_id, list of image bytes)
    """
    # Copy workflow and set prompt
    workflow = HERO_IMAGE_WORKFLOW.copy()

    # Update prompt
    workflow["6"]["inputs"]["text"] = prompt

    # Set seed if provided
    if seed is not None:
        workflow["3"]["inputs"]["seed"] = seed

    print(f"\n🎨 Generating image...")
    print(f"Prompt: {prompt[:100]}...")

    # Execute workflow
    result = await client.execute_workflow(
        workflow,
        wait_for_completion=True,
        progress_callback=lambda update: print(f"  Progress: {update.get('value', 0)}/{update.get('max', 100)}")
    )

    if result.status == ComfyUIStatus.COMPLETED:
        print(f"✅ Generation complete! Prompt ID: {result.prompt_id}")

        # Download images
        images = await client.get_output_images(result.prompt_id)
        print(f"📥 Downloaded {len(images)} image(s)")

        return result.prompt_id, images
    else:
        print(f"❌ Generation failed: {result.error}")
        return result.prompt_id, []


async def save_images(images: list[bytes], prompt_id: str, output_dir: Path):
    """Save generated images to disk."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, img_data in enumerate(images):
        output_path = output_dir / f"{prompt_id}_{i}.png"
        output_path.write_bytes(img_data)
        print(f"💾 Saved: {output_path}")


async def main():
    """Main execution."""
    print("=" * 60)
    print("🚀 Creator Hero Image Generator")
    print("=" * 60)

    # Initialize client
    client = get_comfyui_client()

    # Check if ComfyUI is running
    print("\n🔍 Checking ComfyUI server...")
    is_healthy = await client.health_check()

    if not is_healthy:
        print("❌ ComfyUI server is not running!")
        print("\nPlease start ComfyUI server first:")
        print("  cd /path/to/ComfyUI")
        print("  python main.py")
        print("\nOr use the RunPod deployment if available.")
        return

    print("✅ ComfyUI server is running")

    # Create output directory
    output_dir = Path("assets/generated/heroes")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {output_dir.absolute()}")

    # Generate images
    print(f"\n🎨 Generating {len(HERO_PROMPTS)} professional hero backgrounds...")

    for i, prompt in enumerate(HERO_PROMPTS, 1):
        print(f"\n{'='*60}")
        print(f"Image {i}/{len(HERO_PROMPTS)}")
        print(f"{'='*60}")

        try:
            prompt_id, images = await generate_hero_image(
                client,
                prompt,
                seed=1000 + i  # Deterministic seeds for reproducibility
            )

            if images:
                await save_images(images, prompt_id, output_dir)

            # Small delay between generations
            if i < len(HERO_PROMPTS):
                await asyncio.sleep(2)

        except Exception as e:
            print(f"❌ Error generating image: {e}")
            continue

    print("\n" + "="*60)
    print("✅ Generation complete!")
    print(f"📂 Images saved to: {output_dir.absolute()}")
    print("="*60)

    print("\n📋 Next steps:")
    print("1. Review generated images in assets/generated/heroes/")
    print("2. Pick your favorites")
    print("3. Update HTML templates to use the new backgrounds")
    print("4. Consider A/B testing different variations")
    print("\nExample usage in HTML:")
    print('  <div style="background-image: url(\'/assets/generated/heroes/[prompt_id]_0.png\');">')


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
