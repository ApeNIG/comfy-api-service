"""
Pytest fixtures for integration tests.

Provides:
- HTTP client with API base URL
- Admin API key for authenticated tests
- Helper functions for job lifecycle
"""

import pytest
import asyncio
import httpx
import time
from typing import Optional, Dict, Any


# Configuration
API_BASE_URL = "http://localhost:8000"
ADMIN_API_KEY = None  # Set by setup fixture


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def api_client():
    """HTTP client for API requests."""
    async with httpx.AsyncClient(
        base_url=API_BASE_URL,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        yield client


@pytest.fixture(scope="session")
async def admin_setup(api_client):
    """
    Setup admin user and API key.

    Creates an INTERNAL user and API key for testing.
    Returns the API key for authenticated requests.
    """
    # Create admin user
    user_response = await api_client.post(
        "/admin/users",
        json={
            "email": "test-admin@example.com",
            "role": "internal",
        },
    )

    if user_response.status_code == 400:
        # User already exists, skip creation
        pass
    else:
        assert user_response.status_code == 201, f"Failed to create user: {user_response.text}"

    # Create API key (without auth - assuming auth is disabled for tests)
    key_response = await api_client.post(
        "/admin/api-keys",
        json={
            "user_id": user_response.json().get("user_id", "test-user-id"),
            "name": "Integration Test Key",
            "expires_in_days": 1,
        },
    )

    if key_response.status_code == 201:
        api_key = key_response.json()["api_key"]
        return api_key
    else:
        # If auth endpoints not available, return None
        return None


@pytest.fixture
async def auth_headers(admin_setup):
    """Authentication headers for requests."""
    if admin_setup:
        return {"Authorization": f"Bearer {admin_setup}"}
    return {}


@pytest.fixture
def job_prefix():
    """Unique prefix for test jobs to avoid collisions."""
    return f"test_{int(time.time() * 1000)}"


# Helper functions

async def enqueue_job(
    client: httpx.AsyncClient,
    prompt: str = "A test image",
    headers: Optional[Dict[str, str]] = None,
    idempotency_key: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Enqueue a job and return response.

    Args:
        client: HTTP client
        prompt: Image prompt
        headers: Optional headers (for auth, idempotency)
        idempotency_key: Optional idempotency key
        **kwargs: Additional job parameters

    Returns:
        Response JSON dict
    """
    request_headers = headers or {}
    if idempotency_key:
        request_headers["Idempotency-Key"] = idempotency_key

    payload = {
        "prompt": prompt,
        "model": "dreamshaper_8.safetensors",
        "width": 512,
        "height": 512,
        "num_images": 1,
        "steps": 20,
        **kwargs,
    }

    response = await client.post(
        "/api/v1/jobs",
        json=payload,
        headers=request_headers,
    )

    assert response.status_code in [200, 202], f"Job submission failed: {response.text}"
    return response.json()


async def wait_for_job_status(
    client: httpx.AsyncClient,
    job_id: str,
    target_status: str,
    timeout: float = 60.0,
    poll_interval: float = 0.5,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Poll job status until target status reached or timeout.

    Args:
        client: HTTP client
        job_id: Job ID to poll
        target_status: Target status (succeeded, failed, canceled)
        timeout: Max seconds to wait
        poll_interval: Seconds between polls
        headers: Optional auth headers

    Returns:
        Final job data

    Raises:
        TimeoutError: If timeout reached before target status
    """
    start = time.time()

    while time.time() - start < timeout:
        response = await client.get(
            f"/api/v1/jobs/{job_id}",
            headers=headers or {},
        )

        if response.status_code != 200:
            raise ValueError(f"Failed to get job status: {response.status_code}")

        job_data = response.json()
        current_status = job_data.get("status")

        if current_status == target_status:
            return job_data

        # Check for terminal states
        if target_status not in ["succeeded", "failed", "canceled", "expired"]:
            if current_status in ["succeeded", "failed", "canceled", "expired"]:
                raise ValueError(
                    f"Job reached terminal state {current_status} "
                    f"before target {target_status}"
                )

        await asyncio.sleep(poll_interval)

    raise TimeoutError(
        f"Job {job_id} did not reach status {target_status} "
        f"within {timeout}s (last status: {current_status})"
    )


async def cancel_job(
    client: httpx.AsyncClient,
    job_id: str,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Cancel a job.

    Args:
        client: HTTP client
        job_id: Job ID to cancel
        headers: Optional auth headers

    Returns:
        Response JSON
    """
    response = await client.delete(
        f"/api/v1/jobs/{job_id}",
        headers=headers or {},
    )

    assert response.status_code in [200, 202], f"Cancel failed: {response.text}"
    return response.json()


@pytest.fixture
async def helpers(api_client, auth_headers):
    """
    Helper functions bound to client and auth.

    Usage:
        async def test_something(helpers):
            job = await helpers.enqueue("test prompt")
            result = await helpers.wait_for("succeeded", job["job_id"])
    """

    class Helpers:
        async def enqueue(self, prompt="Test image", **kwargs):
            return await enqueue_job(api_client, prompt, auth_headers, **kwargs)

        async def wait_for(self, status, job_id, timeout=60):
            return await wait_for_job_status(
                api_client, job_id, status, timeout, headers=auth_headers
            )

        async def cancel(self, job_id):
            return await cancel_job(api_client, job_id, auth_headers)

        async def get_job(self, job_id):
            response = await api_client.get(
                f"/api/v1/jobs/{job_id}",
                headers=auth_headers,
            )
            return response.json()

    return Helpers()
