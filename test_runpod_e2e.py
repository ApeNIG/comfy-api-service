#!/usr/bin/env python3
"""
End-to-end test of ComfyUI API with RunPod backend
"""

import requests
import json
import time

API_URL = "http://comfyui-api:8000"

DESSERT_PROMPT = """Hyperrealistic still life of a stainless steel dessert cup filled with scoops of salted caramel ice cream. A melting caramel-coated chocolate bar leans diagonally against the scoops, dripping thick golden caramel that runs down the cup and pools below. Studio lighting with soft warm reflections on a brown background, detailed textures, rich highlights, cinematic composition, modern food photography, ultra sharp focus."""

def main():
    print("=" * 80)
    print("ComfyUI API + RunPod - End-to-End Test")
    print("=" * 80)

    # 1. Health check
    print("\n1. Health Check")
    print("-" * 40)
    resp = requests.get(f"{API_URL}/health")
    health = resp.json()
    print(f"Status: {health['status']}")
    print(f"ComfyUI: {health['comfyui_status']}")
    print(f"URL: {health['comfyui_url']}")

    if health['comfyui_status'] != 'connected':
        print("\n❌ ComfyUI is not connected!")
        return

    print("✅ ComfyUI is connected!")

    # 2. Submit job
    print("\n2. Submit Image Generation Job")
    print("-" * 40)
    payload = {
        "prompt": DESSERT_PROMPT,
        "width": 512,
        "height": 512,
        "steps": 10,
        "cfg_scale": 7.0,
        "sampler_name": "euler_ancestral",
        "num_images": 1
    }

    print(f"Prompt: {DESSERT_PROMPT[:60]}...")
    print(f"Size: {payload['width']}x{payload['height']}, Steps: {payload['steps']}")

    start_time = time.time()
    resp = requests.post(f"{API_URL}/api/v1/generate", json=payload)

    if resp.status_code >= 400:
        print(f"\n❌ Job submission failed: {resp.status_code}")
        print(f"Response: {resp.text}")
        return

    job_data = resp.json()
    job_id = job_data.get('job_id')
    print(f"\n✅ Job submitted!")
    print(f"Job ID: {job_id}")

    # 3. Monitor job
    print("\n3. Monitoring Job Progress")
    print("-" * 40)

    last_status = None
    for i in range(120):  # 2 minutes max
        time.sleep(2)

        resp = requests.get(f"{API_URL}/api/v1/jobs/{job_id}")

        if resp.status_code == 404:
            print(f"⏳ Job not found yet (queued)...")
            continue

        if resp.status_code >= 400:
            print(f"\n❌ Error checking job: {resp.status_code}")
            print(resp.text)
            break

        job_status = resp.json()

        # Check for different response formats
        if isinstance(job_status, dict):
            current_status = job_status.get('state', job_status.get('status', 'unknown'))

            if current_status != last_status:
                print(f"Status: {current_status}")
                last_status = current_status

            # Check completion
            if current_status in ['completed', 'succeeded', 'success']:
                elapsed = time.time() - start_time
                print(f"\n✅ Job completed in {elapsed:.1f}s!")

                # Get output
                outputs = job_status.get('outputs', job_status.get('result', []))
                if outputs:
                    if isinstance(outputs, list) and len(outputs) > 0:
                        image_url = outputs[0].get('url', 'No URL')
                        print(f"\nImage URL: {image_url}")
                    else:
                        print(f"\nOutputs: {outputs}")

                print(f"\nFull response:")
                print(json.dumps(job_status, indent=2))
                return

            elif current_status in ['failed', 'error']:
                print(f"\n❌ Job failed!")
                error = job_status.get('error', job_status.get('message', 'Unknown error'))
                print(f"Error: {error}")
                print(f"\nFull response:")
                print(json.dumps(job_status, indent=2))
                return

    print(f"\n⏰ Timeout waiting for job completion (120s)")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
