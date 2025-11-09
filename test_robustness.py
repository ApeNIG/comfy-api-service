#!/usr/bin/env python3
"""
Robustness Testing Suite for ComfyUI API Service
Tests error handling, edge cases, and system resilience
"""

import requests
import json
import time
import concurrent.futures
from typing import List, Dict, Any

API_URL = "http://comfyui-api:8000"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name: str):
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}TEST: {name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}")

def print_pass(msg: str):
    print(f"{Colors.GREEN}✓ PASS:{Colors.END} {msg}")

def print_fail(msg: str):
    print(f"{Colors.RED}✗ FAIL:{Colors.END} {msg}")

def print_warn(msg: str):
    print(f"{Colors.YELLOW}⚠ WARN:{Colors.END} {msg}")

def test_health_checks():
    """Test all health check endpoints"""
    print_test("Health Check Endpoints")

    tests_passed = 0
    tests_total = 3

    # Test 1: Liveness
    try:
        resp = requests.get(f"{API_URL}/healthz", timeout=5)
        if resp.status_code == 200 and resp.json().get('status') == 'alive':
            print_pass("Liveness check responds correctly")
            tests_passed += 1
        else:
            print_fail(f"Liveness check failed: {resp.status_code}")
    except Exception as e:
        print_fail(f"Liveness check exception: {e}")

    # Test 2: Readiness
    try:
        resp = requests.get(f"{API_URL}/readyz", timeout=5)
        if resp.status_code in [200, 503]:  # Either ready or not ready is valid
            print_pass(f"Readiness check responds (status: {resp.status_code})")
            tests_passed += 1
        else:
            print_fail(f"Readiness check unexpected status: {resp.status_code}")
    except Exception as e:
        print_fail(f"Readiness check exception: {e}")

    # Test 3: Full health
    try:
        resp = requests.get(f"{API_URL}/health", timeout=10)
        if resp.status_code == 200:
            health = resp.json()
            comfyui_status = health.get('comfyui_status')
            print_pass(f"Health check OK - ComfyUI: {comfyui_status}")
            tests_passed += 1
        else:
            print_fail(f"Health check failed: {resp.status_code}")
    except Exception as e:
        print_fail(f"Health check exception: {e}")

    return tests_passed, tests_total

def test_invalid_inputs():
    """Test API error handling with invalid inputs"""
    print_test("Invalid Input Handling")

    tests_passed = 0
    tests_total = 5

    # Test 1: Missing required fields
    try:
        resp = requests.post(f"{API_URL}/api/v1/generate/", json={}, timeout=5)
        if resp.status_code in [400, 422]:
            print_pass(f"Rejects empty payload (HTTP {resp.status_code})")
            tests_passed += 1
        else:
            print_fail(f"Should reject empty payload, got: {resp.status_code}")
    except Exception as e:
        print_fail(f"Empty payload test exception: {e}")

    # Test 2: Invalid dimensions (not divisible by 8)
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/generate/",
            json={"prompt": "test", "width": 513, "height": 513},
            timeout=5
        )
        if resp.status_code in [400, 422]:
            print_pass(f"Rejects invalid dimensions (HTTP {resp.status_code})")
            tests_passed += 1
        else:
            print_warn(f"Dimensions validation may be permissive: {resp.status_code}")
            tests_passed += 0.5
    except Exception as e:
        print_fail(f"Invalid dimensions test exception: {e}")

    # Test 3: Negative steps
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/generate/",
            json={"prompt": "test", "steps": -10},
            timeout=5
        )
        if resp.status_code in [400, 422]:
            print_pass(f"Rejects negative steps (HTTP {resp.status_code})")
            tests_passed += 1
        else:
            print_fail(f"Should reject negative steps, got: {resp.status_code}")
    except Exception as e:
        print_fail(f"Negative steps test exception: {e}")

    # Test 4: Extremely large dimensions
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/generate/",
            json={"prompt": "test", "width": 10000, "height": 10000},
            timeout=5
        )
        if resp.status_code in [400, 422]:
            print_pass(f"Rejects oversized dimensions (HTTP {resp.status_code})")
            tests_passed += 1
        else:
            print_warn(f"Large dimensions accepted: {resp.status_code}")
            tests_passed += 0.5
    except Exception as e:
        print_fail(f"Large dimensions test exception: {e}")

    # Test 5: Invalid prompt type
    try:
        resp = requests.post(
            f"{API_URL}/api/v1/generate/",
            json={"prompt": 12345},  # Should be string
            timeout=5
        )
        if resp.status_code in [400, 422]:
            print_pass(f"Rejects invalid prompt type (HTTP {resp.status_code})")
            tests_passed += 1
        else:
            print_fail(f"Should reject non-string prompt, got: {resp.status_code}")
    except Exception as e:
        print_fail(f"Invalid prompt type test exception: {e}")

    return tests_passed, tests_total

