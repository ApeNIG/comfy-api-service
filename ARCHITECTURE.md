# ComfyUI API Service - Architecture Documentation

**Version:** 1.0
**Last Updated:** 2025-11-06
**Status:** Design Phase

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [API Design](#api-design)
6. [Security Considerations](#security-considerations)
7. [Scalability & Performance](#scalability--performance)

---

## System Overview

### High-Level Architecture

The ComfyUI API Service follows a **multi-tier architecture** with clear separation between presentation (API), business logic (services), and external systems (ComfyUI).

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
│         (Web Apps, Mobile Apps, CLI Tools, etc.)            │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/HTTPS (REST API)
                        │ Port 8000
┌───────────────────────▼─────────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              API Endpoints (Routers)                 │   │
│  │  - Image Generation  - Workflow Management           │   │
│  │  - Status Checking   - Health/Metrics               │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼─────────────────────────────────┐   │
│  │              Middleware Layer                        │   │
│  │  - Error Handling    - Logging                       │   │
│  │  - Request Validation - Response Formatting          │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼─────────────────────────────────┐   │
│  │              Service Layer                           │   │
│  │  - ComfyUI Client    - File Manager                  │   │
│  │  - Job Tracker       - Validation Logic              │   │
│  └───────────────────┬─────────────────────────────────┘   │
│                      │                                       │
│  ┌───────────────────▼─────────────────────────────────┐   │
│  │         Pydantic Models (Data Validation)            │   │
│  │  - Request Models    - Response Models               │   │
│  │  - Config Models     - Error Models                  │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP (HTTPX AsyncClient)
                        │ Port 8188
┌───────────────────────▼─────────────────────────────────────┐
│                     ComfyUI Backend                          │
│  - Node-based workflow engine                                │
│  - AI model execution (Stable Diffusion, etc.)               │
│  - Image processing pipeline                                 │
└──────────────────────────────────────────────────────────────┘
```

### Service Separation

**Why Two Services?**

1. **ComfyUI (Port 8188):**
   - Original ComfyUI application
   - Handles AI model execution
   - Provides workflow processing
   - Has its own HTTP API and WebSocket interface

2. **FastAPI Service (Port 8000):**
   - REST API wrapper
   - Request validation and transformation
   - Authentication and authorization
   - Rate limiting and quota management
   - Simplified interface for common operations
   - Production-ready features (logging, monitoring, etc.)

**Benefits:**
- Keep ComfyUI untouched (easier to update)
- Add production features without modifying ComfyUI
- Abstract ComfyUI's complexity
- Enable multiple API versions simultaneously

---

## Architecture Diagrams

### Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│ FastAPI Application (apps/api/)                                   │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ main.py                                                      │ │
│  │  - App initialization                                        │ │
│  │  - Router registration                                       │ │
│  │  - Middleware configuration                                  │ │
│  │  - CORS settings                                             │ │
│  │  - Lifespan events (startup/shutdown)                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ routers/                                                     │ │
│  │  ├─ generate.py      (POST /generate, POST /generate/batch) │ │
│  │  ├─ workflows.py     (GET /workflows, POST /workflows)      │ │
│  │  ├─ jobs.py          (GET /jobs/{id}, GET /jobs)            │ │
│  │  └─ health.py        (GET /health, GET /metrics)            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ services/                                                    │ │
│  │  ├─ comfyui_client.py  (HTTPX client, API wrapper)          │ │
│  │  ├─ file_service.py    (File upload/download handling)      │ │
│  │  ├─ job_service.py     (Job tracking, status management)    │ │
│  │  └─ workflow_service.py (Workflow templates, management)    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ models/                                                      │ │
│  │  ├─ requests.py   (GenerateImageRequest, WorkflowRequest)   │ │
│  │  ├─ responses.py  (ImageResponse, JobStatus, ErrorResponse) │ │
│  │  └─ config.py     (Configuration models)                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ middleware/                                                  │ │
│  │  ├─ error_handler.py   (Global error handling)              │ │
│  │  ├─ logging_middleware.py (Request/response logging)        │ │
│  │  └─ rate_limiter.py    (Rate limiting, future)              │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ utils/                                                       │ │
│  │  ├─ validators.py  (Custom validation logic)                │ │
│  │  ├─ constants.py   (Constants, enums)                       │ │
│  │  └─ helpers.py     (Utility functions)                      │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Request Flow Diagram

```
Client Request
     │
     ▼
┌─────────────────────┐
│ FastAPI Endpoint    │
│ (Router Handler)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Request Validation  │
│ (Pydantic Model)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Business Logic      │
│ (Service Layer)     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ComfyUI Client      │
│ (HTTPX Request)     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ ComfyUI Backend     │
│ (AI Processing)     │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Response Transform  │
│ (Pydantic Model)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ JSON Response       │
│ (to Client)         │
└─────────────────────┘
```

---

## Component Design

### 1. API Layer (Routers)

**Responsibility:** Handle HTTP requests, validate input, return responses

**Design Principles:**
- Thin controllers - delegate to services
- Async handlers for non-blocking I/O
- Clear HTTP semantics (status codes, headers)
- OpenAPI/Swagger documentation

**Example Structure:**
```python
# apps/api/routers/generate.py
from fastapi import APIRouter, Depends, HTTPException
from ..models.requests import GenerateImageRequest
from ..models.responses import ImageResponse
from ..services.comfyui_client import ComfyUIClient

router = APIRouter(prefix="/api/v1/generate", tags=["Image Generation"])

@router.post("/", response_model=ImageResponse)
async def generate_image(
    request: GenerateImageRequest,
    client: ComfyUIClient = Depends()
) -> ImageResponse:
    """Generate an image using ComfyUI"""
    # Delegate to service layer
    pass
```

### 2. Service Layer

**Responsibility:** Business logic, external system communication, data transformation

**Key Services:**

#### ComfyUI Client Service
```
Purpose: Abstract ComfyUI HTTP API
Methods:
  - submit_workflow(workflow: dict) -> str (job_id)
  - get_job_status(job_id: str) -> JobStatus
  - get_generated_image(job_id: str) -> bytes
  - list_models() -> List[str]
  - health_check() -> bool
```

#### File Service
```
Purpose: Handle image uploads/downloads
Methods:
  - save_uploaded_file(file: UploadFile) -> str (path)
  - get_generated_image(path: str) -> bytes
  - cleanup_old_files() -> int (deleted_count)
```

#### Job Service (Future)
```
Purpose: Track job status, manage queue
Methods:
  - create_job(request: GenerateRequest) -> Job
  - update_job_status(job_id: str, status: str)
  - get_job(job_id: str) -> Job
  - list_jobs(user_id: str) -> List[Job]
```

### 3. Data Models (Pydantic)

**Responsibility:** Request/response validation, data serialization

**Key Models:**

#### Request Models
```python
class GenerateImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    negative_prompt: Optional[str] = None
    width: int = Field(512, ge=64, le=2048)
    height: int = Field(512, ge=64, le=2048)
    steps: int = Field(20, ge=1, le=150)
    cfg_scale: float = Field(7.0, ge=1.0, le=30.0)
    sampler: str = Field("euler_a")
    seed: Optional[int] = None
    model: str = Field("sd_xl_base_1.0.safetensors")
```

#### Response Models
```python
class ImageResponse(BaseModel):
    job_id: str
    status: str  # "queued", "processing", "completed", "failed"
    image_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
```

### 4. Middleware

**Responsibility:** Cross-cutting concerns (logging, errors, CORS)

**Middleware Stack:**
1. **CORS Middleware** - Allow cross-origin requests
2. **Logging Middleware** - Log all requests/responses
3. **Error Handler Middleware** - Catch and format exceptions
4. **Rate Limiter** (Future) - Prevent abuse

---

## Data Flow

### Image Generation Flow

```
1. Client sends POST /api/v1/generate
   {
     "prompt": "A beautiful sunset",
     "width": 1024,
     "height": 1024,
     "steps": 30
   }

2. FastAPI validates request (Pydantic)
   - Check required fields
   - Validate ranges (width, height, steps)
   - Sanitize prompt

3. Router passes to Service Layer
   - ComfyUIClient.generate_image(request)

4. Service transforms to ComfyUI workflow format
   {
     "prompt": {...},  # Node graph structure
     "client_id": "..."
   }

5. Service sends to ComfyUI via HTTPX
   POST http://localhost:8188/prompt

6. ComfyUI processes request
   - Queues job
   - Loads model
   - Generates image
   - Saves to output folder

7. Service polls/waits for completion
   - Check job status
   - Wait for completion
   - Retrieve image file

8. Service returns to Router
   - ImageResponse with URL or base64 data

9. FastAPI serializes and sends to Client
   {
     "job_id": "abc-123",
     "status": "completed",
     "image_url": "/api/v1/images/abc-123.png",
     "metadata": {...}
   }
```

### Error Handling Flow

```
1. Error occurs (any layer)

2. Exception propagates up

3. Error Handler Middleware catches

4. Transform to standard format
   {
     "error": {
       "code": "VALIDATION_ERROR",
       "message": "Width must be between 64 and 2048",
       "details": {...}
     }
   }

5. Set appropriate HTTP status code
   - 400: Client errors (validation)
   - 500: Server errors (ComfyUI down)
   - 503: Service unavailable

6. Log error details

7. Return JSON error response
```

---

## API Design

### RESTful Principles

1. **Resource-Based URLs**
   - `/api/v1/generate` (not `/api/v1/create_image`)
   - `/api/v1/jobs/{id}` (not `/api/v1/get_job`)

2. **HTTP Verbs**
   - `POST /generate` - Create new generation job
   - `GET /jobs/{id}` - Retrieve job status
   - `GET /workflows` - List workflows
   - `POST /workflows` - Create workflow template

3. **Status Codes**
   - `200 OK` - Successful GET
   - `201 Created` - Successful POST (resource created)
   - `400 Bad Request` - Validation error
   - `404 Not Found` - Resource doesn't exist
   - `500 Internal Server Error` - Server failure
   - `503 Service Unavailable` - ComfyUI down

4. **Versioning**
   - URL-based: `/api/v1/...`
   - Allows future API changes without breaking clients

### Endpoint Design

#### Image Generation Endpoints

```
POST /api/v1/generate
  Description: Generate a single image
  Request Body: GenerateImageRequest
  Response: ImageResponse (201 Created)

POST /api/v1/generate/batch
  Description: Generate multiple images
  Request Body: BatchGenerateRequest
  Response: BatchImageResponse (201 Created)

GET /api/v1/generate/{job_id}
  Description: Get generation job status
  Response: ImageResponse (200 OK)

GET /api/v1/generate/{job_id}/image
  Description: Download generated image
  Response: Binary image data (200 OK)
```

#### Workflow Endpoints (Future)

```
GET /api/v1/workflows
  Description: List available workflow templates
  Response: List[WorkflowTemplate] (200 OK)

POST /api/v1/workflows
  Description: Create custom workflow template
  Request Body: WorkflowTemplate
  Response: WorkflowTemplate (201 Created)

POST /api/v1/workflows/{id}/execute
  Description: Execute a workflow template
  Request Body: WorkflowParameters
  Response: ImageResponse (201 Created)
```

#### Health & Monitoring

```
GET /health
  Description: Service health check
  Response: {"status": "healthy", "comfyui": "connected"}

GET /metrics
  Description: Service metrics (future)
  Response: {"requests": 1234, "avg_time": 15.2, ...}
```

---

## Security Considerations

### Current State (Development)
- **No authentication** - Open access
- **No rate limiting** - Unlimited requests
- **No input sanitization** - Basic validation only

### Future Security Features

#### 1. Authentication & Authorization
```
Strategy: JWT-based authentication
- Bearer token in Authorization header
- User registration/login endpoints
- Role-based access control (RBAC)
  - Free tier: 10 images/day
  - Pro tier: 1000 images/day
  - Admin: Unlimited + workflow management
```

#### 2. Rate Limiting
```
Strategy: Token bucket algorithm
- Per-user limits based on tier
- IP-based limits for unauthenticated requests
- 429 Too Many Requests response
```

#### 3. Input Validation & Sanitization
```
Current: Pydantic validation (types, ranges)
Future:
  - Prompt content filtering (no malicious prompts)
  - File upload validation (size, type)
  - SQL injection prevention (if DB added)
  - XSS prevention in responses
```

#### 4. CORS Configuration
```
Current: Permissive (development)
Production:
  - Whitelist specific origins
  - Restrict HTTP methods
  - Limit headers
```

#### 5. Secrets Management
```
Current: N/A (no secrets yet)
Future:
  - Environment variables for API keys
  - Vault for sensitive data
  - No secrets in code/git
```

---

## Scalability & Performance

### Current Architecture (Single Instance)
```
Capacity:
  - Single ComfyUI instance
  - Single FastAPI instance
  - Handles ~1-5 concurrent requests
  - Limited by GPU/CPU availability
```

### Scaling Strategies (Future)

#### Horizontal Scaling
```
┌──────────┐
│ Client   │
└────┬─────┘
     │
┌────▼──────────────┐
│ Load Balancer     │
│ (nginx/traefik)   │
└───┬───────┬───────┘
    │       │
┌───▼───┐ ┌─▼─────┐
│ API 1 │ │ API 2 │
└───┬───┘ └───┬───┘
    │         │
┌───▼─────────▼───┐
│ ComfyUI Cluster │
│ (w/ job queue)  │
└─────────────────┘
```

#### Optimization Strategies

1. **Caching**
   - Redis for job status
   - CDN for generated images
   - Model caching in ComfyUI

2. **Job Queue**
   - Celery or RQ for background tasks
   - Separate worker processes
   - Priority queuing

3. **Database**
   - PostgreSQL for job history
   - User management
   - Analytics

4. **Async Processing**
   - Return job_id immediately
   - Client polls for status
   - WebSocket for real-time updates

5. **Resource Management**
   - Connection pooling (HTTPX)
   - Request timeouts
   - Graceful shutdown

---

## Technology Choices

### Why FastAPI?
- **Performance:** ASGI-based, async support
- **Developer Experience:** Auto-generated docs, type hints
- **Validation:** Built-in Pydantic integration
- **Modern:** Current best practice for Python APIs

### Why HTTPX?
- **Async Support:** Non-blocking HTTP requests
- **HTTP/2:** Better performance than requests library
- **Similar API:** Familiar to requests users
- **Timeouts:** Better timeout handling

### Why Pydantic V2?
- **Fast:** Rust-based core (significant speed improvement)
- **Type Safety:** Strong typing with IDE support
- **Validation:** Comprehensive validation rules
- **Serialization:** Easy JSON conversion

### Why Not...?

**Django REST Framework:**
- Heavier framework
- Synchronous by default
- More boilerplate

**Flask:**
- Requires more setup for async
- Less modern API design patterns
- Manual validation

**GraphQL:**
- Overkill for simple CRUD operations
- REST is simpler for this use case
- Clients prefer REST for image generation

---

## Deployment Architecture

### Development Environment
```
Docker Devcontainer
  ├─ Python 3.11
  ├─ Poetry (dependencies)
  ├─ ComfyUI (cloned, running)
  └─ FastAPI (running with auto-reload)
```

### Production Environment (Future)
```
Docker Compose:
  - api_service (FastAPI)
  - comfyui_service (ComfyUI)
  - redis (caching, job queue)
  - postgres (persistence)
  - nginx (reverse proxy)

Kubernetes (Advanced):
  - API Deployment (replicas: 3)
  - ComfyUI StatefulSet (GPU nodes)
  - Redis Service
  - Postgres StatefulSet
  - Ingress (HTTPS, load balancing)
```

---

## Monitoring & Observability (Future)

### Logging
- **Structured Logging:** JSON format
- **Log Levels:** DEBUG, INFO, WARNING, ERROR
- **Context:** Request ID, user ID, timestamps
- **Aggregation:** ELK stack or CloudWatch

### Metrics
- **Request Rate:** Requests per second
- **Latency:** P50, P95, P99
- **Error Rate:** 4xx and 5xx responses
- **ComfyUI Health:** Uptime, response time
- **Resource Usage:** CPU, memory, GPU

### Tracing
- **Distributed Tracing:** OpenTelemetry
- **Span Tracking:** API → Service → ComfyUI
- **Performance Profiling:** Identify bottlenecks

---

**Document Version:** 1.0
**Status:** Initial Design
**Next Review:** After Phase 1 implementation
