#!/usr/bin/env python3
"""
Simple test using requests library directly
"""

import requests
import time
import json

API_URL = "http://172.19.0.6:8000"  # Docker container IP

DESSERT_PROMPT = """Hyperrealistic still life of a stainless steel dessert cup filled with scoops of salted caramel ice cream. A melting caramel-coated chocolate bar leans diagonally against the scoops, dripping thick golden caramel that runs down the cup and pools below. Studio lighting with soft warm reflections on a brown background, detailed textures, rich highlights, cinematic composition, modern food photography, ultra sharp focus."""

def test_generate(name, steps):
    print(f"\n{'='*80}")
    print(f"Test: {name}")
    print(f"{'='*80}")

    # Estimate cost
    cost_resp = requests.get(f"{API_URL}/api/v1/monitoring/estimate-cost", params={
        "width": 512,
        "height": 512,
        "steps": steps,
        "num_images": 1
    })
    cost_data = cost_resp.json()
    print(f"Estimated cost: ${cost_data['estimated_cost_usd']:.6f}")
    print(f"Estimated time: {cost_data['estimated_time_seconds']}s\n")

    # Submit job
    payload = {
        "prompt": DESSERT_PROMPT,
        "width": 512,
        "height": 512,
        "steps": steps,
        "cfg_scale": 7.0,
        "sampler_name": "euler_ancestral",
        "num_images": 1
    }

    start_time = time.time()
    resp = requests.post(f"{API_URL}/api/v1/generate", json=payload)
    job_data = resp.json()
    job_id = job_data['job_id']

    print(f"Job submitted: {job_id}")
    print("Waiting for completion...")

    # Poll for completion
    while True:
        status_resp = requests.get(f"{API_URL}/api/v1/jobs/{job_id}")
        status = status_resp.json()

        if status['status'] == 'completed':
            generation_time = time.time() - start_time
            print(f"✓ Completed in {generation_time:.1f}s")
            image_url = status['outputs'][0]['url']
            print(f"✓ Image URL: {image_url}\n")
            return {
                'name': name,
                'time': generation_time,
                'cost': cost_data['estimated_cost_usd'],
                'url': image_url,
                'job_id': job_id
            }
        elif status['status'] == 'failed':
            print(f"✗ Job failed: {status.get('error', 'Unknown error')}")
            return None

        time.sleep(1)

print("=" * 80)
print("ComfyUI API Test - Dessert Prompt A/B Testing")
print("=" * 80)
print(f"\nAPI URL: {API_URL}")
print(f"Prompt: {DESSERT_PROMPT[:80]}...")

results = []
results.append(test_generate("Fast (10 steps)", 10))
time.sleep(2)
results.append(test_generate("Quality (30 steps)", 30))

# Summary
print(f"\n{'='*80}")
print("SUMMARY - A/B Test Results")
print(f"{'='*80}\n")
print(f"{'Config':<25} {'Time':<12} {'Cost':<15}")
print("-" * 52)

for r in results:
    if r:
        print(f"{r['name']:<25} {r['time']:.1f}s{'':<8} ${r['cost']:.6f}")

print(f"\n{'='*80}")
print("Image URLs:")
print(f"{'='*80}")
for r in results:
    if r:
        print(f"\n{r['name']}:")
        print(f"  {r['url']}")

total_time = sum(r['time'] for r in results if r)
total_cost = sum(r['cost'] for r in results if r)
print(f"\nTotal time: {total_time:.1f}s")
print(f"Total cost: ${total_cost:.6f}")
print(f"\nView images in MinIO: http://localhost:9001")
print()