def test_concurrent_requests():
    """Test system under concurrent load"""
    print_test("Concurrent Request Handling")

    num_requests = 5
    payload = {
        "prompt": "A simple test image",
        "width": 512,
        "height": 512,
        "steps": 5  # Reduced for faster testing
    }

    def make_request(i: int) -> Dict[str, Any]:
        try:
            start = time.time()
            resp = requests.post(
                f"{API_URL}/api/v1/jobs",
                json=payload,
                headers={"Idempotency-Key": f"concurrent-test-{i}-{int(time.time())}"},
                timeout=10
            )
            elapsed = time.time() - start
            return {
                "id": i,
                "status": resp.status_code,
                "time": elapsed,
                "success": resp.status_code in [200, 202]
            }
        except Exception as e:
            return {
                "id": i,
                "status": 0,
                "time": 0,
                "success": False,
                "error": str(e)
            }

    print(f"Submitting {num_requests} concurrent requests...")
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
        results = list(executor.map(make_request, range(num_requests)))

    total_time = time.time() - start_time

    successful = sum(1 for r in results if r['success'])
    avg_time = sum(r['time'] for r in results if r['success']) / max(successful, 1)

    print(f"\nResults:")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Successful: {successful}/{num_requests}")
    print(f"  Average response time: {avg_time:.3f}s")

    if successful == num_requests:
        print_pass(f"All {num_requests} concurrent requests succeeded")
        return 1, 1
    elif successful >= num_requests * 0.8:
        print_warn(f"Most requests succeeded ({successful}/{num_requests})")
        return 0.8, 1
    else:
        print_fail(f"Too many failures ({num_requests - successful} failed)")
        return 0, 1

def test_idempotency():
    """Test idempotency key handling"""
    print_test("Idempotency Key Handling")

    tests_passed = 0
    tests_total = 2

    payload = {
        "prompt": "Idempotency test",
        "width": 512,
        "height": 512,
        "steps": 5
    }

    idempotency_key = f"idempotency-test-{int(time.time())}"

    # Test 1: Submit same request twice with same key
    try:
        resp1 = requests.post(
            f"{API_URL}/api/v1/jobs",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
            timeout=10
        )

        time.sleep(0.5)

        resp2 = requests.post(
            f"{API_URL}/api/v1/jobs",
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
            timeout=10
        )

        if resp1.status_code in [200, 202] and resp2.status_code in [200, 202]:
            job_id_1 = resp1.json().get('job_id')
            job_id_2 = resp2.json().get('job_id')

            if job_id_1 == job_id_2:
                print_pass(f"Idempotency works - same job ID returned: {job_id_1}")
                tests_passed += 1
            else:
                print_warn(f"Different job IDs: {job_id_1} vs {job_id_2}")
        else:
            print_fail(f"Request failed: {resp1.status_code}, {resp2.status_code}")
    except Exception as e:
        print_fail(f"Idempotency test exception: {e}")

    # Test 2: Different key should create new job
    try:
        resp3 = requests.post(
            f"{API_URL}/api/v1/jobs",
            json=payload,
            headers={"Idempotency-Key": f"{idempotency_key}-different"},
            timeout=10
        )

        if resp3.status_code in [200, 202]:
            job_id_3 = resp3.json().get('job_id')
            if job_id_3 != job_id_1:
                print_pass(f"Different key creates new job: {job_id_3}")
                tests_passed += 1
            else:
                print_fail("Same job ID with different key")
        else:
            print_fail(f"Request failed: {resp3.status_code}")
    except Exception as e:
        print_fail(f"Different key test exception: {e}")

    return tests_passed, tests_total

