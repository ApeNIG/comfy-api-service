# Sprint 2: Trust and Fairness Layer

**Based on expert production feedback**

**Started:** 2025-11-06
**Goal:** Make the service "safe for strangers" - who gets to burn GPU cycles and how much?

---

## Overview

Sprint 2 transforms our distributed compute service from "it works" to "it's safe for multi-tenant production use."

**Core Problem:** Right now, anyone can submit unlimited jobs and burn unlimited GPU time. We need:
1. **Identity** (who are you?)
2. **Fairness** (how much can you take?)
3. **Resilience** (what if things break?)
4. **Confidence** (does it actually work?)
5. **Visibility** (what's happening?)

---

## Week 1: Trust Layer

### 1. API Key Authentication ⭐

**Priority:** HIGHEST (gates everything else)

**Design Decision:** Start with API keys (not JWT)
- Simpler to implement and rotate
- Easier for users (just a header)
- Can upgrade to JWT later without breaking changes

**Redis Schema:**
```
cui:apikey:{key_hash}  → HASH {
    user_id: int,
    role: str,          # free, pro, internal
    created_at: timestamp,
    last_used_at: timestamp,
    is_active: bool,
    name: str           # optional label
}

cui:user:{id}  → HASH {
    user_id: int,
    email: str,
    role: str,
    quota_daily: int,        # max jobs per day
    quota_concurrent: int,   # max concurrent jobs
    created_at: timestamp
}

cui:user_email:{email} → user_id  # Email lookup index
```

**Roles & Quotas:**
```python
ROLES = {
    "free": {
        "quota_daily": 10,
        "quota_concurrent": 1,
        "rate_limit_per_minute": 5
    },
    "pro": {
        "quota_daily": 100,
        "quota_concurrent": 3,
        "rate_limit_per_minute": 20
    },
    "internal": {
        "quota_daily": -1,      # unlimited
        "quota_concurrent": 10,
        "rate_limit_per_minute": -1  # unlimited
    }
}
```

**Implementation:**

**Files to create:**
- `apps/api/models/auth.py` - User, APIKey, Role models
- `apps/api/services/auth_service.py` - Key validation, user lookup
- `apps/api/middleware/auth.py` - Extract & validate API key
- `apps/api/routers/admin.py` - Key management endpoints (internal only)

**Auth Flow:**
```
Request with X-API-Key header
    ↓
Middleware extracts key
    ↓
Hash key with SHA256
    ↓
Redis lookup: cui:apikey:{hash}
    ↓ (not found)
401 Unauthorized
    ↓ (found, is_active=false)
401 Unauthorized (revoked)
    ↓ (found, is_active=true)
Load user from cui:user:{user_id}
    ↓
Attach to request.state.user
    ↓
Update last_used_at (async, no await)
    ↓
Continue to endpoint
```

**Endpoints:**
```
POST   /api/v1/admin/users         Create user (email, role)
POST   /api/v1/admin/apikeys       Create API key for user
GET    /api/v1/admin/apikeys       List keys (with filters)
DELETE /api/v1/admin/apikeys/{id}  Revoke key
GET    /api/v1/auth/me             Get current user info
```

**Security:**
- Store hashed keys (SHA256) in Redis, not plaintext
- Return plaintext key ONLY on creation (user must save it)
- Admin endpoints require `role=internal` key
- Keys are 32-byte random (base64 encoded = 44 chars)

---

### 2. Rate Limiting with Token Bucket ⭐

**Priority:** HIGH (prevents abuse)

**Pattern:** Redis token bucket per key per window

**Algorithm:**
```python
key = f"cui:rl:{api_key_hash}:{endpoint}:{window}"
current = await redis.incr(key)
if current == 1:
    await redis.expire(key, window_seconds)

if current > limit:
    reset_time = await redis.ttl(key) + time.now()
    raise HTTPException(
        status_code=429,
        headers={
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_time),
            "Retry-After": str(await redis.ttl(key))
        }
    )

remaining = max(0, limit - current)
```

**Headers (Industry Standard):**
```
X-RateLimit-Limit: 20          # Max requests in window
X-RateLimit-Remaining: 15      # Requests left
X-RateLimit-Reset: 1699372800  # Unix timestamp when window resets
Retry-After: 42                # Seconds to wait (only on 429)
```

**Rate Limits by Role:**
```python
RATE_LIMITS = {
    "POST /api/v1/jobs": {
        "free": 5,    # 5 per minute
        "pro": 20,    # 20 per minute
        "internal": -1  # unlimited
    },
    "GET /api/v1/jobs/{id}": {
        "free": 30,
        "pro": 100,
        "internal": -1
    }
}
```

**Implementation:**

**Files to create:**
- `apps/api/services/rate_limiter.py` - Token bucket logic
- `apps/api/middleware/rate_limit.py` - Rate limit middleware

**Middleware Flow:**
```
Request arrives
    ↓
Auth middleware runs (sets request.state.user)
    ↓
Rate limit middleware checks
    ↓
Get user role and endpoint
    ↓
Lookup limit for (role, endpoint)
    ↓
Check Redis token bucket
    ↓ (over limit)
Return 429 with headers
    ↓ (within limit)
Add rate limit headers to response
    ↓
Continue
```

**Edge Cases:**
- Unauthenticated requests: use IP-based rate limiting (strict)
- Internal keys: skip rate limiting
- WebSocket: no rate limiting (stateful connection)

---

## Week 2: Resilience Layer

### 3. Crash Recovery Loop ⭐

**Priority:** CRITICAL (prevents zombie jobs)

**Problem:** If worker crashes mid-job, job stays in `running` state forever.

**Solution:** On worker startup, scan for stale jobs.

**Implementation:**

**Add to `apps/worker/main.py`:**
```python
async def startup(ctx):
    await redis_client.connect()
    logger.info("Worker started, checking for stale jobs...")

    # Reconcile stale jobs
    in_progress = await redis_client.get_in_progress_jobs()

    recovered = 0
    for job_id in in_progress:
        try:
            job = await redis_client.get_job(job_id)

            if not job:
                # Job data missing but in-progress flag exists
                await redis_client.unmark_job_in_progress(job_id)
                logger.warning(f"Cleaned up orphaned in-progress flag: {job_id}")
                continue

            if job["status"] != "running":
                # Job finished but flag not cleared
                await redis_client.unmark_job_in_progress(job_id)
                logger.info(f"Cleaned up stale flag for finished job: {job_id}")
                continue

            # Job is marked running, check if stale
            started_at = datetime.fromisoformat(job["started_at"])
            age = datetime.now(timezone.utc) - started_at

            if age > timedelta(seconds=settings.job_timeout + 60):  # +60s grace period
                # Job is stale, mark as failed
                await redis_client.update_job_status(
                    job_id,
                    "failed",
                    error={
                        "message": "Job timeout - worker may have crashed",
                        "age_seconds": int(age.total_seconds()),
                        "timeout": settings.job_timeout
                    }
                )
                await redis_client.unmark_job_in_progress(job_id)
                await redis_client.increment_metric("jobs_recovered", {"status": "failed"})

                logger.warning(f"Recovered stale job: {job_id} (age: {age})")
                recovered += 1

        except Exception as e:
            logger.error(f"Failed to recover job {job_id}: {e}")

    logger.info(f"Crash recovery complete: {recovered} jobs recovered")
```

**Metrics:**
```python
jobs_recovered_total{status}  # failed, requeued
```

**Testing:**
1. Start worker
2. Submit job
3. Kill worker mid-processing (kill -9)
4. Start new worker
5. Verify job marked failed

---

### 4. Integration Tests with Docker Compose

**Priority:** HIGH (confidence)

**Setup:**

**Create `docker-compose.test.yml`:**
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  minio:
    image: quay.io/minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio:9000
      JOBS_ENABLED: "true"
    depends_on:
      redis:
        condition: service_healthy
      minio:
        condition: service_healthy
    command: uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

  worker:
    build: .
    environment:
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio:9000
    depends_on:
      - redis
      - minio
      - api
    command: arq apps.worker.main.WorkerSettings
```

**Create `tests/integration/`:**

**`tests/integration/conftest.py`:**
```python
import pytest
import httpx
from typing import AsyncGenerator

@pytest.fixture
async def api_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client

@pytest.fixture
async def admin_api_key():
    # Create internal API key for tests
    # TODO: implement key creation
    return "test-internal-key-123"
```

**`tests/integration/test_job_lifecycle.py`:**
```python
import pytest
import asyncio

@pytest.mark.asyncio
async def test_full_job_lifecycle(api_client, admin_api_key):
    """Test complete job flow: submit → poll → succeed → download"""

    # Submit job
    response = await api_client.post(
        "/api/v1/jobs",
        json={
            "prompt": "A test image",
            "width": 512,
            "height": 512,
            "steps": 1  # Fast for testing
        },
        headers={"X-API-Key": admin_api_key}
    )

    assert response.status_code == 202
    data = response.json()
    job_id = data["job_id"]

    # Poll for completion (timeout 60s)
    for _ in range(60):
        response = await api_client.get(
            f"/api/v1/jobs/{job_id}",
            headers={"X-API-Key": admin_api_key}
        )

        assert response.status_code == 200
        status = response.json()

        if status["status"] in ["succeeded", "failed"]:
            break

        await asyncio.sleep(1)

    # Verify success
    assert status["status"] == "succeeded"
    assert len(status["result"]["artifacts"]) > 0

    # Verify artifact URL accessible
    artifact_url = status["result"]["artifacts"][0]["url"]
    artifact_response = await api_client.get(artifact_url)
    assert artifact_response.status_code == 200
    assert artifact_response.headers["content-type"].startswith("image/")

@pytest.mark.asyncio
async def test_idempotency(api_client, admin_api_key):
    """Test that duplicate requests return same job_id"""

    idempotency_key = "test-idem-001"

    # Submit job twice with same key
    response1 = await api_client.post(
        "/api/v1/jobs",
        json={"prompt": "Test", "width": 512, "height": 512},
        headers={
            "X-API-Key": admin_api_key,
            "Idempotency-Key": idempotency_key
        }
    )

    response2 = await api_client.post(
        "/api/v1/jobs",
        json={"prompt": "Test", "width": 512, "height": 512},
        headers={
            "X-API-Key": admin_api_key,
            "Idempotency-Key": idempotency_key
        }
    )

    # Same job_id returned
    assert response1.json()["job_id"] == response2.json()["job_id"]

@pytest.mark.asyncio
async def test_rate_limiting(api_client):
    """Test that rate limits are enforced"""

    # Create free tier key
    # Submit requests until 429

    for i in range(20):
        response = await api_client.get("/health")

        if response.status_code == 429:
            assert "X-RateLimit-Limit" in response.headers
            assert "Retry-After" in response.headers
            break
    else:
        pytest.fail("Rate limit not enforced")
```

**Run tests:**
```bash
docker-compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v
docker-compose -f docker-compose.test.yml down
```

---

## Week 3: Operational Layer

### 5. Metrics Maturity & SLOs

**Priority:** MEDIUM (visibility)

**Define Service Level Objectives:**

```python
SLOs = {
    "job_success_rate": {
        "target": 0.99,  # 99% of jobs succeed
        "window": "1h"
    },
    "job_latency_p99": {
        "target": 60.0,  # P99 < 60s for 512x512
        "window": "1h"
    },
    "queue_depth_max": {
        "target": 50,    # Queue never exceeds 50 jobs
        "window": "5m"
    },
    "api_latency_p95": {
        "target": 0.5,   # P95 < 500ms for API calls
        "window": "1h"
    }
}
```

**Add to metrics.py:**
```python
# SLO tracking
job_slo_violations = Counter(
    "comfyui_slo_violations_total",
    "SLO violations by type",
    ["slo_name"]
)

def check_slos():
    """Background task to check SLOs and increment violations"""
    # Check job success rate
    # Check latency percentiles
    # Check queue depth
    # Increment violation counter if breached
```

**Grafana Dashboard:**
```json
{
  "panels": [
    {
      "title": "Job Success Rate (SLO: 99%)",
      "targets": [
        "rate(comfyui_jobs_total{status=\"succeeded\"}[1h]) / rate(comfyui_jobs_total[1h])"
      ]
    },
    {
      "title": "P99 Latency (SLO: 60s)",
      "targets": [
        "histogram_quantile(0.99, comfyui_job_duration_seconds_bucket)"
      ]
    },
    {
      "title": "Queue Depth (SLO: <50)",
      "targets": [
        "comfyui_queue_depth"
      ]
    }
  ]
}
```

---

### 6. Documentation: LIMITS.md

**Create `LIMITS.md`:**
```markdown
# Service Limits and Quotas

## Rate Limits

| Tier | Jobs/minute | Polling/minute | Concurrent Jobs |
|------|-------------|----------------|-----------------|
| Free | 5 | 30 | 1 |
| Pro | 20 | 100 | 3 |
| Internal | Unlimited | Unlimited | 10 |

## Timeouts

- **Job Timeout:** 20 minutes (1200s)
- **API Request Timeout:** 30 seconds
- **WebSocket Idle Timeout:** 5 minutes

## Batch Limits

- **Max Batch Size:** 10 images per job
- **Max Megapixels:** 4MP per image (2048x2048)
- **Max Steps:** 150
- **Max CFG Scale:** 30.0

## Storage

- **Artifact TTL:** 24 hours
- **Presigned URL TTL:** 1 hour
- **Max Image Size:** 20MB

## Retry Policy

- **Idempotency:** All job submissions are idempotent with 24h window
- **Safe to Retry:** All endpoints are safe to retry
- **Backoff:** Use exponential backoff on 429 or 5xx errors

## Fair Use

- Do not hammer polling endpoints (use WebSocket for progress)
- Include Idempotency-Key to prevent duplicate work
- Respect rate limit headers and Retry-After
```

---

## Gentle Nudges (From Expert Feedback)

### Environment Namespacing

Update storage client:
```python
bucket_name = f"comfyui-artifacts-{settings.environment}"
# dev: comfyui-artifacts-dev
# prod: comfyui-artifacts-prod
```

### Request ID Propagation

Update logging:
```python
logger.info("Job started", extra={
    "request_id": request_id,
    "job_id": job_id,
    "labels": {"request_id": request_id}  # For Prometheus
})
```

### Worker Protocol Versioning

Add to job data:
```python
{
    "protocol_version": "v1",
    "params": {...}
}
```

---

## Success Criteria

### Week 1: Trust Layer
- [ ] Users can be created with roles (free, pro, internal)
- [ ] API keys can be generated and revoked
- [ ] All endpoints require valid API key (except /health, /metrics)
- [ ] Rate limiting enforced per role
- [ ] Rate limit headers returned on all responses
- [ ] 429 responses with Retry-After

### Week 2: Resilience Layer
- [ ] Worker startup recovers stale jobs
- [ ] Docker Compose test environment works
- [ ] Integration tests pass (job lifecycle, idempotency, rate limit)
- [ ] Crash recovery tested (kill worker mid-job)

### Week 3: Operational Layer
- [ ] SLOs defined and tracked
- [ ] Grafana dashboard created
- [ ] LIMITS.md documentation complete
- [ ] All documentation updated with auth examples

---

## Timeline

**Week 1:** Authentication + Rate Limiting (5 days)
- Day 1-2: API key auth (models, middleware, Redis)
- Day 3: Admin endpoints (create user, create key, revoke)
- Day 4: Rate limiting (token bucket, headers)
- Day 5: Testing & polish

**Week 2:** Resilience (5 days)
- Day 6: Crash recovery loop
- Day 7: Docker Compose setup
- Day 8-9: Integration tests
- Day 10: Chaos tests (kill worker)

**Week 3:** Operations (5 days)
- Day 11: SLO definitions
- Day 12: Grafana dashboard
- Day 13: Documentation (LIMITS.md, update guides)
- Day 14-15: Testing, bug fixes, commit

---

**Status:** Ready to implement
**Next:** Create auth models and middleware
