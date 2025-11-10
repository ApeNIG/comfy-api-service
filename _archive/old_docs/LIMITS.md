# API Limits & Quotas

**Version:** 1.0.0
**Last Updated:** 2025-11-07

This document defines limits, quotas, and expectations for the ComfyUI API Service.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication & Roles](#authentication--roles)
3. [Rate Limits](#rate-limits)
4. [Job Limits](#job-limits)
5. [Idempotency](#idempotency)
6. [Artifacts & Retention](#artifacts--retention)
7. [Error Handling](#error-handling)
8. [Cancellation & Retries](#cancellation--retries)
9. [Service Level Objectives](#service-level-objectives)
10. [API Versioning](#api-versioning)
11. [Client Best Practices](#client-best-practices)

---

## Overview

The ComfyUI API Service provides two modes of operation:

### Synchronous (Simple)
- **Endpoint:** `POST /api/v1/generate`
- **Behavior:** Waits for completion, returns image URL
- **Use case:** Quick prototyping, small images
- **Timeout:** 120 seconds

### Asynchronous (Recommended)
- **Endpoints:** `POST /api/v1/jobs`, `GET /api/v1/jobs/{id}`
- **Behavior:** Returns `job_id` immediately (202 Accepted)
- **Use case:** Production, batch processing, large images
- **Timeout:** 600 seconds per job

**💡 Recommendation:** Use async for all production workloads.

---

## Authentication & Roles

### API Key Format

```
cui_sk_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789
```

- **Prefix:** `cui_sk_`
- **Length:** 43 characters (32 random bytes, base64-encoded)
- **Header:** `Authorization: Bearer <api_key>`

### Roles & Quotas

| Role | Daily Jobs | Concurrent Jobs | Rate Limit (req/min) | Price |
|------|------------|-----------------|----------------------|-------|
| **FREE** | 10 | 1 | 5 | Free |
| **PRO** | 100 | 3 | 20 | $29/mo |
| **INTERNAL** | Unlimited | 10 | Unlimited | N/A |

**Notes:**
- Daily quotas reset at 00:00 UTC
- Concurrent limit applies to `running` jobs only (not `queued`)
- INTERNAL role for admin/testing use

---

## Rate Limits

### Enforcement

Rate limits use a **token bucket algorithm** with a sliding window.

**Window:** 60 seconds

### Headers

Every authenticated response includes rate limit headers:

```http
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 13
X-RateLimit-Reset: 1731000000
```

- **X-RateLimit-Limit:** Max requests per window
- **X-RateLimit-Remaining:** Requests left in current window
- **X-RateLimit-Reset:** Unix timestamp when window resets

### 429 Response

When rate limit exceeded:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 42
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1731000042
```

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again later.",
    "limit": 20,
    "retry_after": 42
  }
}
```

**Client Action:** Wait `Retry-After` seconds before retrying.

---

## Job Limits

### Image Dimensions

| Limit | Value | Reason |
|-------|-------|--------|
| **Min width/height** | 64 px | Below this, quality suffers |
| **Max width/height** | 2048 px | GPU memory constraints |
| **Max megapixels** | 4 MP (2048×2048) | Prevents OOM errors |

**Examples:**
- ✅ 512×512 (0.26 MP)
- ✅ 1024×1024 (1.05 MP)
- ✅ 1920×1080 (2.07 MP)
- ✅ 2048×2048 (4.19 MP)
- ❌ 4096×4096 (16.78 MP) - **Exceeds limit**

### Batch Size

| Role | Max Batch | Reason |
|------|-----------|--------|
| **FREE** | 1 | Resource conservation |
| **PRO** | 4 | Reasonable for batch use |
| **INTERNAL** | 10 | Testing and admin |

**Note:** `num_images` parameter controls batch size.

### Generation Parameters

| Parameter | Min | Max | Default | Notes |
|-----------|-----|-----|---------|-------|
| `steps` | 1 | 150 | 20 | Higher = better quality, slower |
| `cfg_scale` | 1.0 | 30.0 | 7.0 | Guidance strength |
| `seed` | -1 | 2^31-1 | -1 | -1 = random |
| `num_images` | 1 | (see batch) | 1 | Batch size |

### Allowed Samplers

```
euler, euler_a, heun, dpm_2, dpm_2_a, lms,
dpm_fast, dpm_adaptive, dpmpp_2s_a, dpmpp_2m,
dpmpp_sde, ddim, plms, uni_pc
```

**Default:** `euler`

### Timeouts

| Timeout | Duration | Applies To |
|---------|----------|------------|
| **Job timeout** | 600s (10 min) | Single job execution |
| **Queue timeout** | None | Jobs wait indefinitely |
| **Sync endpoint** | 120s | `/api/v1/generate` only |

**Notes:**
- Jobs running > 600s are marked `failed` by crash recovery
- Long queue waits may occur if workers are busy

---

## Idempotency

### Purpose

Prevent duplicate job execution on network retries.

### Usage

Include `Idempotency-Key` header:

```http
POST /api/v1/jobs
Idempotency-Key: unique-key-12345
Content-Type: application/json

{
  "prompt": "A sunset",
  "model": "dreamshaper_8.safetensors"
}
```

### Behavior

- **First request:** Creates job, returns new `job_id`
- **Duplicate requests (same key):** Returns **same** `job_id`, no new execution
- **Key format:** Any string (recommend UUID or hash of request)
- **Key scope:** Per user
- **TTL:** 24 hours

### Example

```bash
# Request 1
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Idempotency-Key: abc123" \
  -d '{"prompt": "test"}'
# Returns: {"job_id": "job_001", ...}

# Request 2 (network retry)
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Idempotency-Key: abc123" \
  -d '{"prompt": "test"}'
# Returns: {"job_id": "job_001", ...}  # Same job!
```

**💡 Best Practice:** Always use idempotency keys in production.

---

## Artifacts & Retention

### Storage Backend

- **Type:** S3-compatible (MinIO)
- **Bucket:** `comfyui-artifacts`
- **Format:** PNG
- **Path:** `jobs/{job_id}/image_{index}.png`

### Presigned URLs

Artifact URLs are **presigned** for temporary access:

```json
{
  "url": "https://minio.example.com/comfyui-artifacts/jobs/abc123/image_0.png?X-Amz-Signature=..."
}
```

**TTL by role:**
- **FREE:** 1 hour
- **PRO:** 24 hours
- **INTERNAL:** 7 days

**Note:** Download artifacts within TTL period. URLs expire after that.

### Retention Policy

| Role | Retention | Reasoning |
|------|-----------|-----------|
| **FREE** | 7 days | Cost optimization |
| **PRO** | 30 days | Production workflows |
| **INTERNAL** | 90 days | Testing/debugging |

**After retention period:** Artifacts are permanently deleted.

**💡 Best Practice:** Download important artifacts immediately.

---

## Error Handling

### Standard Error Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": {...},
    "request_id": "req_abc123",
    "timestamp": "2025-11-07T12:00:00Z"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Meaning | Client Action |
|------|-------------|---------|---------------|
| `VALIDATION_ERROR` | 422 | Invalid parameters | Fix request, retry |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Wait `Retry-After`, retry |
| `UNAUTHORIZED` | 401 | Missing/invalid API key | Check authentication |
| `FORBIDDEN` | 403 | Insufficient permissions | Upgrade plan |
| `NOT_FOUND` | 404 | Job/resource not found | Check job_id |
| `QUOTA_EXCEEDED` | 402 | Daily/concurrent limit hit | Wait or upgrade |
| `INTERNAL_ERROR` | 500 | Server error | Retry with backoff |
| `BACKEND_UNAVAILABLE` | 503 | ComfyUI down | Retry with backoff |

### Example Errors

**Validation Error (422):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid width: must be between 64 and 2048",
    "details": {
      "field": "width",
      "value": -100,
      "constraint": "64 <= width <= 2048"
    }
  }
}
```

**Rate Limit (429):**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "limit": 20,
    "retry_after": 42
  }
}
```

---

## Cancellation & Retries

### Cancellation

**Endpoint:** `DELETE /api/v1/jobs/{job_id}`

**Behavior:**
- **Queued jobs:** Cancelled immediately, never start
- **Running jobs:** Best-effort cancellation (worker polls cancel flag)
- **Completed jobs:** Cannot be cancelled

**Guarantee:** Cancellation is **best-effort**, not atomic. Jobs may complete before cancellation takes effect.

**Response:**
```json
{
  "job_id": "job_123",
  "status": "canceling",
  "message": "Cancellation requested"
}
```

**Final statuses:** `canceled` or `succeeded` (if too late)

### Automatic Retries

**Policy:** No automatic retries.

**Rationale:** Image generation is expensive. We don't retry to avoid double-billing.

**Client Action:** Implement your own retry logic with exponential backoff.

### Retry Recommendations

```python
import time
import random

def submit_with_retry(payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post("/api/v1/jobs", json=payload)
            if response.status_code == 429:
                # Rate limit - respect Retry-After
                retry_after = int(response.headers.get("Retry-After", 60))
                time.sleep(retry_after)
                continue
            elif response.status_code >= 500:
                # Server error - exponential backoff with jitter
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
                continue
            else:
                return response.json()
        except requests.RequestException:
            # Network error - exponential backoff
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)

    raise Exception("Max retries exceeded")
```

---

## Service Level Objectives

See [SLO.md](SLO.md) for full details.

**Key promises:**

| Metric | Target | Impact if Missed |
|--------|--------|------------------|
| **P95 Latency** | ≤ 20s | Slow UX |
| **P99 Latency** | ≤ 40s | Timeouts in client apps |
| **API Availability** | 99.5% | Cannot submit jobs |
| **Job Success Rate** | 99.5% | Wasted credits |
| **WebSocket Freshness** | < 2s | Appears stuck |

**Error Budget:** 0.5% (99.5% SLO) = ~4.5 hours downtime/month

---

## API Versioning

### Current Version

**Version:** `v1`
**Base Path:** `/api/v1/`

### Versioning Policy

- **Breaking changes:** New major version (`/api/v2/`)
- **Non-breaking additions:** Same version
- **Deprecation notice:** 6 months minimum
- **Deprecation header:** `Deprecated: true; sunset="2026-05-01"`

### Backward Compatibility

**Guaranteed:**
- Request/response schemas won't remove fields
- Existing endpoints won't change behavior
- Status codes stay consistent

**Not Guaranteed:**
- New optional fields may be added
- New endpoints may be added
- Error messages may be improved (codes stay same)

---

## Client Best Practices

### 1. Always Use Idempotency Keys

```python
import uuid

idempotency_key = str(uuid.uuid4())
headers = {
    "Authorization": f"Bearer {api_key}",
    "Idempotency-Key": idempotency_key,
}
response = requests.post("/api/v1/jobs", json=payload, headers=headers)
```

**Why:** Prevents duplicate jobs on network failures.

---

### 2. Implement Exponential Backoff

```python
def exponential_backoff(attempt):
    return min(60, (2 ** attempt) + random.uniform(0, 1))
```

**Why:** Avoids hammering service during outages.

---

### 3. Respect 429 Rate Limits

```python
if response.status_code == 429:
    retry_after = int(response.headers["Retry-After"])
    time.sleep(retry_after)
    # Retry request
```

**Why:** Avoids wasting requests and further throttling.

---

### 4. Cap Image Dimensions

```python
MAX_PIXELS = 4_000_000  # 4 MP

def validate_dimensions(width, height):
    if width * height > MAX_PIXELS:
        # Resize proportionally
        ratio = (MAX_PIXELS / (width * height)) ** 0.5
        width = int(width * ratio)
        height = int(height * ratio)
    return width, height
```

**Why:** Prevents 422 errors and excessive generation times.

---

### 5. Don't Hot-Loop WebSockets

```python
# ❌ Bad: Reconnect immediately on disconnect
while True:
    connect_websocket()

# ✅ Good: Backoff on reconnect
for attempt in range(5):
    try:
        connect_websocket()
        break
    except:
        time.sleep(2 ** attempt)
```

**Why:** Prevents connection storms during outages.

---

### 6. Poll Status with Jitter

```python
import random

def poll_job_status(job_id):
    while True:
        status = get_job_status(job_id)
        if status in ["succeeded", "failed", "canceled"]:
            return status

        # Poll every 2-5 seconds (jitter prevents thundering herd)
        time.sleep(2 + random.uniform(0, 3))
```

**Why:** Reduces load spikes, distributes polling.

---

### 7. Download Artifacts Immediately

```python
result = get_job_status(job_id)
if result["status"] == "succeeded":
    for artifact in result["artifacts"]:
        # Download within presigned URL TTL
        image_data = requests.get(artifact["url"]).content
        save_to_disk(image_data)
```

**Why:** Presigned URLs expire. Artifacts get deleted after retention period.

---

### 8. Handle Partial Failures in Batches

```python
# Request: num_images = 4
result = wait_for_completion(job_id)

if result["status"] == "succeeded":
    artifacts = result["artifacts"]
    if len(artifacts) < 4:
        # Partial failure: some images generated
        log_warning(f"Only {len(artifacts)}/4 images generated")
```

**Why:** Batch jobs may partially succeed. Check artifact count.

---

## Questions & Support

**Documentation:** https://github.com/ApeNIG/comfy-api-service

**API Docs:** http://localhost:8000/docs

**Issues:** https://github.com/ApeNIG/comfy-api-service/issues

**Health Status:** http://localhost:8000/health

---

**Last Updated:** 2025-11-07 | **Version:** 1.0.0
