# Phase 2 - Revised Based on Expert Feedback

**Date:** 2025-11-06
**Status:** Planning - Incorporating Expert Review

---

## Expert Feedback Summary

Received detailed production-readiness review. Key points:
- ✅ Phase 1 foundation is **solid** (clean API, good validation, excellent docs)
- ⚠️ Need **job queue system** (async processing) - CRITICAL
- ⚠️ Need **observability** (metrics, tracing) - CRITICAL
- ⚠️ Need **artifact storage** (S3/MinIO) - IMPORTANT
- ⚠️ Need **idempotency** - IMPORTANT
- ⚠️ Need **circuit breakers** - IMPORTANT

---

## Revised Sprint Order

### Sprint 1: Job Queue System (CRITICAL - Week 1)
**Why First:** Long-running GPU tasks will timeout in synchronous API

**Tasks:**
1. Implement async job queue (Redis + background workers)
2. POST /generate returns job_id immediately (202 Accepted)
3. GET /jobs/{id} for status polling
4. WebSocket /ws/jobs/{id} for real-time updates
5. Job status: pending → processing → completed/failed
6. Graceful job cancellation

**Dependencies:**
- `redis` - Job queue backing store
- `dramatiq` or `arq` - Task queue (async-native)
- `websockets` - Real-time updates (already have)

**Breaking Change:** Generate endpoints become async by default

---

### Sprint 2: Authentication & Rate Limiting (HIGH - Week 2)
**Why:** Required before any public deployment

**Tasks:**
1. Database setup (SQLModel + SQLite)
2. User model with tiers (free/pro/enterprise)
3. API key authentication (X-API-Key header)
4. Auth middleware on all protected endpoints
5. Rate limiting by tier
6. Usage tracking and quotas

**Dependencies:**
- `sqlmodel` - Database ORM
- `slowapi` - Rate limiting
- `passlib[bcrypt]` - Password hashing

---

### Sprint 3: Observability (HIGH - Week 3)
**Why:** Can't debug/optimize what you can't measure

**Tasks:**
1. Structured logging with request_id tracking
2. Prometheus metrics endpoint (/metrics)
3. Key metrics:
   - Queue depth
   - Job duration (p50, p95, p99)
   - Failure rate by reason
   - GPU utilization (if available)
4. OpenTelemetry tracing
5. Sentry integration for exceptions

**Dependencies:**
- `prometheus-fastapi-instrumentator` - Metrics
- `opentelemetry-api` + `opentelemetry-sdk` - Tracing
- `sentry-sdk` - Error tracking

---

### Sprint 4: Idempotency & Resilience (MEDIUM - Week 4)
**Why:** Handle retries gracefully, fail safely

**Tasks:**
1. Idempotency-Key header support
2. Request deduplication (hash → job mapping)
3. Circuit breaker for ComfyUI calls
4. Retry logic with exponential backoff
5. Timeout enforcement
6. Graceful degradation

**Dependencies:**
- `circuitbreaker` or `pybreaker` - Circuit breaker pattern
- `tenacity` - Retry logic

---

### Sprint 5: Artifact Storage (MEDIUM - Week 5)
**Why:** Don't serve large images through API, use object storage

**Tasks:**
1. S3/MinIO integration
2. Upload generated images to object storage
3. Return signed URLs (time-limited)
4. Include metadata (seed, params) with images
5. TTL-based cleanup
6. Optional: CDN integration

**Dependencies:**
- `boto3` or `minio` - Object storage client
- `aiofiles` - Async file operations

---

### Sprint 6: Production Hardening (Week 6)
**Why:** Secure and deploy safely

**Tasks:**
1. Security:
   - CORS explicit allowlist
   - TLS enforcement
   - Request body size limits
   - MIME validation for uploads
   - Prompt redaction in logs
2. API Polish:
   - Consistent error envelope
   - Sampler enum in OpenAPI
   - X-Request-ID header
   - Pagination for /models
   - API examples in OpenAPI
3. Deployment:
   - Docker Compose (API + Redis + ComfyUI + MinIO)
   - Health/liveness probes
   - Graceful shutdown
   - Multi-worker setup

**Dependencies:**
- `gunicorn` - Production WSGI server (optional with uvicorn workers)

---

### Sprint 7: Testing & Documentation (Week 7)
**Why:** Ensure reliability, enable others

**Tasks:**
1. Tests:
   - Contract tests (all endpoints)
   - Property tests (seed determinism)
   - Load tests (Locust/k6)
   - Chaos tests (kill ComfyUI mid-gen)
   - Smoke tests (validate OpenAPI)
