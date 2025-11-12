"""
Test workflow control - demonstrates enabling/disabling features

This script shows how to control the complex workflow you shared.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.shared.services.comfyui.client import get_comfyui_client, ComfyUIStatus
from workflow_builder import WorkflowBuilder


async def test_workflow_control():
    """Test different workflow configurations."""
    print("🎮 Testing Workflow Control")
    print("=" * 60)

    client = get_comfyui_client()

    # Check server
    print("\n🔍 Checking ComfyUI server...")
    if not await client.health_check():
        print("❌ ComfyUI server not running!")
        return

    print("✅ Server ready")

    # Test 1: Basic workflow (no extras)
    print("\n" + "=" * 60)
    print("Test 1: Basic Workflow (minimal)")
    print("=" * 60)

    builder = WorkflowBuilder()
    workflow = builder.build_basic(
        prompt="abstract coral gradient background, minimalist",
        width=512,
        height=512,
        steps=15  # Faster for testing
    )

    print(f"Nodes in workflow: {len(workflow)}")
    print(f"Node types: {[v['class_type'] for v in workflow.values()]}")

    # Execute
    print("\n🎨 Generating...")
    result = await client.execute_workflow(
        workflow,
        wait_for_completion=True,
        progress_callback=lambda x: print(f"  Progress: {x.get('value', 0)}/{x.get('max', 100)}")
    )

    if result.status == ComfyUIStatus.COMPLETED:
        print(f"✅ Basic workflow completed! ID: {result.prompt_id}")
    else:
        print(f"❌ Failed: {result.error}")

    # Test 2: Workflow with Gemini enabled
    print("\n" + "=" * 60)
    print("Test 2: With Gemini 2.5 Flash")
    print("=" * 60)

    workflow_gemini = builder.build_advanced(
        prompt="futuristic tech background",
        use_gemini=True,  # Enable Gemini
        use_adetailer=False,
        use_upscaling=False,
        width=512,
        height=512
    )

    print(f"Nodes in workflow: {len(workflow_gemini)}")
    print(f"Gemini node added: {'NanoBananoGeminiFlash' in str(workflow_gemini)}")

    print("\n⚠️  Note: This will only work if NanoBanano is installed and loaded")
    print("    Skipping execution for now...")

    # Test 3: Full pipeline
    print("\n" + "=" * 60)
    print("Test 3: Full Pipeline (all features)")
    print("=" * 60)

    workflow_full = builder.build_advanced(
        prompt="professional portrait",
        use_gemini=True,
        use_adetailer=True,  # Face detection
        use_upscaling=True,  # 2x upscale
        width=512,
        height=512
    )

    print(f"Nodes in workflow: {len(workflow_full)}")
    print("Features enabled:")
    print("  - Gemini 2.5 Flash: ✓")
    print("  - Face Detection: ✓")
    print("  - Upscaling: ✓")

    # Test 4: Manual modification
    print("\n" + "=" * 60)
    print("Test 4: Manual Node Modification")
    print("=" * 60)

    # Start with basic
    workflow_mod = builder.build_basic("test prompt")
    print(f"Initial nodes: {len(workflow_mod)}")

    # Remove a node manually
    if "5" in workflow_mod:  # KSampler
        original_steps = workflow_mod["5"]["inputs"]["steps"]
        workflow_mod["5"]["inputs"]["steps"] = 50  # Modify parameters
        print(f"Modified KSampler steps: {original_steps} → 50")

    # Add custom metadata
    for node_id in workflow_mod:
        if "class_type" in workflow_mod[node_id]:
            workflow_mod[node_id]["_meta"] = {
                "title": f"Custom {workflow_mod[node_id]['class_type']}"
            }

    print(f"Added metadata to {len(workflow_mod)} nodes")

    print("\n✅ All control tests completed!")
    print("\n📚 Key Takeaways:")
    print("  1. Workflows are just JSON dicts - modify freely")
    print("  2. Use builder.build_advanced() with feature flags")
    print("  3. Manual modifications: workflow[node_id][...] = new_value")
    print("  4. Remove nodes: del workflow[node_id]")
    print("  5. Add nodes: workflow[new_id] = {...}")


async def demonstrate_config_based_control():
    """Show configuration-based workflow control."""
    print("\n\n🎛️  Configuration-Based Control")
    print("=" * 60)

    # Simulate user preferences/configuration
    user_config = {
        "enable_gemini": False,  # User disabled Gemini
        "enable_face_enhancement": True,  # User wants face enhancement
        "enable_upscaling": False,  # No upscaling to save time
        "quality_preset": "high"  # high, medium, low
    }

    # Map quality presets to sampling parameters
    quality_presets = {
        "low": {"steps": 15, "cfg": 6.0},
        "medium": {"steps": 25, "cfg": 7.5},
        "high": {"steps": 40, "cfg": 8.5}
    }

    # Build workflow based on config
    builder = WorkflowBuilder()

    print("\nUser Configuration:")
    print(f"  Gemini: {user_config['enable_gemini']}")
    print(f"  Face Enhancement: {user_config['enable_face_enhancement']}")
    print(f"  Upscaling: {user_config['enable_upscaling']}")
    print(f"  Quality: {user_config['quality_preset']}")

    workflow = builder.build_advanced(
        prompt="portrait photo",
        use_gemini=user_config["enable_gemini"],
        use_adetailer=user_config["enable_face_enhancement"],
        use_upscaling=user_config["enable_upscaling"]
    )

    # Apply quality preset
    quality = quality_presets[user_config["quality_preset"]]
    for node_id, node in workflow.items():
        if node.get("class_type") == "KSampler":
            workflow[node_id]["inputs"]["steps"] = quality["steps"]
            workflow[node_id]["inputs"]["cfg"] = quality["cfg"]
            print(f"\nApplied {user_config['quality_preset']} quality preset:")
            print(f"  Steps: {quality['steps']}")
            print(f"  CFG: {quality['cfg']}")

    print(f"\nFinal workflow has {len(workflow)} nodes")
    print("✅ Workflow built according to user preferences!")


if __name__ == "__main__":
    try:
        asyncio.run(test_workflow_control())
        asyncio.run(demonstrate_config_based_control())
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
