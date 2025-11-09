#!/usr/bin/env python3
"""
Create a ComfyUI pod on RunPod with proper GPU configuration
"""
import runpod
import os

# API key is already configured in ~/.runpod/config.toml
# So we don't need to set it here

def create_comfyui_pod():
    """Create a GPU pod with ComfyUI image"""

    print("🚀 Creating ComfyUI Pod on RunPod...")
    print()

    # Configuration for the pod
    config = {
        "name": "comfyui-backend",
        "image_name": "yanwk/comfyui-boot:latest",  # Popular ComfyUI Docker image
        "gpu_type_id": "NVIDIA RTX 4000 Ada Generation",  # Mid-range GPU
        "gpu_count": 1,
        "volume_in_gb": 50,  # Persistent storage for models
        "container_disk_in_gb": 20,
        "min_download": 100,  # Min download speed
        "min_upload": 100,    # Min upload speed
        "ports": "8188/http",  # Expose ComfyUI port
        "cloud_type": "SECURE",  # SECURE for on-demand, COMMUNITY for spot
        "env": {
            "COMFYUI_PORT_HOST": "8188",
        }
    }

    print(f"📦 Image: {config['image_name']}")
    print(f"🎮 GPU: {config['gpu_type_id']} x{config['gpu_count']}")
    print(f"💾 Storage: {config['volume_in_gb']}GB volume + {config['container_disk_in_gb']}GB container")
    print(f"🌐 Ports: {config['ports']}")
    print()

    try:
        # Create the pod
        pod = runpod.create_pod(**config)

        print("✅ Pod created successfully!")
        print()
        print(f"Pod ID: {pod['id']}")
        print(f"Pod Name: {pod.get('name', 'N/A')}")
        print(f"Status: {pod.get('status', 'N/A')}")
        print()

        # The URL will be available once the pod starts
        pod_id = pod['id']
        comfyui_url = f"https://{pod_id}-8188.proxy.runpod.net"

        print(f"🔗 ComfyUI URL (once running): {comfyui_url}")
        print()
        print("⏳ Pod is being created... Check RunPod dashboard for status")
        print("   It will take ~2-3 minutes to start up")
        print()
        print("📝 Update your .env file with:")
        print(f"   COMFYUI_URL={comfyui_url}")
        print()

        return pod

    except Exception as e:
        print(f"❌ Error creating pod: {e}")
        print()
        print("💡 Try creating the pod manually via RunPod dashboard:")
        print("   1. Go to https://runpod.io/console/pods")
        print("   2. Click '+ Deploy'")
        print("   3. Select GPU: RTX 4000 Ada (Spot or On-Demand)")
        print("   4. Template: Search for 'ComfyUI' or use image: yanwk/comfyui-boot:latest")
        print("   5. Expose port: 8188")
        print()
        return None

if __name__ == "__main__":
    create_comfyui_pod()