2. Documentation:
   - "Limits & Guarantees" page
   - Operations runbook
   - Updated architecture diagram
   - Postman collection
   - Python client library

**Dependencies:**
- `pytest` + `pytest-asyncio` - Testing
- `locust` or `k6` - Load testing
- `httpx` - Test client

---

## New Dependencies to Add

```toml
[tool.poetry.dependencies]
# Critical
redis = "^5.0.1"
arq = "^0.25.0"  # or dramatiq = "^1.15.0"

# Auth & Database
sqlmodel = "^0.0.14"
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
slowapi = "^0.1.9"

# Observability
prometheus-fastapi-instrumentator = "^6.1.0"
opentelemetry-api = "^1.21.0"
opentelemetry-sdk = "^1.21.0"
opentelemetry-instrumentation-fastapi = "^0.42b0"
sentry-sdk = {extras = ["fastapi"], version = "^1.39.0"}

# Resilience
pybreaker = "^1.0.1"
tenacity = "^8.2.3"

# Storage
boto3 = "^1.34.0"  # or minio = "^7.2.0"
aiofiles = "^23.2.1"

# Testing
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
locust = "^2.20.0"
```

---

## Quick Wins (Can Do Now)

These are small improvements that don't require major refactoring:

### 1. Add X-Request-ID Header
```python
# middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 2. Consistent Error Envelope
```python
# models/responses.py
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
```

### 3. Explicit Sampler Enum in OpenAPI
Already done in requests.py! ✅

### 4. Request Body Size Limit
```python
# main.py
app.add_middleware(
    LimitUploadSize,
    max_upload_size=10_485_760  # 10MB
)
```

### 5. Better HTTP Status Codes
```python
# For job submission, return 202 Accepted instead of 201
@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
```

---

## Architecture Decision: Job Queue

### Option A: Redis + ARQ (Recommended)
**Pros:**
- Async-native (built for asyncio)
- Simple, lightweight
- Good for FastAPI
- Persistent queue

**Cons:**
- Less mature than Celery
- Smaller ecosystem

### Option B: Redis + Dramatiq
**Pros:**
- More mature than ARQ
- Better error handling
- Good middleware system

**Cons:**
- Not async-native (uses threads)
- More complex setup

### Option C: Celery + Redis
**Pros:**
- Battle-tested, mature
- Huge ecosystem
- Great monitoring tools

**Cons:**
- Heavy, complex
- Not async-native
- Overkill for this project

**Decision:** Start with **ARQ** for simplicity and async support

---

## Job Queue Flow Design

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT REQUEST                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  POST /api/v1/jobs                                          │
│  {                                                           │
│    "prompt": "A sunset",                                    │
│    "width": 1024,                                           │
│    "height": 1024                                           │
│  }                                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Validate request (Pydantic)                             │
│  2. Create job record in DB                                 │
│  3. Enqueue job to Redis                                    │
│  4. Return 202 Accepted with job_id                         │
│                                                              │
│  Response:                                                   │
│  {                                                           │
│    "job_id": "abc-123",                                     │
│    "status": "pending",                                     │
│    "status_url": "/api/v1/jobs/abc-123",                   │
│    "websocket_url": "ws://localhost:8000/ws/jobs/abc-123" │
│  }                                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    REDIS QUEUE                               │
│  [job1, job2, job3, ...]                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKGROUND WORKER POOL                          │
│  Worker 1: Processing job1                                   │
│  Worker 2: Processing job2                                   │
│  Worker 3: Idle                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Dequeue job from Redis                                  │
│  2. Update job status: "processing"                         │
│  3. Call ComfyUI (with timeout & circuit breaker)          │
│  4. Wait for generation                                      │
│  5. Upload image to S3/MinIO                                │
│  6. Update job with result URL                              │
│  7. Update status: "completed"                              │
│  8. Broadcast via WebSocket                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  CLIENT POLLING                                              │
│  GET /api/v1/jobs/abc-123                                   │
│                                                              │
│  Response:                                                   │
│  {                                                           │
│    "job_id": "abc-123",                                     │
│    "status": "completed",                                   │
│    "result_url": "https://s3.../abc-123.png?signed=...",   │
│    "metadata": { ... },                                     │
│    "created_at": "...",                                     │
│    "completed_at": "..."                                    │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Idempotency Design

```python
# Client sends:
POST /api/v1/jobs
Idempotency-Key: user-generated-unique-key-12345
{ "prompt": "A sunset" }

