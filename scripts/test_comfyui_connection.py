"""
Quick test to check if ComfyUI is accessible
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.shared.services.comfyui.client import get_comfyui_client


async def main():
    print("🔍 Testing ComfyUI connection...")
    print("=" * 60)

    client = get_comfyui_client()
    print(f"ComfyUI URL: {client.base_url}")
    print(f"WebSocket URL: {client.ws_url}")
    print()

    print("Checking health...")
    is_healthy = await client.health_check()

    if is_healthy:
        print("✅ ComfyUI is accessible and healthy!")
        print()
        print("You can now run:")
        print("  python scripts/generate_hero_images.py")
    else:
        print("❌ ComfyUI is not accessible")
        print()
        print("Troubleshooting:")
        print("1. Open this URL in your browser:")
        print(f"   {client.base_url}")
        print("2. Wait for ComfyUI interface to load (may take 1-2 minutes)")
        print("3. Run this test again")
        print()
        print("If the URL doesn't load:")
        print("- Check if RunPod instance is running")
        print("- Verify COMFYUI_URL in .env file")
        print("- Make sure instance isn't paused/stopped")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
