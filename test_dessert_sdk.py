#!/usr/bin/env python3
"""
Test script for dessert prompt using ComfyUI Python SDK
"""

from comfyui_client import ComfyUIClient
import time

# Your dessert prompt
DESSERT_PROMPT = """Hyperrealistic still life of a stainless steel dessert cup filled with scoops of salted caramel ice cream. A melting caramel-coated chocolate bar leans diagonally against the scoops, dripping thick golden caramel that runs down the cup and pools below. Studio lighting with soft warm reflections on a brown background, detailed textures, rich highlights, cinematic composition, modern food photography, ultra sharp focus."""

def main():
    print("=" * 80)
    print("ComfyUI Python SDK Test - Dessert Prompt")
    print("=" * 80)
    print()

    # Connect to API
    print("Connecting to ComfyUI API at http://localhost:8000...")
    client = ComfyUIClient("http://localhost:8000")
    print("✓ Connected successfully!\n")

    # Test configurations
    configs = [
        {"name": "Fast (10 steps)", "steps": 10, "width": 512, "height": 512},
        {"name": "Quality (30 steps)", "steps": 30, "width": 512, "height": 512},
    ]

    results = []

    for i, config in enumerate(configs, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(configs)}: {config['name']}")
        print(f"{'='*80}")
        print(f"Configuration: {config['width']}x{config['height']}, {config['steps']} steps")
        print(f"Prompt: {DESSERT_PROMPT[:80]}...")
        print()

        # Estimate cost
        cost_info = client.estimate_cost(
            config['width'],
            config['height'],
            config['steps'],
            num_images=1
        )

        print(f"Estimated cost: ${cost_info['estimated_cost_usd']:.6f}")
        print(f"Estimated time: {cost_info['estimated_time_seconds']}s")
        print()

        # Generate image
        print("Submitting job...")
        start_time = time.time()

        job = client.generate(
            prompt=DESSERT_PROMPT,
            width=config['width'],
            height=config['height'],
            steps=config['steps'],
            cfg_scale=7.0,
            sampler_name="euler_ancestral",
            num_images=1
        )

        print(f"✓ Job submitted: {job.job_id}")
        print("Waiting for completion...")

        # Wait for result
        result = job.wait_for_completion(timeout=300)
        generation_time = time.time() - start_time

        print(f"✓ Generation completed in {generation_time:.1f}s")

        # Download image
        output_filename = f"dessert_{config['steps']}_steps.png"
        result.download_image(0, output_filename)
        print(f"✓ Image saved to: {output_filename}")

        # Get image URL
        image_url = result.get_image_url(0)
        print(f"✓ Image URL: {image_url}")

        # Store results
        results.append({
            'config': config,
            'job_id': job.job_id,
            'generation_time': generation_time,
            'estimated_cost': cost_info['estimated_cost_usd'],
            'output_file': output_filename,
            'image_url': image_url
        })

        # Small delay between tests
        if i < len(configs):
            print("\nWaiting 2 seconds before next test...")
            time.sleep(2)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - A/B Test Results")
    print("=" * 80)
    print()
    print(f"{'Config':<25} {'Time':<12} {'Cost':<15} {'Output File':<30}")
    print("-" * 80)

    for r in results:
        print(f"{r['config']['name']:<25} {r['generation_time']:.1f}s{'':<8} ${r['estimated_cost']:.6f}{'':<6} {r['output_file']:<30}")

    print("\n" + "=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print("1. Compare the images visually:")
    for r in results:
        print(f"   - {r['output_file']}")
    print()
    print("2. Check images in MinIO browser: http://localhost:9001")
    print("   Login: minioadmin / minioadmin")
    print()
    print("3. View image URLs:")
    for r in results:
        print(f"   - {r['config']['name']}: {r['image_url']}")
    print()

    total_time = sum(r['generation_time'] for r in results)
    total_cost = sum(r['estimated_cost'] for r in results)
    print(f"Total time: {total_time:.1f}s")
    print(f"Total cost: ${total_cost:.6f}")
    print()

if __name__ == "__main__":
    main()
