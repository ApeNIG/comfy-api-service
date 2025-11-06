# ComfyUI API Service - Phase 2 Plan

**Started:** 2025-11-06
**Status:** Planning
**Goal:** Add production-ready features (auth, rate limiting, job queue)

---

## Phase 2 Overview

Transform the Phase 1 foundation into a production-ready service with:
- Authentication & Authorization
- Rate Limiting
- Async Job Queue
- Database Persistence
- WebSocket Support
- File Upload
- Comprehensive Testing

---

## Feature Breakdown

### 1. Authentication System

#### API Key Authentication (Simple)
**Priority:** HIGH
**Complexity:** Low

```python
# Simple API key in headers
headers = {
    "X-API-Key": "your-api-key-here"
}
```

**Implementation:**
- API keys stored in database
- Middleware to validate keys
- Associate keys with users/tiers
- Key generation endpoint (admin only)
- Key revocation support

**Files to create:**
- `apps/api/middleware/auth.py`
- `apps/api/models/auth.py`
- `apps/api/services/auth_service.py`

#### JWT Authentication (Advanced)
**Priority:** MEDIUM
**Complexity:** Medium

```python
# OAuth-style flow
POST /auth/login -> JWT token
Use token in Authorization: Bearer {token}
```

**Implementation:**
- User registration/login
- JWT token generation
- Token refresh mechanism
- Password hashing (bcrypt)
- Token expiration

**Dependencies needed:**
- `python-jose[cryptography]` - JWT handling
- `passlib[bcrypt]` - Password hashing
- `python-multipart` - Form data (already have)

---

### 2. Rate Limiting

**Priority:** HIGH
**Complexity:** Medium

**Strategy:**
- Token bucket algorithm
- Per-user limits based on tier
- IP-based limits for anonymous
- Different limits per endpoint

**Tiers:**
```
Free:     10 images/day,  1 concurrent
Basic:    100 images/day, 2 concurrent
Pro:      1000 images/day, 5 concurrent
Enterprise: Unlimited, custom limits
```

**Implementation:**
- Redis for distributed rate limiting (or in-memory for simple)
- Middleware to check limits
- Headers to show remaining quota
- 429 Too Many Requests response

**Dependencies:**
- `slowapi` - Rate limiting for FastAPI
- OR `redis` + custom implementation

**Files:**
- `apps/api/middleware/rate_limiter.py`
- `apps/api/models/rate_limits.py`

---

### 3. Async Job Queue

**Priority:** HIGH
**Complexity:** High

**Problem:** Image generation is slow (10-60+ seconds)
**Solution:** Return job_id immediately, process in background

**Flow:**
```
1. POST /api/v1/generate -> Returns job_id immediately (201 Created)
2. GET /api/v1/jobs/{job_id} -> Check status (pending/processing/completed/failed)
3. GET /api/v1/jobs/{job_id}/image -> Download image when ready
```

**Options:**

#### Option A: Simple In-Memory Queue (Start Here)
- Python's `asyncio.Queue`
- Background workers
- No external dependencies
- Lost on restart

#### Option B: Redis Queue (Production)
- `arq` or `rq` library
- Persistent queue
- Distributed workers
- Survives restarts

#### Option C: Celery (Enterprise)
- Full-featured task queue
- Complex setup
- RabbitMQ or Redis broker
- Overkill for this project?

**Recommendation:** Start with Option A, upgrade to B

**Implementation:**
- Job model with status tracking
- Background worker pool
- Queue management service
- Job status endpoints
- Job cancellation support

**Files:**
- `apps/api/services/job_queue.py`
- `apps/api/services/job_worker.py`
- `apps/api/models/jobs.py`
- `apps/api/routers/jobs.py`

---

### 4. Database Persistence

**Priority:** HIGH (needed for auth, jobs)
**Complexity:** Medium

**What to store:**
- Users and API keys
- Job history
- Usage statistics
- Rate limit counters (or use Redis)

**Options:**

#### SQLite (Development)
- Built-in, no setup
- Good for development
- File-based

#### PostgreSQL (Production)
- Robust, scalable
- JSON support
- Better for production

**ORM Choice:**
- **SQLAlchemy** - Standard, powerful
- **Tortoise ORM** - Async-native
- **SQLModel** - Pydantic + SQLAlchemy

**Recommendation:** SQLModel (Pydantic integration)

