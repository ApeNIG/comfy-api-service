#!/usr/bin/env python3
"""
Professional AI Asset Generator for Creator Platform
===================================================

Generates high-quality AI assets using ComfyUI with designer-quality prompts.
"""

import asyncio
import httpx
import json
from pathlib import Path
from urllib.parse import quote


# ComfyUI endpoint (RunPod)
COMFYUI_URL = "https://jfmkqw45px5o3x-8188.proxy.runpod.net"


async def generate_image(prompt, negative_prompt, width, height, filename, seed=42):
    """Generate image using ComfyUI API with designer-quality settings."""

    print(f"\n🎨 Generating: {filename}")
    print(f"   Size: {width}x{height}")
    print(f"   Prompt: {prompt[:80]}...")

    # Build workflow with optimized settings
    workflow = {
        "3": {
            "inputs": {
                "seed": seed,
                "steps": 35,  # More steps for quality
                "cfg": 8.0,   # Higher CFG for prompt adherence
                "sampler_name": "dpmpp_2m",  # High quality sampler
                "scheduler": "karras",       # Better noise schedule
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            },
            "class_type": "KSampler"
        },
        "4": {
            "inputs": {
                "ckpt_name": "v1-5-pruned-emaonly.ckpt"
            },
            "class_type": "CheckpointLoaderSimple"
        },
        "5": {
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            },
            "class_type": "EmptyLatentImage"
        },
        "6": {
            "inputs": {
                "text": prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "7": {
            "inputs": {
                "text": negative_prompt,
                "clip": ["4", 1]
            },
            "class_type": "CLIPTextEncode"
        },
        "8": {
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            },
            "class_type": "VAEDecode"
        },
        "9": {
            "inputs": {
                "filename_prefix": "creator_pro",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit prompt
        response = await client.post(
            f"{COMFYUI_URL}/prompt",
            json={"prompt": workflow, "client_id": "creator_designer"}
        )

        if response.status_code != 200:
            print(f"   ❌ Error: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

        result = response.json()
        prompt_id = result.get("prompt_id")

        if not prompt_id:
            print("   ❌ No prompt_id received")
            return None

        print(f"   ⏳ Job ID: {prompt_id}")
        print(f"   ⏳ Waiting for generation...")

        # Poll for completion
        for i in range(120):  # Wait up to 2 minutes
            await asyncio.sleep(1)

            if i % 5 == 0:  # Progress update every 5 seconds
                print(f"   ⏳ Still working... ({i}s)")

            history_response = await client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            history_data = history_response.json()

            if prompt_id in history_data:
                history = history_data[prompt_id]
                status = history.get("status", {})

                if status.get("completed"):
                    # Get image URL
                    outputs = history.get("outputs", {})
                    for node_id, output in outputs.items():
                        if "images" in output and len(output["images"]) > 0:
                            image_info = output["images"][0]
                            image_filename = image_info["filename"]
                            subfolder = image_info.get("subfolder", "")

                            # Download image
                            url = f"{COMFYUI_URL}/view?filename={quote(image_filename)}&type=output"
                            if subfolder:
                                url += f"&subfolder={quote(subfolder)}"

                            img_response = await client.get(url)
                            output_path = Path("assets") / filename
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_bytes(img_response.content)

                            file_size = len(img_response.content) / 1024  # KB
                            print(f"   ✅ Saved: {output_path} ({file_size:.1f} KB)")
                            return str(output_path)

        print("   ⏰ Timeout - generation took too long")
        return None


async def main():
    """Generate all professional assets."""
    print("=" * 70)
    print("🎨 Creator Professional Asset Generator")
    print("   Designer-quality AI assets with ComfyUI")
    print("=" * 70)

    # Professional asset specifications
    assets = [
        {
            "filename": "hero-ai-pro.png",
            "prompt": "isometric 3D illustration of AI workflow automation, floating holographic interface panels showing image transformation, glowing blue and purple neon lights, modern tech aesthetic, clean composition, professional digital art, octane render, trending on artstation, 8k uhd, crisp details",
            "negative_prompt": "text, words, letters, watermark, signature, username, blurry, low quality, jpeg artifacts, distorted, ugly, messy, cluttered, realistic photo, amateur, low resolution, bad anatomy",
            "width": 1024,
            "height": 576,
            "seed": 12345
        },
        {
            "filename": "feature-drive-pro.png",
            "prompt": "3D render of cloud storage icon, elegant folder with document symbols floating around it, soft blue and purple gradient background, modern minimalist design, studio lighting, clean composition, isometric view, white backdrop, professional product photography style, octane render",
            "negative_prompt": "text, logo, watermark, signature, blurry, low quality, messy, cluttered, realistic, photograph, complex background, dark, shadows",
            "width": 512,
            "height": 512,
            "seed": 23456
        },
        {
            "filename": "feature-upload-pro.png",
            "prompt": "3D render of image upload concept, photo frame with upward arrow, floating photograph elements, soft blue and purple gradient glow, modern minimalist design, studio lighting, clean composition, isometric view, white backdrop, professional product photography style, octane render",
            "negative_prompt": "text, logo, watermark, signature, blurry, low quality, messy, cluttered, realistic, photograph, complex background, dark, shadows",
            "width": 512,
            "height": 512,
            "seed": 34567
        },
        {
            "filename": "feature-magic-pro.png",
            "prompt": "3D render of magic wand with sparkles and stars, automated workflow visualization with checkmark symbol, soft blue and purple gradient glow, modern minimalist design, studio lighting, clean composition, isometric view, white backdrop, professional product photography style, octane render",
            "negative_prompt": "text, logo, watermark, signature, blurry, low quality, messy, cluttered, realistic, photograph, complex background, dark, shadows",
            "width": 512,
            "height": 512,
            "seed": 45678
        },
        {
            "filename": "dashboard-stat-jobs.png",
            "prompt": "3D icon design, elegant clock symbol with circular arrows showing time management, blue and purple gradient, modern minimalist style, glass morphism effect, centered composition, white background, professional icon design, octane render",
            "negative_prompt": "text, numbers, watermark, signature, blurry, low quality, messy, realistic photo, complex",
            "width": 256,
            "height": 256,
            "seed": 56789
        },
        {
            "filename": "dashboard-stat-trial.png",
            "prompt": "3D icon design, elegant calendar symbol with highlighted date, blue and purple gradient, modern minimalist style, glass morphism effect, centered composition, white background, professional icon design, octane render",
            "negative_prompt": "text, numbers, watermark, signature, blurry, low quality, messy, realistic photo, complex",
            "width": 256,
            "height": 256,
            "seed": 67890
        },
        {
            "filename": "dashboard-stat-total.png",
            "prompt": "3D icon design, elegant bar chart with ascending trend line, blue and purple gradient, modern minimalist style, glass morphism effect, centered composition, white background, professional icon design, octane render",
            "negative_prompt": "text, numbers, watermark, signature, blurry, low quality, messy, realistic photo, complex",
            "width": 256,
            "height": 256,
            "seed": 78901
        }
    ]

    print(f"\n📊 Generating {len(assets)} professional AI assets")
    print(f"🔗 Using ComfyUI at: {COMFYUI_URL}")
    print()

    successful = 0
    failed = 0

    for i, asset in enumerate(assets, 1):
        print(f"\n[{i}/{len(assets)}] {'-' * 60}")
        result = await generate_image(
            prompt=asset["prompt"],
            negative_prompt=asset["negative_prompt"],
            width=asset["width"],
            height=asset["height"],
            filename=asset["filename"],
            seed=asset.get("seed", 42)
        )

        if result:
            successful += 1
        else:
            failed += 1

    print("\n" + "=" * 70)
    print(f"✅ Generation Complete!")
    print(f"   Successful: {successful}/{len(assets)}")
    print(f"   Failed: {failed}/{len(assets)}")
    print(f"   Output: assets/ directory")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