def test_error_recovery():
    """Test system recovery from errors"""
    print_test("Error Recovery & Resilience")

    tests_passed = 0
    tests_total = 2

    # Test 1: System recovers after invalid request
    try:
        # Send invalid request
        resp_bad = requests.post(
            f"{API_URL}/api/v1/generate/",
            json={"invalid": "data"},
            timeout=5
        )

        # Send valid request immediately after
        resp_good = requests.post(
            f"{API_URL}/api/v1/generate/",
            json={
                "prompt": "Recovery test",
                "width": 512,
                "height": 512,
                "steps": 5
            },
            timeout=60
        )

        if resp_good.status_code in [200, 201]:
            print_pass("System recovers from invalid request")
            tests_passed += 1
        else:
            print_fail(f"System didn't recover: {resp_good.status_code}")
    except Exception as e:
        print_fail(f"Recovery test exception: {e}")

    # Test 2: Health check still works after errors
    try:
        resp = requests.get(f"{API_URL}/health", timeout=10)
        if resp.status_code == 200:
            print_pass("Health check works after error conditions")
            tests_passed += 1
        else:
            print_fail(f"Health check degraded: {resp.status_code}")
    except Exception as e:
        print_fail(f"Health check exception: {e}")

    return tests_passed, tests_total

def test_timeout_handling():
    """Test timeout configuration"""
    print_test("Timeout Handling")

    # Test: Very quick timeout on client side
    try:
        start = time.time()
        try:
            resp = requests.post(
                f"{API_URL}/api/v1/generate/",
                json={
                    "prompt": "Timeout test",
                    "width": 512,
                    "height": 512,
                    "steps": 50  # More steps to potentially take longer
                },
                timeout=0.1  # Very short timeout
            )
            print_warn("Request completed faster than timeout")
        except requests.Timeout:
            elapsed = time.time() - start
            print_pass(f"Client timeout triggered correctly after {elapsed:.2f}s")
            return 1, 1
    except Exception as e:
        print_fail(f"Timeout test exception: {e}")
        return 0, 1

    return 0.5, 1

def main():
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}ComfyUI API Service - Robustness Test Suite{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}")

    total_passed = 0
    total_tests = 0

    # Run all test suites
    test_suites = [
        ("Health Checks", test_health_checks),
        ("Invalid Input Handling", test_invalid_inputs),
        ("Concurrent Requests", test_concurrent_requests),
        ("Idempotency", test_idempotency),
        ("Error Recovery", test_error_recovery),
        ("Timeout Handling", test_timeout_handling),
    ]

    results = []

    for suite_name, test_func in test_suites:
        try:
            passed, total = test_func()
            total_passed += passed
            total_tests += total
            results.append((suite_name, passed, total))
        except Exception as e:
            print_fail(f"Test suite '{suite_name}' crashed: {e}")
            results.append((suite_name, 0, 1))
            total_tests += 1

    # Summary
    print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BLUE}SUMMARY{Colors.END}")
    print(f"{Colors.BLUE}{'='*80}{Colors.END}\n")

    for suite_name, passed, total in results:
        percentage = (passed / total * 100) if total > 0 else 0
        color = Colors.GREEN if percentage == 100 else Colors.YELLOW if percentage >= 80 else Colors.RED
        print(f"{suite_name:.<40} {color}{passed:.1f}/{total} ({percentage:.0f}%){Colors.END}")

    overall_percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0

    print(f"\n{'Overall Score':.<40} {total_passed:.1f}/{total_tests} ({overall_percentage:.0f}%)")

    if overall_percentage >= 90:
        print(f"\n{Colors.GREEN}✓ ROBUST - System is highly resilient{Colors.END}")
    elif overall_percentage >= 75:
        print(f"\n{Colors.YELLOW}⚠ MODERATE - System is fairly robust with some issues{Colors.END}")
    else:
        print(f"\n{Colors.RED}✗ WEAK - System needs robustness improvements{Colors.END}")

    print()

if __name__ == "__main__":
    main()