# Server:
1. Check if Idempotency-Key exists in cache/DB
2. If exists: Return existing job_id (200 OK, not 202)
3. If new: Create job, store key → job_id mapping
4. TTL: 24 hours

# Store in Redis:
idempotency:user-generated-unique-key-12345 → job_id=abc-123
```

---

## Metrics to Track

### Request Metrics
- `http_requests_total` - Counter by endpoint, method, status
- `http_request_duration_seconds` - Histogram (p50, p95, p99)
- `http_requests_in_progress` - Gauge

### Job Queue Metrics
- `job_queue_depth` - Gauge (jobs waiting)
- `job_processing_duration_seconds` - Histogram
- `job_failures_total` - Counter by reason
- `jobs_in_progress` - Gauge (current processing)

### ComfyUI Metrics
- `comfyui_requests_total` - Counter
- `comfyui_request_duration_seconds` - Histogram
- `comfyui_failures_total` - Counter
- `comfyui_circuit_breaker_state` - Gauge (open/closed)

### Resource Metrics
- `gpu_utilization_percent` - Gauge (if available)
- `memory_usage_bytes` - Gauge
- `active_connections` - Gauge

---

## Testing Strategy

### 1. Contract Tests
```python
def test_job_submission():
    response = client.post("/api/v1/jobs", json=valid_request)
    assert response.status_code == 202
    assert "job_id" in response.json()

def test_job_status():
    response = client.get("/api/v1/jobs/abc-123")
    assert response.status_code == 200
    assert response.json()["status"] in ["pending", "processing", "completed", "failed"]
```

### 2. Property Tests
```python
@given(seed=st.integers(min_value=0, max_value=2**32-1))
def test_seed_determinism(seed):
    # Same seed + params = same image hash
    result1 = generate_with_seed(seed)
    result2 = generate_with_seed(seed)
    assert hash(result1) == hash(result2)
```

### 3. Load Tests
```python
# locustfile.py
class ImageGenUser(HttpUser):
    @task
    def generate_image(self):
        self.client.post("/api/v1/jobs", json={
            "prompt": "Test image",
            "width": 512,
            "height": 512
        })
```

### 4. Chaos Tests
```python
async def test_comfyui_dies_mid_generation():
    # Submit job
    job_id = submit_job()
    # Kill ComfyUI
    kill_comfyui()
    # Wait
    await asyncio.sleep(5)
    # Check job marked as failed
    status = get_job_status(job_id)
    assert status == "failed"
    assert "ComfyUI unavailable" in error_message
```

---

## Deployment Checklist

### Docker Compose Production Setup

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db/comfy
      - REDIS_URL=redis://redis:6379
      - S3_BUCKET=comfy-images
      - COMFYUI_URL=http://comfyui:8188
    depends_on:
      - redis
      - db
      - comfyui
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  worker:
    build: .
    command: arq apps.api.services.job_worker.WorkerSettings
    environment:
      - DATABASE_URL=postgresql://user:pass@db/comfy
      - REDIS_URL=redis://redis:6379
      - COMFYUI_URL=http://comfyui:8188
    depends_on:
      - redis
      - db
      - comfyui
    deploy:
      replicas: 2

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=comfy
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
    volumes:
      - db-data:/var/lib/postgresql/data

  comfyui:
    # Your ComfyUI Docker image
    ports:
      - "8188:8188"
    volumes:
      - comfyui-models:/app/models

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=admin
      - MINIO_ROOT_PASSWORD=password
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data

volumes:
  redis-data:
  db-data:
  comfyui-models:
  minio-data:
```

---

## Summary

### What the Expert Got Right
✅ Job queue is CRITICAL (Sprint 1)
✅ Observability is CRITICAL (Sprint 3)
✅ Idempotency is important (Sprint 4)
✅ Storage is important (Sprint 5)
✅ Current foundation is solid

### Adjusted Priorities
1. **Job Queue** (was Sprint 2, now Sprint 1)
2. **Auth** (was Sprint 1, now Sprint 2)
3. **Observability** (new, now Sprint 3)
4. **Idempotency & Resilience** (new, now Sprint 4)
5. **Storage** (new, now Sprint 5)
6. **Hardening** (expanded, now Sprint 6)
7. **Testing** (was Sprint 5, now Sprint 7)

### Timeline
**7 weeks** for production-ready (was 5 weeks)
- More realistic given added scope
- Can still do faster with focused effort

---

**Status:** Ready to implement
**Next:** Sprint 1 - Job Queue System
