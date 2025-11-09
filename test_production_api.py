#!/usr/bin/env python3
"""
Test Production API from Local Machine

This script tests the deployed ComfyUI API on your DigitalOcean server.
Run this from your LOCAL machine, not from the server.

Usage:
    python test_production_api.py
"""

import requests
import json

# Your production API URL
API_URL = "http://167.71.137.165:8000"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"{title:^60}")
    print(f"{'='*60}\n")

def test_health():
    """Test if API is accessible"""
    print_section("1. Health Check")
    try:
        response = requests.get(f"{API_URL}/health", timeout=10)
        if response.status_code == 200:
            health = response.json()
            print(f"✓ API is reachable!")
            print(f"  Status: {health.get('status', 'unknown')}")
            print(f"  Redis: {health.get('redis_status', 'unknown')}")
            print(f"  MinIO: {health.get('minio_status', 'unknown')}")
            return True
        else:
            print(f"✗ Health check failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot reach API: {e}")
        return False

def test_stats():
    """Test monitoring stats endpoint"""
    print_section("2. Monitoring Stats")
    try:
        response = requests.get(f"{API_URL}/api/v1/monitoring/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Monitoring endpoint working!")
            print(f"  Total Jobs: {stats.get('total_jobs', 0)}")
            print(f"  Successful: {stats.get('successful_jobs', 0)}")
            print(f"  Failed: {stats.get('failed_jobs', 0)}")
            print(f"  Images Generated: {stats.get('total_images_generated', 0)}")
            return True
        else:
            print(f"✗ Stats failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot get stats: {e}")
        return False

def test_cost_estimation():
    """Test cost estimation"""
    print_section("3. Cost Estimation")
    try:
        response = requests.post(
            f"{API_URL}/api/v1/monitoring/estimate-cost",
            params={
                "width": 512,
                "height": 512,
                "steps": 20,
                "num_images": 1
            },
            timeout=10
        )
        if response.status_code == 200:
            cost = response.json()
            print(f"✓ Cost estimation working!")
            print(f"  GPU Type: {cost.get('gpu_type', 'unknown')}")
            print(f"  Estimated Time: {cost.get('estimated_time_seconds', 0)}s")
            print(f"  Cost per Image: ${cost.get('cost_per_image', 0):.6f}")
            return True
        else:
            print(f"✗ Cost estimation failed: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot estimate cost: {e}")
        return False

def test_with_api_key():
    """Test with API key (optional)"""
    print_section("4. Test with API Key (Optional)")
    print("If you have an API key, test it with:")
    print(f"  curl -H 'X-API-Key: YOUR_KEY' {API_URL}/api/v1/monitoring/stats")
    print("\nNote: AUTH_ENABLED is currently false, so API key is not required.")

if __name__ == '__main__':
    print_section("Production API Test")
    print(f"Testing API at: {API_URL}")
    print(f"\nMake sure:")
    print(f"  1. Your DigitalOcean firewall allows port 8000")
    print(f"  2. UFW on server allows port 8000: sudo ufw allow 8000/tcp")

    # Run tests
    tests_passed = 0
    tests_total = 3

    if test_health():
        tests_passed += 1

    if test_stats():
        tests_passed += 1

    if test_cost_estimation():
        tests_passed += 1

    test_with_api_key()

    # Summary
    print_section("Summary")
    print(f"Tests passed: {tests_passed}/{tests_total}")

    if tests_passed == tests_total:
        print("\n✓ All tests passed! Your API is accessible from the internet!")
        print("\nNext steps:")
        print("  1. Install SDK: cd sdk/python && pip install -e .")
        print("  2. Generate images: python demo/image_generator.py \\")
        print(f"       --url {API_URL} \\")
        print("       --prompt 'A beautiful landscape'")
    else:
        print("\n✗ Some tests failed. Common issues:")
        print("  1. Firewall blocking port 8000")
        print("  2. Docker containers not running")
        print("  3. Server is down")
        print("\nTroubleshooting:")
        print("  - On server: docker compose ps")
        print("  - On server: sudo ufw allow 8000/tcp")
        print("  - On server: docker compose logs api")
