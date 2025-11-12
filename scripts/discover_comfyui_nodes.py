"""
Discover all available ComfyUI nodes and their parameters

This script queries your ComfyUI instance to show:
- All installed nodes (built-in + custom)
- Required inputs for each node
- Optional inputs
- Valid values for each parameter

Use this to explore what's available and design custom workflows!
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp
from config import settings


async def discover_nodes():
    """Query ComfyUI /object_info endpoint to list all nodes."""
    print("🔍 Discovering ComfyUI Nodes...")
    print("=" * 80)
    print()

    url = f"{settings.COMFYUI_URL}/object_info"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                data = await response.json()

                # Categorize nodes
                samplers = []
                loaders = []
                conditioning = []
                latent = []
                image = []
                custom = []
                other = []

                for node_name in sorted(data.keys()):
                    node_info = data[node_name]

                    # Categorize
                    if "Sampler" in node_name or "Sample" in node_name:
                        samplers.append((node_name, node_info))
                    elif "Loader" in node_name or "Load" in node_name:
                        loaders.append((node_name, node_info))
                    elif "CLIP" in node_name or "Condition" in node_name:
                        conditioning.append((node_name, node_info))
                    elif "Latent" in node_name:
                        latent.append((node_name, node_info))
                    elif "Image" in node_name or "VAE" in node_name:
                        image.append((node_name, node_info))
                    elif any(x in node_name for x in ["Banana", "Custom", "Advanced"]):
                        custom.append((node_name, node_info))
                    else:
                        other.append((node_name, node_info))

                # Print by category
                print_category("🎲 Samplers & Generation", samplers)
                print_category("📦 Loaders", loaders)
                print_category("📝 Conditioning & Prompts", conditioning)
                print_category("🖼️  Latent Operations", latent)
                print_category("🎨 Image Processing", image)
                print_category("🍌 Custom Nodes", custom)
                print_category("🔧 Other", other)

                print()
                print("=" * 80)
                print(f"✅ Total nodes available: {len(data)}")
                print()
                print("💡 To use a node in your workflow:")
                print('   workflow["node_id"] = {')
                print('       "inputs": { ... },')
                print('       "class_type": "NodeClassName"')
                print('   }')

    except Exception as e:
        print(f"❌ Error discovering nodes: {e}")
        print()
        print("Make sure ComfyUI is running and accessible")


def print_category(title: str, nodes: list):
    """Print a category of nodes."""
    if not nodes:
        return

    print()
    print(title)
    print("-" * 80)

    for node_name, node_info in nodes:
        print(f"\n  📌 {node_name}")

        # Show required inputs
        if "input" in node_info and "required" in node_info["input"]:
            inputs = node_info["input"]["required"]
            if inputs:
                print(f"     Required inputs:")
                for input_name, input_spec in inputs.items():
                    # Parse input spec
                    if isinstance(input_spec, list) and len(input_spec) > 0:
                        input_type = input_spec[0]

                        # Show valid values if available
                        if isinstance(input_type, list):
                            values_preview = ", ".join(str(v) for v in input_type[:3])
                            if len(input_type) > 3:
                                values_preview += f"... ({len(input_type)} total)"
                            print(f"       - {input_name}: [{values_preview}]")
                        elif isinstance(input_type, str):
                            print(f"       - {input_name}: {input_type}")
                        else:
                            print(f"       - {input_name}: {input_spec}")
                    else:
                        print(f"       - {input_name}: {input_spec}")

        # Show optional inputs
        if "input" in node_info and "optional" in node_info["input"]:
            optional = node_info["input"]["optional"]
            if optional:
                print(f"     Optional inputs: {', '.join(optional.keys())}")


async def main():
    await discover_nodes()


if __name__ == "__main__":
    asyncio.run(main())
