#!/usr/bin/env python3
import requests
import json
import time

# Test job submission (using Docker container IP)
url = "http://172.19.0.4:8000/api/v1/jobs"
payload = {
    "prompt": "a beautiful sunset over mountains",
    "width": 512,
    "height": 512,
    "steps": 10
}

print("Submitting job...")
response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200 or response.status_code == 201:
    job_data = response.json()
    job_id = job_data.get("job_id")
    print(f"\nJob ID: {job_id}")

    # Monitor job
    for i in range(30):
        time.sleep(2)
        status_response = requests.get(f"http://172.19.0.4:8000/api/v1/jobs/{job_id}")
        if status_response.status_code == 200:
            job_status = status_response.json()
            status = job_status.get("status")
            print(f"Status: {status}")

            if status == "succeeded":
                print("\nSuccess!")
                print(json.dumps(job_status, indent=2))
                break
            elif status == "failed":
                print("\nFailed!")
                print(json.dumps(job_status, indent=2))
                break
