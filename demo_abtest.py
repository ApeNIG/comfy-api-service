#!/usr/bin/env python3
"""
A/B Testing Demo - See it in action!

This shows you EXACTLY what A/B testing does.
"""

import requests
import json
import time

API_URL = "http://172.19.0.6:8000"

print("=" * 70)
print("A/B TESTING DEMO - Let's Compare Different Settings!")
print("=" * 70)
print()
print("WHAT IS A/B TESTING?")
print("  - Generate the SAME image with DIFFERENT settings")
print("  - Compare: quality, speed, cost")
print("  - Find the best settings for your needs")
print()
print("=" * 70)
print()

# Example: Compare fast vs quality settings
print("TEST SCENARIO: Fast vs Quality")
print("  - Variant A: 10 steps (fast but lower quality)")
print("  - Variant B: 30 steps (slower but higher quality)")
print()

test_data = {
    "base_prompt": "A serene mountain landscape with a lake",
    "description": "Comparing speed vs quality (10 steps vs 30 steps)",
    "variants": [
        {
            "name": "Fast (10 steps)",
            "request": {
                "prompt": "A serene mountain landscape with a lake",
                "steps": 10,
                "width": 512,
                "height": 512
            }
        },
        {
            "name": "Quality (30 steps)",
            "request": {
                "prompt": "A serene mountain landscape with a lake",
                "steps": 30,
                "width": 512,
                "height": 512
            }
        }
    ]
}

print("Sending A/B test request...")
print(json.dumps(test_data, indent=2))
print()
print("⏳ Generating images... (this takes a few minutes)")
print()

try:
    response = requests.post(
        f"{API_URL}/api/v1/abtest",
        json=test_data,
        timeout=600  # 10 minutes max
    )

    if response.status_code == 201:
        result = response.json()

        print("=" * 70)
        print("✅ A/B TEST COMPLETE!")
        print("=" * 70)
        print()
        print(f"Test ID: {result['test_id']}")
        print(f"Prompt: {result['base_prompt']}")
        print(f"Description: {result['description']}")
        print()
        print(f"Results: {result['completed_variants']}/{result['total_variants']} successful")
        print(f"Total Cost: ${result['total_cost']:.6f}")
        print(f"Total Time: {result['total_time']:.1f} seconds")
        print()
        print("=" * 70)
        print("COMPARISON:")
        print("=" * 70)
        print()

        for variant in result['variants']:
            print(f"📊 {variant['name']}")
            print(f"   Status: {variant['status']}")
            if variant['generation_time']:
                print(f"   Time: {variant['generation_time']:.1f} seconds")
            if variant['estimated_cost']:
                print(f"   Cost: ${variant['estimated_cost']:.6f}")
            if variant['image_url']:
                print(f"   Image: {variant['image_url']}")
            if variant['metadata']:
                print(f"   Steps: {variant['metadata']['steps']}")
            print()

        print("=" * 70)
        print("WINNER ANALYSIS:")
        print("=" * 70)
        print()

        # Find fastest and cheapest
        variants_with_time = [v for v in result['variants'] if v['generation_time']]
        if variants_with_time:
            fastest = min(variants_with_time, key=lambda x: x['generation_time'])
            cheapest = min(variants_with_time, key=lambda x: x['estimated_cost'] or 999)

            print(f"🏃 Fastest: {fastest['name']} ({fastest['generation_time']:.1f}s)")
            print(f"💰 Cheapest: {cheapest['name']} (${cheapest['estimated_cost']:.6f})")
            print()

        print("=" * 70)
        print()
        print("This helps you decide:")
        print("  • Need it fast? Use the fast variant")
        print("  • Need best quality? Use the quality variant")
        print("  • See exact cost difference")
        print()

    else:
        print(f"❌ Error: HTTP {response.status_code}")
        print(response.text)

except requests.exceptions.Timeout:
    print("⏱️  Request timed out - images might be generating slowly")
    print("   Try again with simpler prompts or check the API logs")
except Exception as e:
    print(f"❌ Error: {e}")
    print()
    print("Make sure:")
    print("  1. API is running: docker compose ps")
    print("  2. Worker is running: docker compose ps worker")
    print("  3. Redis is running: docker compose ps redis")
