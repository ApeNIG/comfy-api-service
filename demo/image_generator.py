#!/usr/bin/env python3
"""
ComfyUI Image Generator Demo

A feature-rich CLI application demonstrating the ComfyUI Python SDK.

Features:
- Interactive image generation
- Cost estimation before generating
- Real-time progress tracking
- Multiple image generation
- Usage statistics
- Error handling

Usage:
    python image_generator.py
    python image_generator.py --prompt "A sunset" --width 512 --height 512
    python image_generator.py --stats
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from comfyui_client import ComfyUIClient
    from comfyui_client.exceptions import (
        ComfyUIClientError,
        JobFailedError,
        TimeoutError as JobTimeoutError,
    )
except ImportError:
    print("Error: comfyui_client not installed.")
    print("Install it with: cd sdk/python && pip install -e .")
    sys.exit(1)


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print colored header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.END} {text}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.END} {text}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ{Colors.END} {text}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")


def progress_callback(status_data: dict):
    """Callback for job progress updates"""
    status = status_data.get('status', 'unknown')

    # Simple progress indicator
    if status == 'pending':
        print(f"  {Colors.YELLOW}⏳{Colors.END} Waiting in queue...", end='\r')
    elif status == 'running':
        print(f"  {Colors.CYAN}⚙{Colors.END}  Generating image...  ", end='\r')
    elif status == 'succeeded':
        print(f"  {Colors.GREEN}✓{Colors.END} Generation complete!   ")
    elif status == 'failed':
        print(f"  {Colors.RED}✗{Colors.END} Generation failed     ")


def estimate_cost(client: ComfyUIClient, width: int, height: int, steps: int, num_images: int = 1):
    """Estimate and display cost before generating"""
    print_header("Cost Estimation")

    try:
        cost_info = client.estimate_cost(width, height, steps, num_images)

        print(f"GPU Type:        {Colors.BOLD}{cost_info['gpu_type']}{Colors.END}")
        print(f"Hourly Rate:     ${cost_info['hourly_rate']:.2f}/hour")
        print(f"Est. Time:       {cost_info['estimated_time_seconds']}s per image")
        print(f"Total Time:      {cost_info['total_time_seconds']}s")
        print(f"Cost per Image:  ${cost_info['cost_per_image']:.6f}")
        print(f"Total Cost:      {Colors.BOLD}${cost_info['estimated_cost_usd']:.6f}{Colors.END}")

        if cost_info['estimated_cost_usd'] == 0:
            print_info("Free tier (CPU/Local GPU)")
        elif cost_info['estimated_cost_usd'] < 0.001:
            print_success("Very affordable! Less than $0.001")
        elif cost_info['estimated_cost_usd'] < 0.01:
            print_success("Affordable! Less than a penny")
        else:
            print_warning(f"This will cost ${cost_info['estimated_cost_usd']:.4f}")

        return cost_info

    except Exception as e:
        print_error(f"Failed to estimate cost: {e}")
        return None


def show_stats(client: ComfyUIClient):
    """Display usage statistics"""
    print_header("Usage Statistics")

    try:
        stats = client.get_stats()

        print(f"Total Jobs:        {stats['total_jobs']}")
        print(f"Successful:        {Colors.GREEN}{stats['successful_jobs']}{Colors.END}")
        print(f"Failed:            {Colors.RED}{stats['failed_jobs']}{Colors.END}")
        print(f"Success Rate:      {stats['success_rate_percent']:.1f}%")
        print(f"Images Generated:  {stats['total_images_generated']}")
        print(f"Total Cost:        ${stats['total_cost_usd']:.6f}")
        print(f"Total Runtime:     {stats['total_runtime_hours']:.2f} hours")

        if stats['total_images_generated'] > 0:
            print(f"Avg Time/Image:    {stats['avg_time_per_image_seconds']:.1f}s")
            print(f"Avg Cost/Image:    ${stats['avg_cost_per_image_usd']:.6f}")

    except Exception as e:
        print_error(f"Failed to get stats: {e}")


def show_monthly_projection(client: ComfyUIClient, images_per_day: int):
    """Show monthly cost projection"""
    print_header("Monthly Cost Projection")

    try:
        # Use reasonable time estimate (3 seconds for RTX 4000 Ada)
        projection = client.project_monthly_cost(images_per_day, avg_time_seconds=3.0)

        print(f"Images per Day:    {projection['images_per_day']}")
        print(f"Monthly Images:    {projection['monthly_images']}")
        print(f"Daily Runtime:     {projection['daily_runtime_hours']:.2f} hours")
        print(f"Monthly Runtime:   {projection['monthly_runtime_hours']:.1f} hours")
        print(f"Daily Cost:        ${projection['daily_cost_usd']:.4f}")
        print(f"Monthly Cost:      {Colors.BOLD}${projection['monthly_cost_usd']:.2f}{Colors.END}")
        print(f"Cost per Image:    ${projection['cost_per_image']:.6f}")

        if projection['monthly_cost_usd'] == 0:
            print_success("Free tier - no monthly charges!")
        elif projection['monthly_cost_usd'] < 10:
            print_success(f"Very affordable! Less than $10/month")
        elif projection['monthly_cost_usd'] < 50:
            print_info(f"Reasonable cost for {images_per_day} images/day")
        else:
            print_warning("Consider optimizing image parameters or GPU type")

    except Exception as e:
        print_error(f"Failed to project costs: {e}")


def generate_image(
    client: ComfyUIClient,
    prompt: str,
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    num_images: int = 1,
    output_dir: str = "generated_images",
    estimate_first: bool = True,
    show_progress: bool = True
):
    """Generate an image with the given parameters"""

    # Show cost estimation
    if estimate_first:
        cost_info = estimate_cost(client, width, height, steps, num_images)
        if cost_info is None:
            print_error("Cannot proceed without cost estimation")
            return False

        # Ask for confirmation if cost is high
        if cost_info['estimated_cost_usd'] > 0.01:
            response = input(f"\nProceed with generation? (y/n): ").strip().lower()
            if response != 'y':
                print_info("Generation cancelled")
                return False

    # Generate image
    print_header("Generating Image")
    print(f"Prompt:  {Colors.BOLD}{prompt}{Colors.END}")
    print(f"Size:    {width}x{height}")
    print(f"Steps:   {steps}")
    print(f"Count:   {num_images}")
    print()

    try:
        # Submit job
        print_info("Submitting job to ComfyUI API...")
        job = client.generate(
            prompt=prompt,
            width=width,
            height=height,
            steps=steps,
            num_images=num_images
        )

        print_success(f"Job submitted: {job.job_id}")

        # Wait for completion with progress
        print_info("Waiting for generation to complete...")
        start_time = time.time()

        result = job.wait_for_completion(
            timeout=600,
            poll_interval=2,
            progress_callback=progress_callback if show_progress else None
        )

        elapsed = time.time() - start_time

        # Download images
        print_success(f"Generated {len(result.artifacts)} image(s) in {elapsed:.1f}s")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Download each image
        saved_files = []
        for i, artifact in enumerate(result.artifacts):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"image_{timestamp}_{i}.png"
            filepath = output_path / filename

            result.download_image(index=i, save_path=str(filepath))
            saved_files.append(filepath)
            print_success(f"Saved: {filepath}")

        # Show summary
        print()
        print_header("Generation Summary")
        print(f"Images Generated:  {len(result.artifacts)}")
        print(f"Total Time:        {elapsed:.1f}s")
        print(f"Avg Time/Image:    {elapsed/len(result.artifacts):.1f}s")
        print(f"Output Directory:  {output_path.absolute()}")

        return True

    except JobFailedError as e:
        print_error(f"Job failed: {e}")
        if e.error_details:
            print(f"Details: {e.error_details}")
        return False

    except JobTimeoutError:
        print_error("Job timed out after 10 minutes")
        return False

    except ComfyUIClientError as e:
        print_error(f"Client error: {e}")
        return False

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def interactive_mode(client: ComfyUIClient):
    """Interactive mode for image generation"""
    print_header("ComfyUI Image Generator - Interactive Mode")

    while True:
        print("\nOptions:")
        print("  1. Generate an image")
        print("  2. View usage statistics")
        print("  3. Project monthly costs")
        print("  4. Configure GPU type")
        print("  5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == '1':
            # Get parameters
            prompt = input("Enter prompt: ").strip()
            if not prompt:
                print_error("Prompt cannot be empty")
                continue

            try:
                width = int(input("Width [512]: ").strip() or "512")
                height = int(input("Height [512]: ").strip() or "512")
                steps = int(input("Steps [20]: ").strip() or "20")
                num_images = int(input("Number of images [1]: ").strip() or "1")
            except ValueError:
                print_error("Invalid numeric input")
                continue

            generate_image(client, prompt, width, height, steps, num_images)

        elif choice == '2':
            show_stats(client)

        elif choice == '3':
            try:
                images_per_day = int(input("Expected images per day [100]: ").strip() or "100")
                show_monthly_projection(client, images_per_day)
            except ValueError:
                print_error("Invalid numeric input")

        elif choice == '4':
            try:
                pricing = client.get_gpu_pricing()
                print("\nAvailable GPU types:")
                for gpu_type, price in pricing['pricing'].items():
                    marker = " (current)" if gpu_type == pricing['current_gpu'] else ""
                    print(f"  - {gpu_type}: ${price:.2f}/hour{marker}")

                gpu_type = input("\nEnter GPU type: ").strip()
                client.configure_gpu(gpu_type)
                print_success(f"GPU configured to: {gpu_type}")
            except Exception as e:
                print_error(f"Failed to configure GPU: {e}")

        elif choice == '5':
            print_info("Goodbye!")
            break

        else:
            print_error("Invalid option")


def main():
    parser = argparse.ArgumentParser(
        description="ComfyUI Image Generator Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python image_generator.py

  # Generate with specific parameters
  python image_generator.py --prompt "A sunset over mountains" --width 1024 --height 1024

  # View statistics
  python image_generator.py --stats

  # Project monthly costs
  python image_generator.py --project 200
        """
    )

    parser.add_argument('--url', default='http://localhost:8000',
                       help='ComfyUI API URL (default: http://localhost:8000)')
    parser.add_argument('--api-key', help='API key (if authentication enabled)')

    # Generation parameters
    parser.add_argument('--prompt', help='Image generation prompt')
    parser.add_argument('--width', type=int, default=512, help='Image width (default: 512)')
    parser.add_argument('--height', type=int, default=512, help='Image height (default: 512)')
    parser.add_argument('--steps', type=int, default=20, help='Diffusion steps (default: 20)')
    parser.add_argument('--num-images', type=int, default=1, help='Number of images (default: 1)')
    parser.add_argument('--output', default='generated_images', help='Output directory')

    # Modes
    parser.add_argument('--stats', action='store_true', help='Show usage statistics')
    parser.add_argument('--project', type=int, metavar='N',
                       help='Project monthly costs for N images/day')
    parser.add_argument('--no-estimate', action='store_true',
                       help='Skip cost estimation before generating')
    parser.add_argument('--no-progress', action='store_true',
                       help='Disable progress display')

    args = parser.parse_args()

    # Create client
    try:
        client = ComfyUIClient(args.url, api_key=args.api_key)
        print_success(f"Connected to ComfyUI API at {args.url}")
    except Exception as e:
        print_error(f"Failed to connect to API: {e}")
        sys.exit(1)

    # Handle different modes
    if args.stats:
        show_stats(client)
    elif args.project:
        show_monthly_projection(client, args.project)
    elif args.prompt:
        success = generate_image(
            client,
            args.prompt,
            args.width,
            args.height,
            args.steps,
            args.num_images,
            args.output,
            estimate_first=not args.no_estimate,
            show_progress=not args.no_progress
        )
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        interactive_mode(client)


if __name__ == '__main__':
    main()
