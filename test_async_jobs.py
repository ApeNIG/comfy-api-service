#!/usr/bin/env python3
"""
Test async job queue system with RunPod
"""

import requests
import json
import time

API_URL = "http://comfyui-api:8000"

def main():
    print("=" * 80)
    print("Async Job Queue Test - RunPod ComfyUI")
    print("=" * 80)

    # Health check
    print("\n1. Health Check")
    resp = requests.get(f"{API_URL}/health")
    health = resp.json()
    print(f"   Status: {health['status']}")
    print(f"   ComfyUI: {health['comfyui_status']}")

    if health['comfyui_status'] != 'connected':
        print("\n❌ ComfyUI not connected!")
        return

    # Submit async job
    print("\n2. Submit Async Job")
    print("-" * 40)

    payload = {
        "prompt": "A serene mountain landscape with a lake",
        "width": 512,
        "height": 512,
        "steps": 10,
        "cfg_scale": 7.0,
        "sampler_name": "euler_ancestral"
    }

    print(f"Prompt: {payload['prompt']}")
    print("\nSubmitting job to queue...")

    try:
        resp = requests.post(
            f"{API_URL}/api/v1/jobs",  # Note: /jobs not /generate
            json=payload,
            headers={"Idempotency-Key": f"test-{int(time.time())}"}
        )

        if resp.status_code >= 400:
            print(f"\n❌ Job submission failed: HTTP {resp.status_code}")
            print(f"Response: {resp.text}")
            return

        job_data = resp.json()
        job_id = job_data.get('job_id')

        print(f"\n✅ Job submitted!")
        print(f"Job ID: {job_id}")
        print(f"Status: {job_data.get('status', 'N/A')}")
        print(f"Location: {resp.headers.get('Location', 'N/A')}")

        # Monitor job status
        print("\n3. Monitor Job Status")
        print("-" * 40)

        start_time = time.time()

        for i in range(60):  # Check for up to 60 seconds
            time.sleep(1)

            status_resp = requests.get(f"{API_URL}/api/v1/jobs/{job_id}")

            if status_resp.status_code == 404:
                print(f"⏳ Job not in database yet...")
                continue

            if status_resp.status_code >= 400:
                print(f"\n❌ Error checking job: {status_resp.status_code}")
                print(status_resp.text)
                break

            job_status = status_resp.json()
            # The Redis data uses 'status' but API might return 'state'
            state = job_status.get('status', job_status.get('state', 'unknown'))
            progress = job_status.get('progress', 0)

            if i % 5 == 0:  # Print every 5 seconds
                print(f"State: {state}, Progress: {progress:.0%}")

            if state in ['completed', 'succeeded', 'finished']:
                elapsed = time.time() - start_time
                print(f"\n✅ Job completed in {elapsed:.1f}s!")

                # Print result
                result = job_status.get('result', {})
                if result.get('artifacts'):
                    print(f"\nArtifacts:")
                    for artifact in result['artifacts']:
                        print(f"  - {artifact.get('url', 'No URL')}")

                print(f"\nFull Response:")
                print(json.dumps(job_status, indent=2))
                return

            elif state in ['failed', 'error']:
                print(f"\n❌ Job failed!")
                error = job_status.get('error', 'Unknown error')
                print(f"Error: {error}")
                print(f"\nFull Response:")
                print(json.dumps(job_status, indent=2))
                return

        print(f"\n⏰ Timeout after 60s")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
