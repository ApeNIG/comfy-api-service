#!/usr/bin/env python3
"""Simple asset generator using ComfyUI API directly."""

import asyncio
import httpx
import json
from pathlib import Path


async def generate_image(prompt, negative_prompt, width, height, filename):
    """Generate image using ComfyUI API."""

    # Build workflow
    workflow = {
        "3": {
            "inputs": {
                "seed": 42,
                "steps": 30,
                "cfg": 7.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
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
                "filename_prefix": "creator_asset",
                "images": ["8", 0]
            },
            "class_type": "SaveImage"
        }
    }

    base_url = "http://localhost:8188"

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Submit prompt
        print(f"  Generating: {filename}")
        print(f"  Prompt: {prompt[:60]}...")

        response = await client.post(
            f"{base_url}/prompt",
            json={"prompt": workflow, "client_id": "creator_script"}
        )

        if response.status_code != 200:
            print(f"  ❌ Error: {response.status_code}")
            return None

        result = response.json()
        prompt_id = result.get("prompt_id")

        if not prompt_id:
            print("  ❌ No prompt_id received")
            return None

        print(f"  ⏳ Waiting for completion (ID: {prompt_id})...")

        # Poll for completion
        for _ in range(60):  # Wait up to 60 seconds
            await asyncio.sleep(1)

            history_response = await client.get(f"{base_url}/history/{prompt_id}")
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
                            from urllib.parse import quote
                            url = f"{base_url}/view?filename={quote(image_filename)}&type=output"
                            if subfolder:
                                url += f"&subfolder={quote(subfolder)}"

                            img_response = await client.get(url)
                            output_path = Path("assets") / filename
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            output_path.write_bytes(img_response.content)

                            print(f"  ✅ Saved: {output_path}")
                            return str(output_path)

        print("  ⏰ Timeout waiting for completion")
        return None


async def main():
    """Generate all assets."""
    print("=" * 60)
    print("Creator Asset Generator (AI-powered)")
    print("=" * 60)

    assets = [
        {
            "filename": "hero-ai.png",
            "prompt": "futuristic AI workspace with holographic screens, floating data visualizations, blue and purple gradient lighting, modern minimal design, professional digital art, 8k uhd, clean composition",
            "negative_prompt": "text, watermark, signature, blurry, low quality, messy, cluttered, realistic photo",
            "width": 1024,
            "height": 576
        },
        {
            "filename": "step-drive-ai.png",
            "prompt": "3D icon of cloud storage with folders, Google Drive concept, blue and purple gradient, modern minimal illustration, clean design, centered composition, white background",
            "negative_prompt": "text, watermark, signature, blurry, low quality, realistic, complex, cluttered",
            "width": 512,
            "height": 512
        },
        {
            "filename": "step-upload-ai.png",
            "prompt": "3D icon of image upload, photo gallery with arrow, blue and purple gradient, modern minimal illustration, clean design, centered composition, white background",
            "negative_prompt": "text, watermark, signature, blurry, low quality, realistic, complex, cluttered",
            "width": 512,
            "height": 512
        },
        {
            "filename": "step-magic-ai.png",
            "prompt": "3D icon of magic wand with sparkles and checkmark, automation concept, blue and purple gradient, modern minimal illustration, clean design, centered composition, white background",
            "negative_prompt": "text, watermark, signature, blurry, low quality, realistic, complex, cluttered",
            "width": 512,
            "height": 512
        }
    ]

    print(f"\n🎨 Generating {len(assets)} AI assets...")

    for i, asset in enumerate(assets, 1):
        print(f"\n[{i}/{len(assets)}]")
        await generate_image(
            prompt=asset["prompt"],
            negative_prompt=asset["negative_prompt"],
            width=asset["width"],
            height=asset["height"],
            filename=asset["filename"]
        )

    print("\n" + "=" * 60)
    print("✅ Asset generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
