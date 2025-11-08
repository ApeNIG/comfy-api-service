#!/usr/bin/env python3
"""
Simple image generation example using the ComfyUI Python SDK.
"""

from comfyui_client import ComfyUIClient

def main():
    # Initialize client
    print("Connecting to ComfyUI API...")
    client = ComfyUIClient("http://localhost:8000")

    # Check health
    try:
        health = client.health()
        print(f"API Status: {health['status']}")
        print(f"API Version: {health['api_version']}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Estimate cost first
    print("\nEstimating cost...")
    cost = client.estimate_cost(
        width=512,
        height=512,
        steps=20,
        num_images=1
    )
    print(f"  GPU Type: {cost['gpu_type']}")
    print(f"  Estimated Time: {cost['estimated_time_seconds']}s")
    print(f"  Estimated Cost: ${cost['estimated_cost_usd']:.6f}")

    # Generate image
    print("\nSubmitting image generation job...")
    job = client.generate(
        prompt="A beautiful sunset over mountains, golden hour, photorealistic",
        negative_prompt="blurry, low quality",
        width=512,
        height=512,
        steps=20
    )

    print(f"Job ID: {job.job_id}")
    print("Waiting for completion...")

    # Wait with progress callback
    def progress_callback(status_data):
        status = status_data['status']
        if status == 'processing':
            progress = status_data.get('progress', 0)
            print(f"  Progress: {progress*100:.0f}%")

    try:
        result = job.wait_for_completion(
            timeout=600,
            poll_interval=5,
            progress_callback=progress_callback
        )

        print(f"\nGeneration complete!")
        print(f"Generated {len(result.artifacts)} images")

        # Download the image
        for i, artifact in enumerate(result.artifacts):
            filename = f"generated_image_{i}.png"
            result.download_image(index=i, save_path=filename)
            print(f"  Saved: {filename}")
            print(f"  Seed: {artifact.get('seed', 'N/A')}")
            print(f"  Size: {artifact.get('width')}x{artifact.get('height')}")

        # Show stats
        print("\nUsage Statistics:")
        stats = client.get_stats()
        print(f"  Total Jobs: {stats['total_jobs']}")
        print(f"  Success Rate: {stats['success_rate_percent']:.1f}%")
        print(f"  Total Cost: ${stats['total_cost_usd']:.4f}")
        print(f"  Avg Cost/Image: ${stats['avg_cost_per_image_usd']:.6f}")

    except Exception as e:
        print(f"\nError: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
