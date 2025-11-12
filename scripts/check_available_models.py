"""
Check what models are available in ComfyUI
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp
from config import settings


async def main():
    print("🔍 Checking available models in ComfyUI...")
    print("=" * 60)

    # Get object info (includes available models, samplers, etc.)
    url = f"{settings.COMFYUI_URL}/object_info"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                data = await response.json()

                # Extract checkpoint loader info
                if "CheckpointLoaderSimple" in data:
                    checkpoint_info = data["CheckpointLoaderSimple"]
                    if "input" in checkpoint_info and "required" in checkpoint_info["input"]:
                        ckpt_names = checkpoint_info["input"]["required"].get("ckpt_name", [])

                        if ckpt_names and len(ckpt_names) > 0:
                            available_models = ckpt_names[0]  # First element is the list of models

                            print(f"✅ Found {len(available_models)} checkpoint models:")
                            print()
                            for model in available_models:
                                print(f"  - {model}")
                            print()
                            print("=" * 60)
                            print()
                            print("💡 Recommended: Use one of these models in the workflow")
                            if available_models:
                                print(f"   Suggested model: {available_models[0]}")
                        else:
                            print("❌ No checkpoint models found!")
                            print("You may need to download models to your RunPod instance")
                else:
                    print("❌ Could not find CheckpointLoaderSimple info")
                    print("This might indicate a ComfyUI API issue")

    except Exception as e:
        print(f"❌ Error checking models: {e}")
        print()
        print("Make sure ComfyUI is running and accessible")


if __name__ == "__main__":
    asyncio.run(main())
