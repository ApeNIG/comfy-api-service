#!/usr/bin/env python3
"""
Test synchronous image generation with RunPod
"""

import requests
import json
import time

API_URL = "http://comfyui-api:8000"

def main():
    print("=" * 80)
    print("Synchronous Generation Test - RunPod ComfyUI")
    print("=" * 80)

    # Health check
    print("\n1. Health Check")
    resp = requests.get(f"{API_URL}/health")
    health = resp.json()
    print(f"   Status: {health['status']}")
    print(f"   ComfyUI: {health['comfyui_status']}")
    print(f"   URL: {health['comfyui_url']}")

    if health['comfyui_status'] != 'connected':
        print("\n❌ ComfyUI not connected!")
        return

    # Test generation
    print("\n2. Generate Image (Synchronous)")
    print("-" * 40)

    payload = {
        "prompt": "A beautiful sunset over mountains, golden hour, dramatic clouds",
        "width": 512,
        "height": 512,
        "steps": 10,
        "cfg_scale": 7.0,
        "sampler_name": "euler_ancestral"
    }

    print(f"Prompt: {payload['prompt']}")
    print(f"Size: {payload['width']}x{payload['height']}")
    print(f"Steps: {payload['steps']}")
    print("\nSubmitting generation request...")

    start_time = time.time()

    try:
        resp = requests.post(
            f"{API_URL}/api/v1/generate/",
            json=payload,
            timeout=300  # 5 minute timeout
        )

        elapsed = time.time() - start_time

        if resp.status_code >= 400:
            print(f"\n❌ Generation failed: HTTP {resp.status_code}")
            print(f"Response: {resp.text}")
            return

        result = resp.json()

        print(f"\n✅ Generation completed in {elapsed:.1f}s!")
        print(f"\nJob ID: {result.get('job_id', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")

        if result.get('image_url'):
            print(f"\nImage URL: {result['image_url']}")

        if result.get('metadata'):
            print(f"\nMetadata:")
            print(json.dumps(result['metadata'], indent=2))

        print(f"\nFull Response:")
        print(json.dumps(result, indent=2))

    except requests.Timeout:
        print(f"\n❌ Request timed out after {time.time() - start_time:.1f}s")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