**Dependencies:**
- `sqlmodel` - ORM
- `psycopg2-binary` - PostgreSQL driver (or `asyncpg`)
- `alembic` - Database migrations

**Files:**
- `apps/api/database.py` - DB connection
- `apps/api/models/db/` - Database models
  - `user.py`
  - `api_key.py`
  - `job.py`
  - `usage.py`
- `alembic/` - Migration files

---

### 5. WebSocket for Real-time Updates

**Priority:** MEDIUM
**Complexity:** Medium

**Use case:** Show progress during image generation

```javascript
ws = new WebSocket('ws://localhost:8000/ws/jobs/{job_id}');
ws.onmessage = (event) => {
  // Receive progress updates
  const data = JSON.parse(event.data);
  console.log(`Progress: ${data.progress}%`);
};
```

**Implementation:**
- WebSocket endpoint per job
- Broadcast progress updates
- Connection management
- Automatic cleanup

**FastAPI has built-in WebSocket support!**

**Files:**
- `apps/api/routers/websocket.py`
- `apps/api/services/websocket_manager.py`

---

### 6. File Upload Support

**Priority:** MEDIUM
**Complexity:** Low

**Use cases:**
- Image-to-image generation
- Inpainting
- ControlNet inputs
- Reference images

**Implementation:**
- File upload endpoint
- File validation (type, size)
- Temporary storage
- Cleanup old files

**Files:**
- `apps/api/routers/upload.py`
- `apps/api/services/file_service.py` (extend existing)

**Dependencies:** Already have `python-multipart`

---

### 7. Testing

**Priority:** HIGH
**Complexity:** Medium

**Types:**

#### Unit Tests
- Test individual functions
- Mock external dependencies
- Fast, isolated

#### Integration Tests
- Test API endpoints
- Use test database
- Test workflows end-to-end

#### Load Tests
- Apache Bench, Locust, or k6
- Measure performance
- Find bottlenecks

**Framework:** `pytest` + `pytest-asyncio`

**Dependencies:**
- `pytest`
- `pytest-asyncio`
- `httpx` (for testing FastAPI)
- `pytest-cov` (coverage)

**Files:**
- `tests/` directory
  - `test_auth.py`
  - `test_generate.py`
  - `test_rate_limiting.py`
  - `test_jobs.py`
  - `conftest.py` (fixtures)

---

## Implementation Order

### Sprint 1: Foundation (Week 1)
1. ✅ Set up database (SQLModel + SQLite)
2. ✅ Create database models (User, APIKey, Job)
3. ✅ Implement simple API key authentication
4. ✅ Add auth middleware
5. ✅ Update endpoints to require auth

### Sprint 2: Job Queue (Week 2)
1. ✅ Implement in-memory job queue
2. ✅ Create background worker
3. ✅ Update /generate to return job_id
4. ✅ Add job status endpoints
5. ✅ Test async flow

### Sprint 3: Rate Limiting (Week 3)
1. ✅ Implement rate limiting middleware
2. ✅ Add tier-based limits
3. ✅ Add usage tracking
4. ✅ Test limits work correctly

### Sprint 4: Enhancements (Week 4)
1. ⏳ WebSocket support
2. ⏳ File upload
3. ⏳ JWT authentication (optional)
4. ⏳ Admin endpoints

### Sprint 5: Testing & Polish (Week 5)
1. ⏳ Write unit tests
2. ⏳ Write integration tests
3. ⏳ Load testing
4. ⏳ Documentation updates
5. ⏳ Bug fixes

---

## Dependencies to Add

```toml
[tool.poetry.dependencies]
# Database
sqlmodel = "^0.0.14"
psycopg2-binary = "^2.9.9"  # or asyncpg
alembic = "^1.13.1"

# Authentication
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}

# Rate Limiting
slowapi = "^0.1.9"
redis = "^5.0.1"  # optional, for distributed

# Job Queue (optional - for advanced)
arq = "^0.25.0"  # or rq

# Testing
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
```

---

## Database Schema

### User Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    tier VARCHAR(20) DEFAULT 'free',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### APIKey Table
```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY,
    key VARCHAR(64) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP
);
```

