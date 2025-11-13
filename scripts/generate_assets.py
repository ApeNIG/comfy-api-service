#!/usr/bin/env python3
"""
Asset Generation Script for Creator Platform
=============================================

Generates placeholder assets for the web UI using ComfyUI API.

Assets to generate:
- Landing page hero image
- Onboarding step illustrations (3x)
- Dashboard stat card icons
- User avatar placeholders

Usage:
    python scripts/generate_assets.py

Requirements:
    - ComfyUI service running on localhost:8188
    - Workflows available in workflows/ directory
"""

import asyncio
import sys
import os
import httpx
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.api.services.comfyui_client import ComfyUIClient
from apps.api.models.requests import GenerateImageRequest, Sampler


class AssetGenerator:
    """Generate UI assets using ComfyUI."""

    def __init__(self, output_dir: str = "assets/generated"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "http://localhost:8188"

    async def check_comfyui_health(self) -> bool:
        """Check if ComfyUI is running."""
        print("🔍 Checking ComfyUI service...")
        client = ComfyUIClient(base_url=self.base_url)
        is_healthy = await client.health_check()

        if is_healthy:
            print("✅ ComfyUI service is running")
        else:
            print("❌ ComfyUI service is not available")
            print(f"   Please start ComfyUI on {self.base_url}")

        return is_healthy

    async def generate_hero_image(self):
        """Generate hero image for landing page."""
        print("\n🎨 Generating landing page hero image...")

        request = GenerateImageRequest(
            prompt="futuristic AI workspace, floating holographic screens, blue and purple gradient lighting, modern minimal design, professional photography, 8k uhd, sharp focus",
            negative_prompt="text, watermark, signature, blurry, low quality, distorted",
            width=1024,
            height=576,  # 16:9 aspect ratio
            steps=30,
            cfg_scale=7.5,
            sampler=Sampler.EULER_ANCESTRAL,
            model="v1-5-pruned-emaonly.ckpt"
        )

        async with ComfyUIClient(base_url=self.base_url) as client:
            response = await client.generate_image(request)

            if response.image_url:
                await self._download_image(
                    response.image_url,
                    self.output_dir / "hero-landing.png"
                )
                print(f"✅ Hero image saved to {self.output_dir / 'hero-landing.png'}")
            else:
                print(f"❌ Failed to generate hero image: {response.error}")

    async def generate_step_illustrations(self):
        """Generate illustrations for onboarding steps."""
        print("\n🎨 Generating onboarding step illustrations...")

        prompts = [
            {
                "name": "step-1-drive",
                "prompt": "Google Drive cloud icon, colorful folder, floating documents, blue and purple gradient, modern minimal 3D illustration, clean design",
                "description": "Connect Google Drive"
            },
            {
                "name": "step-2-upload",
                "prompt": "Upload icon with image files, photo gallery, drag and drop interface, blue and purple gradient, modern minimal 3D illustration, clean design",
                "description": "Upload First Image"
            },
            {
                "name": "step-3-results",
                "prompt": "Checkmark icon with sparkles, automated workflow, magic wand effect, blue and purple gradient, modern minimal 3D illustration, clean design",
                "description": "Get Results Automatically"
            }
        ]

        async with ComfyUIClient(base_url=self.base_url) as client:
            for i, config in enumerate(prompts, 1):
                print(f"  Generating {i}/3: {config['description']}...")

                request = GenerateImageRequest(
                    prompt=config["prompt"],
                    negative_prompt="text, watermark, signature, blurry, low quality, realistic photo, cluttered, complex",
                    width=512,
                    height=512,
                    steps=25,
                    cfg_scale=7.0,
                    sampler=Sampler.EULER_ANCESTRAL,
                    model="v1-5-pruned-emaonly.ckpt"
                )

                response = await client.generate_image(request)

                if response.image_url:
                    await self._download_image(
                        response.image_url,
                        self.output_dir / f"{config['name']}.png"
                    )
                    print(f"  ✅ Saved {config['name']}.png")
                else:
                    print(f"  ❌ Failed: {response.error}")

    async def generate_dashboard_graphics(self):
        """Generate graphics for dashboard."""
        print("\n🎨 Generating dashboard graphics...")

        prompts = [
            {
                "name": "stat-jobs",
                "prompt": "Clock icon, timer, hourglass, time management, blue and purple gradient, modern minimal 3D icon, clean design, centered composition",
                "description": "Jobs Remaining Icon"
            },
            {
                "name": "stat-trial",
                "prompt": "Calendar icon, date picker, schedule, blue and purple gradient, modern minimal 3D icon, clean design, centered composition",
                "description": "Trial Days Icon"
            },
            {
                "name": "stat-total",
                "prompt": "Activity graph, statistics chart, analytics, blue and purple gradient, modern minimal 3D icon, clean design, centered composition",
                "description": "Total Jobs Icon"
            }
        ]

        async with ComfyUIClient(base_url=self.base_url) as client:
            for i, config in enumerate(prompts, 1):
                print(f"  Generating {i}/3: {config['description']}...")

                request = GenerateImageRequest(
                    prompt=config["prompt"],
                    negative_prompt="text, watermark, signature, blurry, low quality, realistic photo, cluttered, busy background",
                    width=256,
                    height=256,
                    steps=20,
                    cfg_scale=7.0,
                    sampler=Sampler.EULER_ANCESTRAL,
                    model="v1-5-pruned-emaonly.ckpt"
                )

                response = await client.generate_image(request)

                if response.image_url:
                    await self._download_image(
                        response.image_url,
                        self.output_dir / f"{config['name']}.png"
                    )
                    print(f"  ✅ Saved {config['name']}.png")
                else:
                    print(f"  ❌ Failed: {response.error}")

    async def generate_default_avatar(self):
        """Generate default user avatar."""
        print("\n🎨 Generating default user avatar...")

        request = GenerateImageRequest(
            prompt="user profile avatar, abstract geometric shape, blue and purple gradient, modern minimal design, circular composition, centered",
            negative_prompt="face, person, human, realistic, text, watermark, signature",
            width=256,
            height=256,
            steps=20,
            cfg_scale=7.0,
            sampler=Sampler.EULER_ANCESTRAL,
            model="v1-5-pruned-emaonly.ckpt"
        )

        async with ComfyUIClient(base_url=self.base_url) as client:
            response = await client.generate_image(request)

            if response.image_url:
                await self._download_image(
                    response.image_url,
                    self.output_dir / "default-avatar.png"
                )
                print(f"✅ Avatar saved to {self.output_dir / 'default-avatar.png'}")
            else:
                print(f"❌ Failed to generate avatar: {response.error}")

    async def _download_image(self, url: str, output_path: Path):
        """Download image from URL to local file."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()

            output_path.write_bytes(response.content)

    def create_svg_placeholders(self):
        """Create SVG placeholders as fallback when ComfyUI is not available."""
        print("\n📐 Creating SVG placeholders...")

        # Default avatar SVG
        avatar_svg = '''<svg width="256" height="256" viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:rgb(91,127,255);stop-opacity:1" />
      <stop offset="100%" style="stop-color:rgb(147,51,234);stop-opacity:1" />
    </linearGradient>
  </defs>
  <circle cx="128" cy="128" r="128" fill="url(#grad1)"/>
  <circle cx="128" cy="100" r="40" fill="white" opacity="0.3"/>
  <path d="M 80 200 Q 128 160 176 200" stroke="white" stroke-width="20" fill="none" opacity="0.3"/>
</svg>'''

        (self.output_dir / "default-avatar.svg").write_text(avatar_svg)
        print("  ✅ Created default-avatar.svg")

        # Hero placeholder
        hero_svg = '''<svg width="1024" height="576" viewBox="0 0 1024 576" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:rgb(91,127,255);stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:rgb(147,51,234);stop-opacity:0.3" />
    </linearGradient>
  </defs>
  <rect width="1024" height="576" fill="#0B0C0F"/>
  <rect width="1024" height="576" fill="url(#heroGrad)"/>
  <text x="512" y="288" text-anchor="middle" fill="white" font-size="48" font-family="system-ui" opacity="0.5">CREATOR</text>
</svg>'''

        (self.output_dir / "hero-landing.svg").write_text(hero_svg)
        print("  ✅ Created hero-landing.svg")

        print(f"\n✅ SVG placeholders created in {self.output_dir}")


async def main():
    """Main execution."""
    print("=" * 60)
    print("Creator Asset Generator")
    print("=" * 60)

    generator = AssetGenerator()

    # Check if ComfyUI is available
    is_available = await generator.check_comfyui_health()

    if not is_available:
        print("\n⚠️  ComfyUI not available. Creating SVG placeholders instead...")
        generator.create_svg_placeholders()
        print("\n💡 To generate AI assets:")
        print("   1. Start ComfyUI: python main.py (in ComfyUI directory)")
        print("   2. Re-run this script: python scripts/generate_assets.py")
        return

    try:
        # Generate all assets
        await generator.generate_hero_image()
        await generator.generate_step_illustrations()
        await generator.generate_dashboard_graphics()
        await generator.generate_default_avatar()

        print("\n" + "=" * 60)
        print("✅ All assets generated successfully!")
        print(f"📁 Output directory: {generator.output_dir}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error generating assets: {e}")
        print("\n⚠️  Falling back to SVG placeholders...")
        generator.create_svg_placeholders()


if __name__ == "__main__":
    asyncio.run(main())
