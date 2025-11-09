#!/usr/bin/env python3
"""
Stop the broken pod and create a new one with a working ComfyUI image
"""
import runpod
import sys

def main():
    # Stop the broken pod
    broken_pod_id = "w9eidpqza7je2o"

    print(f"🛑 Stopping broken pod: {broken_pod_id}")
    try:
        runpod.stop_pod(broken_pod_id)
        print("✅ Pod stopped")
    except Exception as e:
        print(f"⚠️  Could not stop pod: {e}")

    print()
    print("📦 Creating new pod with a working ComfyUI image...")
    print()

    # Try a different, well-known ComfyUI image
    config = {
        "name": "comfyui-gpu",
        "image_name": "runpod/stable-diffusion:web-ui-10.2.1",  # RunPod's official SD image with ComfyUI
        "gpu_type_id": "NVIDIA RTX 4000 Ada Generation",
        "gpu_count": 1,
        "volume_in_gb": 50,
        "container_disk_in_gb": 20,
        "ports": "8188/http,3000/http",
        "cloud_type": "SECURE",  # On-demand
        "env": {}
    }

    print(f"📦 Image: {config['image_name']}")
    print(f"🎮 GPU: {config['gpu_type_id']}")
    print()

    try:
        pod = runpod.create_pod(**config)
        pod_id = pod['id']

        print("✅ New pod created!")
        print(f"   Pod ID: {pod_id}")
        print(f"   URL: https://{pod_id}-8188.proxy.runpod.net")
        print()
        print("⏳ The pod will take 2-3 minutes to start")
        print()
        print("📝 Update your .env and docker-compose.yml with:")
        print(f"   COMFYUI_URL=https://{pod_id}-8188.proxy.runpod.net")

    except Exception as e:
        print(f"❌ Error creating pod: {e}")
        print()
        print("💡 Alternative: Use RunPod's template system")
        print("   1. Go to https://runpod.io/console/pods")
        print("   2. Click '+ Deploy'")
        print("   3. Search for 'ComfyUI' in templates")
        print("   4. Select an official template")
        print("   5. Choose RTX 4000 Ada (Spot for cheaper)")

if __name__ == "__main__":
    main()
