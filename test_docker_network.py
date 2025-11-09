#!/usr/bin/env python3
"""
Test the ComfyUI API service from within Docker network
"""

import requests
import json
import time

API_URL = "http://comfyui-api:8000"

DESSERT_PROMPT = """Hyperrealistic still life of a stainless steel dessert cup filled with scoops of salted caramel ice cream. A melting caramel-coated chocolate bar leans diagonally against the scoops, dripping thick golden caramel that runs down the cup and pools below. Studio lighting with soft warm reflections on a brown background, detailed textures, rich highlights, cinematic composition, modern food photography, ultra sharp focus."""

def main():
    print("=" * 80)
    print("ComfyUI API Test - RunPod Connection Test")
    print("=" * 80)
    print(f"\nAPI URL: {API_URL}\n")

    # Test health endpoint
    print("1. Testing health endpoint...")
    try:
        resp = requests.get(f"{API_URL}/healthz")
        print(f"   ✓ Health check: {resp.json()}")
    except Exception as e:
        print(f"   ✗ Health check failed: {e}")
        return

    # Test ComfyUI connection
    print("\n2. Testing ComfyUI connection...")
    try:
        resp = requests.get(f"{API_URL}/api/v1/health")
        health_data = resp.json()
        print(f"   ✓ ComfyUI Status: {health_data.get('comfyui_status', 'unknown')}")
        print(f"   ✓ Response: {json.dumps(health_data, indent=2)}")
    except Exception as e:
        print(f"   ✗ ComfyUI health check failed: {e}")

    # Submit a test job
    print("\n3. Submitting test job...")
    payload = {
        "prompt": DESSERT_PROMPT,
        "width": 512,
        "height": 512,
        "steps": 10,
        "cfg_scale": 7.0,
        "sampler_name": "euler_ancestral",
        "num_images": 1
    }

    try:
        start_time = time.time()
        resp = requests.post(f"{API_URL}/api/v1/generate", json=payload)
        if resp.status_code >= 400:
            print(f"   ✗ Job submission failed: {resp.status_code}")
            print(f"   Response: {resp.text}")
            return

        job_data = resp.json()
        job_id = job_data['job_id']
        print(f"   ✓ Job submitted: {job_id}")
        print(f"   Waiting for completion...")

        # Poll for completion
        for attempt in range(120):  # 2 minutes max
            time.sleep(1)
            status_resp = requests.get(f"{API_URL}/api/v1/jobs/{job_id}")
            status = status_resp.json()

            current_status = status['status']
            if attempt % 5 == 0:  # Print every 5 seconds
                print(f"   Status: {current_status}")

            if current_status == 'completed':
                generation_time = time.time() - start_time
                print(f"\n   ✓ Completed in {generation_time:.1f}s")
                if status.get('outputs'):
                    image_url = status['outputs'][0].get('url', 'No URL')
                    print(f"   ✓ Image URL: {image_url}")
                print(f"\n   Full response:")
                print(f"   {json.dumps(status, indent=2)}")
                break
            elif current_status == 'failed':
                print(f"\n   ✗ Job failed: {status.get('error', 'Unknown error')}")
                print(f"   Full response:")
                print(f"   {json.dumps(status, indent=2)}")
                break
        else:
            print(f"\n   ✗ Timeout waiting for job completion")

    except Exception as e:
        print(f"   ✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
