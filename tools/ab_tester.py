#!/usr/bin/env python3
"""
A/B Testing Tool for ComfyUI Image Generation

Compare different generation settings to find the optimal balance
between quality and cost.

Features:
- Test multiple parameter combinations
- Compare costs across settings
- Generate side-by-side comparisons
- Find cost-effective "sweet spots"
- Save detailed comparison reports
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

try:
    from comfyui_client import ComfyUIClient
    from comfyui_client.exceptions import ComfyUIClientError
except ImportError:
    print("Error: comfyui_client not installed.")
    print("Install it with: cd sdk/python && pip install -e .")
    sys.exit(1)


@dataclass
class TestConfig:
    """Configuration for a single test"""
    name: str
    width: int
    height: int
    steps: int
    description: str = ""


@dataclass
class TestResult:
    """Results from a single test"""
    config: TestConfig
    estimated_cost: float
    actual_cost: float
    generation_time: float
    image_path: Optional[str]
    job_id: str
    success: bool
    error: Optional[str] = None


class Colors:
    """ANSI color codes"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class ABTester:
    """A/B Testing tool for image generation"""
    
    def __init__(self, client: ComfyUIClient, output_dir: str = "ab_tests"):
        self.client = client
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TestResult] = []
    
    def print_header(self, text: str):
        """Print colored header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.HEADER}{text:^70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}\n")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓{Colors.END} {text}")
    
    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.RED}✗{Colors.END} {text}")
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.CYAN}ℹ{Colors.END} {text}")
    
    def estimate_all_costs(self, configs: List[TestConfig], prompt: str) -> Dict:
        """Estimate costs for all configurations"""
        self.print_header("Cost Estimation Summary")
        
        estimates = []
        total_cost = 0
        
        for config in configs:
            cost_info = self.client.estimate_cost(
                config.width,
                config.height,
                config.steps,
                num_images=1
            )
            
            estimates.append({
                'config': config,
                'cost': cost_info['estimated_cost_usd'],
                'time': cost_info['estimated_time_seconds']
            })
            total_cost += cost_info['estimated_cost_usd']
            
            print(f"{Colors.BOLD}{config.name:20s}{Colors.END}")
            print(f"  Size:      {config.width}x{config.height}")
            print(f"  Steps:     {config.steps}")
            print(f"  Est. Cost: ${cost_info['estimated_cost_usd']:.6f}")
            print(f"  Est. Time: {cost_info['estimated_time_seconds']}s")
            if config.description:
                print(f"  Note:      {config.description}")
            print()
        
        print(f"{Colors.BOLD}Total Estimated Cost: ${total_cost:.6f}{Colors.END}")
        print(f"{Colors.BOLD}Number of Tests:      {len(configs)}{Colors.END}\n")
        
        return {
            'estimates': estimates,
            'total_cost': total_cost,
            'prompt': prompt
        }
    
    def run_test(self, config: TestConfig, prompt: str, test_num: int, total_tests: int) -> TestResult:
        """Run a single test"""
        self.print_header(f"Test {test_num}/{total_tests}: {config.name}")
        
        print(f"Configuration:")
        print(f"  Size:   {config.width}x{config.height}")
        print(f"  Steps:  {config.steps}")
        print(f"  Prompt: {prompt}")
        print()
        
        try:
            # Estimate cost first
            cost_info = self.client.estimate_cost(
                config.width,
                config.height,
                config.steps
            )
            estimated_cost = cost_info['estimated_cost_usd']
            
            self.print_info(f"Estimated cost: ${estimated_cost:.6f}")
            
            # Generate image
            start_time = time.time()
            job = self.client.generate(
                prompt=prompt,
                width=config.width,
                height=config.height,
                steps=config.steps,
                num_images=1
            )
            
            self.print_info(f"Job submitted: {job.job_id}")
            
            # Wait for completion
            result = job.wait_for_completion(timeout=600)
            generation_time = time.time() - start_time
            
            # Download image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{config.name.replace(' ', '_')}_{timestamp}.png"
            filepath = self.output_dir / filename
            
            result.download_image(0, str(filepath))
            
            # Calculate actual cost (approximate based on time)
            actual_cost = estimated_cost  # For now, use estimate
            
            self.print_success(f"Generated in {generation_time:.1f}s")
            self.print_success(f"Saved to: {filepath}")
            
            return TestResult(
                config=config,
                estimated_cost=estimated_cost,
                actual_cost=actual_cost,
                generation_time=generation_time,
                image_path=str(filepath),
                job_id=job.job_id,
                success=True
            )
            
        except Exception as e:
            self.print_error(f"Test failed: {e}")
            
            return TestResult(
                config=config,
                estimated_cost=0,
                actual_cost=0,
                generation_time=0,
                image_path=None,
                job_id="",
                success=False,
                error=str(e)
            )
    
    def run_ab_test(self, configs: List[TestConfig], prompt: str, skip_confirmation: bool = False):
        """Run A/B test with multiple configurations"""
        # Show cost estimates
        summary = self.estimate_all_costs(configs, prompt)
        
        # Ask for confirmation unless skipped
        if not skip_confirmation:
            response = input(f"\n{Colors.YELLOW}Proceed with {len(configs)} tests? Total cost: ${summary['total_cost']:.6f} (y/n): {Colors.END}").strip().lower()
            if response != 'y':
                self.print_info("Test cancelled")
                return
        
        # Run all tests
        self.print_header(f"Running {len(configs)} Tests")
        
        for i, config in enumerate(configs, 1):
            result = self.run_test(config, prompt, i, len(configs))
            self.results.append(result)
            
            # Small delay between tests
            if i < len(configs):
                time.sleep(1)
        
        # Generate report
        self.generate_report(prompt)
    
    def generate_report(self, prompt: str):
        """Generate comparison report"""
        self.print_header("A/B Test Results")
        
        # Summary table
        print(f"{'Config':<20} {'Size':<12} {'Steps':<6} {'Time':<8} {'Cost':<12} {'Status':<10}")
        print("-" * 80)
        
        successful_results = [r for r in self.results if r.success]
        
        for result in self.results:
            config = result.config
            size_str = f"{config.width}x{config.height}"
            time_str = f"{result.generation_time:.1f}s" if result.success else "N/A"
            cost_str = f"${result.estimated_cost:.6f}" if result.success else "N/A"
            status = f"{Colors.GREEN}✓ Success{Colors.END}" if result.success else f"{Colors.RED}✗ Failed{Colors.END}"
            
            print(f"{config.name:<20} {size_str:<12} {config.steps:<6} {time_str:<8} {cost_str:<12} {status}")
        
        print()
        
        # Cost analysis
        if successful_results:
            self.print_header("Cost Analysis")
            
            # Sort by cost
            by_cost = sorted(successful_results, key=lambda r: r.estimated_cost)
            cheapest = by_cost[0]
            most_expensive = by_cost[-1]
            
            print(f"{Colors.GREEN}Most Cost-Effective:{Colors.END}")
            print(f"  {cheapest.config.name}")
            print(f"  Size: {cheapest.config.width}x{cheapest.config.height}")
            print(f"  Steps: {cheapest.config.steps}")
            print(f"  Cost: ${cheapest.estimated_cost:.6f}")
            print(f"  Time: {cheapest.generation_time:.1f}s")
            print()
            
            print(f"{Colors.YELLOW}Most Expensive:{Colors.END}")
            print(f"  {most_expensive.config.name}")
            print(f"  Size: {most_expensive.config.width}x{most_expensive.config.height}")
            print(f"  Steps: {most_expensive.config.steps}")
            print(f"  Cost: ${most_expensive.estimated_cost:.6f}")
            print(f"  Time: {most_expensive.generation_time:.1f}s")
            print()
            
            # Cost per pixel analysis
            print(f"{Colors.CYAN}Cost Efficiency (cost per megapixel):{Colors.END}")
            efficiency = []
            for result in successful_results:
                pixels = (result.config.width * result.config.height) / 1_000_000
                cost_per_mp = result.estimated_cost / pixels
                efficiency.append((result.config.name, cost_per_mp, pixels))
            
            efficiency.sort(key=lambda x: x[1])
            for name, cost_per_mp, mp in efficiency:
                print(f"  {name:<20} ${cost_per_mp:.6f}/MP ({mp:.2f} MP)")
            print()
        
        # Save JSON report
        report_path = self.output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'prompt': prompt,
            'timestamp': datetime.now().isoformat(),
            'results': [
                {
                    'config': asdict(r.config),
                    'estimated_cost': r.estimated_cost,
                    'generation_time': r.generation_time,
                    'image_path': r.image_path,
                    'success': r.success,
                    'error': r.error
                }
                for r in self.results
            ]
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        self.print_success(f"Report saved to: {report_path}")
        
        # Show where images are
        if successful_results:
            print(f"\n{Colors.CYAN}Generated images saved to:{Colors.END} {self.output_dir.absolute()}")
            print(f"\n{Colors.BOLD}Next steps:{Colors.END}")
            print("  1. Review the images to compare quality")
            print("  2. Check the cost analysis above")
            print("  3. Choose the best balance of quality and cost")


def main():
    parser = argparse.ArgumentParser(
        description="A/B Testing Tool for ComfyUI Image Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick quality comparison
  python ab_tester.py --preset quality --prompt "A sunset over mountains"
  
  # Size comparison
  python ab_tester.py --preset sizes --prompt "Abstract art"
  
  # Custom test
  python ab_tester.py --custom "512x512x20,1024x1024x30" --prompt "A cat"
  
  # Performance comparison
  python ab_tester.py --preset performance --prompt "Futuristic city"
        """
    )
    
    parser.add_argument('--url', default='http://localhost:8000',
                       help='ComfyUI API URL')
    parser.add_argument('--api-key', help='API key (if authentication enabled)')
    parser.add_argument('--prompt', required=True, help='Image generation prompt')
    parser.add_argument('--output', default='ab_tests', help='Output directory')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompts')
    
    # Preset test configurations
    parser.add_argument('--preset', choices=['quality', 'sizes', 'performance', 'all'],
                       help='Use preset test configurations')
    
    # Custom configuration
    parser.add_argument('--custom', help='Custom configs: "WxHxSteps,WxHxSteps,..."')
    
    args = parser.parse_args()
    
    # Create client
    try:
        client = ComfyUIClient(args.url, api_key=args.api_key)
        print(f"{Colors.GREEN}✓{Colors.END} Connected to ComfyUI API at {args.url}\n")
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.END} Failed to connect: {e}")
        sys.exit(1)
    
    # Define test configurations
    configs = []
    
    if args.preset == 'quality':
        configs = [
            TestConfig("Low Quality", 512, 512, 15, "Fast, low quality"),
            TestConfig("Standard Quality", 512, 512, 20, "Balanced"),
            TestConfig("High Quality", 512, 512, 30, "Better quality"),
            TestConfig("Very High Quality", 512, 512, 50, "Best quality, slower"),
        ]
    
    elif args.preset == 'sizes':
        configs = [
            TestConfig("Small (512x512)", 512, 512, 20, "Standard square"),
            TestConfig("Medium (768x768)", 768, 768, 20, "Larger square"),
            TestConfig("Large (1024x1024)", 1024, 1024, 20, "High resolution"),
            TestConfig("Portrait (512x768)", 512, 768, 20, "Vertical"),
            TestConfig("Landscape (768x512)", 768, 512, 20, "Horizontal"),
        ]
    
    elif args.preset == 'performance':
        configs = [
            TestConfig("Ultra Fast", 512, 512, 10, "Fastest, lowest quality"),
            TestConfig("Fast", 512, 512, 15, "Quick generation"),
            TestConfig("Balanced", 512, 512, 20, "Good balance"),
            TestConfig("Slow", 512, 512, 30, "Better quality"),
        ]
    
    elif args.preset == 'all':
        configs = [
            TestConfig("Tiny Fast", 512, 512, 10, "Cheapest option"),
            TestConfig("Small Standard", 512, 512, 20, "Standard quality"),
            TestConfig("Medium Standard", 768, 768, 20, "Medium size"),
            TestConfig("Large Standard", 1024, 1024, 20, "Large size"),
            TestConfig("Small High-Q", 512, 512, 40, "Small but high quality"),
            TestConfig("Large High-Q", 1024, 1024, 40, "Large and high quality"),
        ]
    
    elif args.custom:
        # Parse custom configuration
        for i, config_str in enumerate(args.custom.split(','), 1):
            try:
                w, h, s = map(int, config_str.split('x'))
                configs.append(TestConfig(f"Custom {i}", w, h, s, f"{w}x{h} @ {s} steps"))
            except:
                print(f"{Colors.RED}✗{Colors.END} Invalid custom config: {config_str}")
                print("  Format: WIDTHxHEIGHTxSTEPS (e.g., 512x512x20)")
                sys.exit(1)
    
    else:
        print(f"{Colors.RED}✗{Colors.END} Please specify --preset or --custom")
        sys.exit(1)
    
    # Run A/B test
    tester = ABTester(client, args.output)
    tester.run_ab_test(configs, args.prompt, skip_confirmation=args.yes)


if __name__ == '__main__':
    main()
