# API + Creator Integration Guide

**Last Updated:** 2025-11-10

---

## 🎯 Overview

This document explains how the existing **API product** (for developers) and the new **Creator product** (for end users) coexist in the same codebase.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│          FastAPI Application (Port 8000)            │
│                                                     │
│  ┌────────────────┐        ┌────────────────────┐  │
│  │   API Routes   │        │  Creator Routes    │  │
│  │  /api/v1/*     │        │  /creator/*        │  │
│  │                │        │  /auth/*           │  │
│  │ - /generate/   │        │  - /dashboard      │  │
│  │ - /jobs        │        │  - /settings       │  │
│  │ - /health      │        │  - /billing        │  │
│  │                │        │                    │  │
│  │ Auth: API Key  │        │ Auth: OAuth        │  │
│  └───────┬────────┘        └─────────┬──────────┘  │
│          │                           │             │
└──────────┼───────────────────────────┼─────────────┘
           │                           │
           ▼                           ▼
    ┌──────────────────────────────────────────┐
    │        Shared Services Layer             │
    │                                          │
    │  - ComfyUI Client                        │
    │  - Storage Providers (Drive, MinIO)      │
    │  - Job Queue (Dramatiq + Redis)          │
    │  - Preset Manager                        │
    └──────────────────────────────────────────┘
           │                           │
           ▼                           ▼
    ┌─────────────┐            ┌─────────────┐
    │    Redis    │            │  Postgres   │
    │   (Jobs)    │            │   (Users)   │
    └─────────────┘            └─────────────┘
```

---

## 📁 Directory Structure

```
comfy-api-service/
├── apps/
│   ├── api/                    # EXISTING: API Product
│   │   ├── main.py            # API app entry point
│   │   ├── config.py          # Settings (Pydantic)
│   │   ├── routers/
│   │   │   ├── generate.py    # POST /api/v1/generate/
│   │   │   ├── jobs.py        # POST /api/v1/jobs
│   │   │   └── health.py      # GET /health, /healthz
│   │   ├── models/
│   │   │   ├── requests.py    # Pydantic request models
│   │   │   └── responses.py   # Pydantic response models
│   │   └── services/
│   │       └── comfyui_client.py  # ComfyUI integration
│   │
│   ├── creator/               # NEW: Creator Product
│   │   ├── main.py           # Creator app entry point
│   │   ├── config.py         # Creator-specific settings
│   │   ├── routers/
│   │   │   ├── auth.py       # OAuth login/logout
│   │   │   ├── dashboard.py  # User dashboard API
│   │   │   ├── drive.py      # Drive folder management
│   │   │   ├── presets.py    # Preset selection
│   │   │   └── billing.py    # Stripe integration
│   │   ├── models/
│   │   │   ├── user.py       # User Pydantic models
│   │   │   └── subscription.py
│   │   └── services/
│   │       ├── auth.py       # OAuth service
│   │       ├── billing.py    # Stripe service
│   │       └── storage/
│   │           ├── base.py   # StorageProvider ABC
│   │           ├── drive.py  # GoogleDriveProvider
│   │           └── minio.py  # MinIOProvider
│   │
│   ├── shared/               # NEW: Shared code
│   │   ├── services/
│   │   │   ├── comfyui.py   # ComfyUI wrapper (both use)
│   │   │   ├── presets.py   # Preset loader
│   │   │   └── storage.py   # Storage factory
│   │   └── models/
│   │       └── job.py       # Shared job models
│   │
│   ├── worker/              # EXISTING: Extend for Creator
│   │   ├── tasks.py         # Add drive_process_upload task
│   │   ├── settings.py
│   │   └── presets/         # NEW: Preset JSON files
│   │       ├── portrait_pro.json
│   │       ├── product_glow.json
│   │       └── cinematic.json
│   │
│   └── web/                 # NEW: Frontend Dashboard
│       ├── static/
│       │   ├── css/
│       │   ├── js/
│       │   └── images/
│       └── templates/
│           ├── dashboard.html
│           ├── settings.html
│           └── billing.html
│
├── sdk/                     # EXISTING: Keep for API users
├── workflows/               # EXISTING: ComfyUI workflows
├── alembic/                 # NEW: DB migrations
│   ├── versions/
│   └── env.py
├── docker-compose.yml       # EXTENDED: Add postgres
└── .env                     # EXTENDED: Add new vars
```

---

## 🔀 Routing Strategy

### Single FastAPI App with Mounted Sub-Apps

**File:** `apps/main.py` (NEW: Top-level entry point)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apps.api.main import app as api_app
from apps.creator.main import app as creator_app

# Main application
app = FastAPI(title="ComfyUI Platform")

# Mount sub-applications
app.mount("/api", api_app)        # API product at /api/*
app.mount("/creator", creator_app) # Creator product at /creator/*

# Static files for dashboard
app.mount("/static", StaticFiles(directory="apps/web/static"), name="static")

# Root redirect
@app.get("/")
async def root():
    return {"message": "ComfyUI Platform", "docs": "/docs"}
```

### API Routes (Existing)

**File:** `apps/api/main.py`

```python
from fastapi import FastAPI, Depends
from apps.api.routers import generate, jobs, health
from apps.api.middleware.auth import verify_api_key

app = FastAPI(title="ComfyUI API")

# API routes (require API key)
app.include_router(
    generate.router,
    prefix="/v1",
    tags=["Generate"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    jobs.router,
    prefix="/v1",
    tags=["Jobs"],
    dependencies=[Depends(verify_api_key)]
)

# Health checks (no auth)
app.include_router(health.router, tags=["Health"])
```

**URLs:**
- `POST /api/v1/generate/` - Sync generation
- `POST /api/v1/jobs` - Async job queue
- `GET /api/v1/jobs/{id}` - Job status
- `GET /api/health` - Health check

**Authentication:** API Key in header
```bash
Authorization: Bearer sk_live_abc123
```

---

### Creator Routes (New)

**File:** `apps/creator/main.py`

```python
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from apps.creator.routers import auth, dashboard, drive, presets, billing
from apps.creator.middleware.auth import get_current_user

app = FastAPI(title="Creator Dashboard")

# Public routes
app.include_router(auth.router, prefix="/auth", tags=["Auth"])

# Protected routes (require OAuth login)
app.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    drive.router,
    prefix="/drive",
    tags=["Drive"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    presets.router,
    prefix="/presets",
    tags=["Presets"],
    dependencies=[Depends(get_current_user)]
)

app.include_router(
    billing.router,
    prefix="/billing",
    tags=["Billing"],
    dependencies=[Depends(get_current_user)]
)

# Serve dashboard HTML
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("apps/web/templates/dashboard.html") as f:
        return f.read()
```

**URLs:**
- `GET /creator/auth/login` - OAuth login
- `GET /creator/auth/callback` - OAuth callback
- `GET /creator/dashboard` - User dashboard (HTML)
- `GET /creator/dashboard/api/jobs` - Recent jobs (JSON)
- `POST /creator/drive/connect` - Connect Drive folder
- `GET /creator/presets` - List presets
- `POST /creator/billing/checkout` - Start Stripe checkout

**Authentication:** Session cookie (OAuth)
```
Cookie: session=<jwt_token>
```

---

## 🔐 Authentication Strategies

### API Product: API Key

**Storage:** Database table `api_keys`
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY,
    key_hash VARCHAR(64) NOT NULL,  -- SHA256 of actual key
    user_email VARCHAR(255),
    scopes TEXT[],  -- ['generate', 'jobs']
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

**Middleware:** `apps/api/middleware/auth.py`
```python
async def verify_api_key(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing API key")

    key = authorization.replace("Bearer ", "")
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    # Check database
    api_key = db.query(APIKey).filter_by(key_hash=key_hash).first()
    if not api_key or api_key.is_expired():
        raise HTTPException(401, "Invalid API key")

    return api_key
```

**Usage:**
```bash
curl -H "Authorization: Bearer sk_live_abc123" \
  https://api.example.com/api/v1/generate/
```

---

### Creator Product: OAuth + Session

**Provider:** Google OAuth 2.0

**Flow:**
1. User clicks "Login with Google"
2. Redirect to Google OAuth consent screen
3. User approves Drive access
4. Google redirects to `/creator/auth/callback?code=...`
5. Exchange code for access + refresh tokens
6. Create user session (JWT cookie)
7. Redirect to dashboard

**Middleware:** `apps/creator/middleware/auth.py`
```python
async def get_current_user(session: str = Cookie(None)):
    if not session:
        raise HTTPException(401, "Not logged in")

    try:
        payload = jwt.decode(session, SECRET_KEY, algorithms=["HS256"])
        user_id = payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")

    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(401, "User not found")

    return user
```

**Session Token:**
```python
# Create JWT
payload = {
    "user_id": str(user.id),
    "exp": datetime.utcnow() + timedelta(days=7)
}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# Set cookie
response.set_cookie(
    key="session",
    value=token,
    httponly=True,
    secure=True,  # HTTPS only
    samesite="lax",
    max_age=7*24*60*60  # 7 days
)
```

---

## 🗄️ Database Strategy

### Two Databases

**Redis (Existing):**
- Job queue (both API and Creator)
- Shared between products

**Postgres (New):**
- User accounts
- Subscriptions
- Creator-specific data
- API keys (optional, can use Redis)

**Connection:**
```python
# API product (no Postgres needed, optional)
REDIS_URL = "redis://localhost:6379"

# Creator product (needs both)
REDIS_URL = "redis://localhost:6379"
DATABASE_URL = "postgresql://user:pass@localhost:5432/creator_db"
```

---

## 🔄 Job Queue Integration

### Shared Worker, Different Task Types

**File:** `apps/worker/tasks.py`

```python
from dramatiq import actor

# EXISTING: API-triggered jobs
@actor
async def api_generate_image(job_data: dict):
    """Called by POST /api/v1/jobs"""
    prompt = job_data["prompt"]
    # ... process with ComfyUI
    # ... store result in MinIO
    return {"status": "completed", "url": "..."}

# NEW: Creator-triggered jobs
@actor
async def drive_process_upload(job_data: dict):
    """Called by Drive polling service"""
    user_id = job_data["user_id"]
    drive_file_id = job_data["drive_file_id"]
    preset_name = job_data["preset_name"]

    # 1. Download from Drive
    file_bytes = await drive_provider.download(drive_file_id)

    # 2. Process with ComfyUI (reuse API logic)
    result = await comfyui_client.process_image(file_bytes, preset_name)

    # 3. Upload to Drive output folder
    output_id = await drive_provider.upload(result, output_folder_id)

    # 4. Update job in Postgres
    db.update_job(job_id, status="completed", output_drive_file_id=output_id)

    # 5. Send email notification
    await send_email(user_id, "Your image is ready!")

    return {"status": "completed"}
```

**Key Difference:**
- **API jobs:** Result stored in MinIO, returned via API
- **Creator jobs:** Result uploaded to Drive, user notified

---

## 📦 Shared Services

### ComfyUI Client (Reused)

**File:** `apps/shared/services/comfyui.py`

```python
class ComfyUIService:
    """Shared by API and Creator products"""

    async def process_image(
        self,
        image_bytes: bytes,
        workflow: dict,
        **params
    ) -> bytes:
        """
        Generic image processing.
        Used by:
        - API: Direct calls from /api/v1/generate/
        - Creator: Called from drive_process_upload task
        """
        # Upload image to ComfyUI
        # Queue prompt
        # Poll for result
        # Download result
        return result_bytes
```

**Usage:**

**From API:**
```python
# apps/api/routers/generate.py
from apps.shared.services.comfyui import ComfyUIService

@router.post("/v1/generate/")
async def generate(request: GenerateRequest):
    comfyui = ComfyUIService()
    result = await comfyui.process_image(
        image_bytes=None,  # Text-to-image
        workflow=load_workflow("t2i_basic.json"),
        prompt=request.prompt
    )
    return {"image_url": upload_to_minio(result)}
```

**From Creator:**
```python
# apps/worker/tasks.py
from apps.shared.services.comfyui import ComfyUIService
from apps.shared.services.presets import load_preset

@actor
async def drive_process_upload(job_data):
    comfyui = ComfyUIService()
    preset = load_preset(job_data["preset_name"])

    result = await comfyui.process_image(
        image_bytes=download_from_drive(job_data["drive_file_id"]),
        workflow=preset["workflow"],
        **preset["params"]
    )
    upload_to_drive(result, job_data["output_folder_id"])
```

---

### Storage Abstraction (New)

**File:** `apps/shared/services/storage.py`

```python
from abc import ABC, abstractmethod

class StorageProvider(ABC):
    """Interface for storage backends"""

    @abstractmethod
    async def upload(self, file_bytes: bytes, filename: str) -> str:
        """Upload file, return URL or ID"""
        pass

    @abstractmethod
    async def download(self, file_id: str) -> bytes:
        """Download file by ID"""
        pass

    @abstractmethod
    async def list_files(self, folder_id: str) -> list:
        """List files in folder"""
        pass
```

**Implementations:**

**Drive Provider:**
```python
class GoogleDriveProvider(StorageProvider):
    async def upload(self, file_bytes, filename):
        # Use Google Drive API
        return drive_file_id

    async def download(self, file_id):
        # Download from Drive
        return file_bytes
```

**MinIO Provider:**
```python
class MinIOProvider(StorageProvider):
    async def upload(self, file_bytes, filename):
        # Upload to MinIO
        return presigned_url

    async def download(self, file_id):
        # Download from MinIO
        return file_bytes
```

**Factory:**
```python
def get_storage_provider(user: User) -> StorageProvider:
    """Return provider based on user config"""
    if user.storage_type == "drive":
        return GoogleDriveProvider(user.drive_tokens)
    elif user.storage_type == "minio":
        return MinIOProvider()
    else:
        raise ValueError("Unknown storage type")
```

---

## 🚀 Deployment

### Docker Compose

**File:** `docker-compose.yml`

```yaml
version: '3.8'

services:
  # EXISTING: Keep all current services
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  minio:
    image: minio/minio
    ports: ["9000:9000", "9001:9001"]

  # NEW: Add Postgres for Creator
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: creator_db
      POSTGRES_USER: creator
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports: ["5432:5432"]
    volumes:
      - postgres-data:/var/lib/postgresql/data

  # EXISTING: API service (updated)
  api:
    build: .
    command: uvicorn apps.main:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://creator:${POSTGRES_PASSWORD}@postgres:5432/creator_db
      - COMFYUI_URL=${COMFYUI_URL}
    depends_on:
      - redis
      - postgres

  # EXISTING: Worker (updated for Drive tasks)
  worker:
    build: .
    command: dramatiq apps.worker.tasks
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://creator:${POSTGRES_PASSWORD}@postgres:5432/creator_db
    depends_on:
      - redis
      - postgres

  # NEW: Drive poller (cron service)
  poller:
    build: .
    command: python apps/worker/poller.py
    environment:
      - DATABASE_URL=postgresql://creator:${POSTGRES_PASSWORD}@postgres:5432/creator_db
    depends_on:
      - postgres

volumes:
  postgres-data:
```

---

## 🔧 Environment Variables

**File:** `.env`

```bash
# EXISTING: API vars
COMFYUI_URL=https://jfmkqw45px5o3x-8188.proxy.runpod.net
COMFYUI_TIMEOUT=120.0
REDIS_URL=redis://localhost:6379
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# NEW: Creator vars
DATABASE_URL=postgresql://creator:password@localhost:5432/creator_db
POSTGRES_PASSWORD=your_secure_password

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/creator/auth/callback

# Stripe
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Security
SECRET_KEY=your_secret_jwt_key
ENCRYPTION_KEY=your_encryption_key_for_tokens

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
```

---

## 📊 Monitoring

### Separate Metrics

**API Product:**
- Requests per minute
- Generation time (p50, p95, p99)
- Error rate
- API key usage

**Creator Product:**
- Active users (DAU, MAU)
- Jobs processed per day
- Subscription conversions
- Churn rate

**Shared:**
- ComfyUI uptime
- Worker queue depth
- Redis memory usage

---

## ✅ Summary

| Aspect | API Product | Creator Product | Shared |
|--------|------------|-----------------|--------|
| **Routes** | `/api/v1/*` | `/creator/*` | - |
| **Auth** | API Key | OAuth + Session | - |
| **Database** | Redis only | Postgres + Redis | Redis |
| **Storage** | MinIO | Google Drive | Abstraction |
| **Processing** | Sync + Async | Async only | ComfyUI |
| **Users** | Developers | End Users | - |
| **Pricing** | Usage-based | Subscription | - |

**Key Insight:** Two products, one backend. Clean separation via routing and auth, shared infrastructure for efficiency.

---

*This architecture allows independent evolution of each product while maximizing code reuse.*