### Job Table
```sql
CREATE TABLE jobs (
    id VARCHAR(36) PRIMARY KEY,  -- UUID
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) NOT NULL,  -- pending, processing, completed, failed
    request_data JSONB NOT NULL,
    result_data JSONB,
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Usage Table
```sql
CREATE TABLE usage (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    endpoint VARCHAR(100) NOT NULL,
    date DATE NOT NULL,
    count INTEGER DEFAULT 0,
    UNIQUE(user_id, endpoint, date)
);
```

---

## Configuration

### Environment Variables
```bash
# Database
DATABASE_URL=sqlite:///./comfy_api.db
# or: postgresql://user:pass@localhost/comfy_api

# Auth
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Rate Limiting
RATE_LIMIT_ENABLED=true
REDIS_URL=redis://localhost:6379

# ComfyUI
COMFYUI_URL=http://localhost:8188

# File Upload
MAX_UPLOAD_SIZE=10485760  # 10MB
UPLOAD_DIR=/tmp/comfy_uploads
```

---

## API Changes

### New Endpoints

#### Authentication
```
POST   /api/v1/auth/register      Register new user
POST   /api/v1/auth/login         Login (get API key or JWT)
POST   /api/v1/auth/logout        Logout
GET    /api/v1/auth/me            Get current user info
POST   /api/v1/auth/keys          Create new API key
DELETE /api/v1/auth/keys/{id}     Revoke API key
```

#### Jobs (Modified Generate Flow)
```
POST   /api/v1/jobs               Submit generation job (returns job_id)
GET    /api/v1/jobs               List user's jobs
GET    /api/v1/jobs/{id}          Get job status
GET    /api/v1/jobs/{id}/result   Get job result (image)
DELETE /api/v1/jobs/{id}          Cancel job
```

#### Upload
```
POST   /api/v1/upload             Upload image file
```

#### Admin (Optional)
```
GET    /api/v1/admin/users        List all users
GET    /api/v1/admin/stats        System statistics
PATCH  /api/v1/admin/users/{id}   Update user tier
```

#### WebSocket
```
WS     /ws/jobs/{id}              Real-time job updates
```

---

## Breaking Changes from Phase 1

**⚠️ IMPORTANT:** Phase 2 introduces breaking changes

### Old Way (Phase 1):
```python
response = requests.post(
    "http://localhost:8000/api/v1/generate",
    json={"prompt": "A sunset"}
)
# Waits for image, returns immediately with image_url
```

### New Way (Phase 2):
```python
# Submit job
response = requests.post(
    "http://localhost:8000/api/v1/jobs",
    headers={"X-API-Key": "your-key"},
    json={"prompt": "A sunset"}
)
job_id = response.json()["job_id"]

# Poll for completion
while True:
    status = requests.get(
        f"http://localhost:8000/api/v1/jobs/{job_id}",
        headers={"X-API-Key": "your-key"}
    ).json()
    if status["status"] == "completed":
        break
    time.sleep(1)

# Get result
image = requests.get(
    f"http://localhost:8000/api/v1/jobs/{job_id}/result",
    headers={"X-API-Key": "your-key"}
).content
```

### Compatibility Option:
Keep Phase 1 endpoints for backwards compatibility:
- `/api/v1/generate` - Synchronous (kept for compatibility)
- `/api/v1/jobs` - Asynchronous (new preferred method)

---

## Success Criteria

### Must Have
- ✅ API key authentication working
- ✅ Rate limiting enforced
- ✅ Job queue functional
- ✅ Database persistence
- ✅ All endpoints require auth
- ✅ Tests passing

### Nice to Have
- ⏳ WebSocket updates
- ⏳ File upload
- ⏳ JWT tokens
- ⏳ Admin interface
- ⏳ Usage dashboard

---

## Risks & Mitigations

### Risk 1: Complexity
**Risk:** Phase 2 is significantly more complex
**Mitigation:** Implement incrementally, test thoroughly

### Risk 2: Breaking Changes
**Risk:** Existing users affected
**Mitigation:** Keep v1 endpoints, version API properly

### Risk 3: Performance
**Risk:** Database/queue overhead
**Mitigation:** Use connection pooling, optimize queries

### Risk 4: Security
**Risk:** Auth vulnerabilities
**Mitigation:** Use proven libraries, security review

---

## Timeline

**Estimated:** 4-5 weeks
- Sprint 1: Database & Auth (1 week)
- Sprint 2: Job Queue (1 week)
- Sprint 3: Rate Limiting (1 week)
- Sprint 4: Enhancements (1 week)
- Sprint 5: Testing (1 week)

**Note:** Can be done faster with focused effort

---

**Status:** Ready to begin
**Next Action:** Install dependencies and set up database
