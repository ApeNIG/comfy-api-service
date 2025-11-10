# Docker Compose Quick Start

Get the full ComfyUI API Service running with all features in under 5 minutes.

---

## Prerequisites

- **Docker** 20.10+ installed
- **Docker Compose** 2.0+ installed
- **8GB RAM** minimum (16GB recommended)
- **50GB disk space** for ComfyUI models
- **(Optional) NVIDIA GPU** for ComfyUI image generation

---

## Quick Start (3 Commands)

### Option 1: Full Stack (Recommended for Testing Full Features)

This starts everything: Redis, MinIO, API, and Worker (no ComfyUI GPU required for testing)

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Start infrastructure and services
docker-compose up -d redis minio api worker

# 3. Verify everything is running
docker-compose ps
```

**Access:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics
- MinIO Console: http://localhost:9001 (admin/minioadmin)

### Option 2: Infrastructure Only (For Local Development)

Start just Redis and MinIO, run API/worker locally:

```bash
# 1. Start infrastructure
docker-compose -f docker-compose.dev.yml up -d

# 2. Run API locally
export REDIS_URL=redis://localhost:6379
export MINIO_ENDPOINT=localhost:9000
poetry run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Run worker locally (in another terminal)
export REDIS_URL=redis://localhost:6379
export MINIO_ENDPOINT=localhost:9000
poetry run arq apps.worker.main.WorkerSettings
```

### Option 3: Full Stack with ComfyUI (GPU Required)

**Requirements:** NVIDIA GPU with Docker GPU support

```bash
# 1. Verify GPU support
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 2. Start everything including ComfyUI
docker-compose up -d

# 3. Wait for ComfyUI to download models (2-3 minutes first time)
docker-compose logs -f comfyui

# 4. Verify ComfyUI is ready
curl http://localhost:8188/system_stats
```

---

## Automated Deployment Script

Use the automated deployment script for a guided setup:

```bash
./scripts/deploy.sh staging
```

This script:
- ✅ Checks prerequisites (Docker, Docker Compose)
- ✅ Validates .env file
- ✅ Builds Docker images
- ✅ Starts services in correct order
- ✅ Waits for health checks
- ✅ Runs smoke tests
- ✅ Creates admin user and API key
- ✅ Displays service URLs

**Output:**
```
==================================================
Deployment Complete!
==================================================

Service URLs:
  - API:         http://localhost:8000
  - API Docs:    http://localhost:8000/docs
  - Health:      http://localhost:8000/health
  - Metrics:     http://localhost:8000/metrics
  - MinIO UI:    http://localhost:9001

Next steps:
  1. Run full validation: ./scripts/validate.sh
  2. View logs: docker-compose logs -f api worker
  3. Run integration tests: poetry run pytest tests/integration/ -v
```

---

## Validation

After deployment, run the validation script:

```bash
./scripts/validate.sh
```

**Expected output:**
```
==================================================
Validation Summary
==================================================

Passed:  18
Failed:  0
Skipped: 2

Success Rate: 100% (18/18)

✓ All tests passed!
```

This validates:
- ✅ Docker containers running
- ✅ Redis connectivity
- ✅ MinIO bucket exists
- ✅ API health endpoints
- ✅ Metrics endpoint
- ✅ Job submission
- ✅ Idempotency
- ✅ Worker startup

---

## Testing the API

### 1. Create Admin User and API Key

```bash
# Create admin user
curl -X POST http://localhost:8000/admin/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "role": "internal"
  }'

# Save the user_id from response, then create API key
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID_FROM_ABOVE",
    "name": "Test Key"
  }'

# Save the api_key from response!
```

### 2. Submit a Test Job

**Without ComfyUI (will queue but not complete):**
```bash
export API_KEY="cui_sk_YOUR_KEY_HERE"

curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "model": "dreamshaper_8.safetensors",
    "width": 512,
    "height": 512,
    "steps": 20
  }'
```

**Response:**
```json
{
  "job_id": "job_abc123...",
  "status": "queued",
  "created_at": "2025-11-07T10:00:00Z",
  "priority": 0
}
```

### 3. Check Job Status

```bash
export JOB_ID="job_abc123..."

curl http://localhost:8000/api/v1/jobs/$JOB_ID \
  -H "Authorization: Bearer $API_KEY"
```

**Response:**
```json
{
  "job_id": "job_abc123...",
  "status": "queued",  // or "running", "succeeded", "failed"
  "created_at": "2025-11-07T10:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

**With ComfyUI running:** Job will complete and return artifact URLs!

---

## Service Management

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f worker
docker-compose logs -f comfyui

# Last 100 lines
docker-compose logs --tail=100 api
```

### Check Service Status

```bash
docker-compose ps
```

**Expected output:**
```
NAME                STATUS              PORTS
comfyui-api         Up 2 minutes        0.0.0.0:8000->8000/tcp
comfyui-worker      Up 2 minutes
redis               Up 2 minutes        0.0.0.0:6379->6379/tcp
minio               Up 2 minutes        0.0.0.0:9000-9001->9000-9001/tcp
```

### Restart Services

```bash
# Restart specific service
docker-compose restart api
docker-compose restart worker

# Restart all
docker-compose restart
```

### Scale Workers

```bash
# Scale to 3 workers
docker-compose up -d --scale worker=3

# Verify
docker-compose ps | grep worker
```

### Stop Services

```bash
# Stop all (preserves data)
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Stop and remove everything including volumes (DESTRUCTIVE!)
docker-compose down -v
```

---

## Troubleshooting

### API Won't Start

**Check logs:**
```bash
docker-compose logs api
```

**Common issues:**
- Port 8000 already in use → Change in docker-compose.yml or stop conflicting process
- Redis connection failed → Ensure Redis container is running
- MinIO connection failed → Ensure MinIO container is running

**Fix:**
```bash
# Restart services
docker-compose down
docker-compose up -d redis minio
sleep 5
docker-compose up -d api worker
```

### Worker Not Processing Jobs

**Check logs:**
```bash
docker-compose logs worker
```

**Common issues:**
- Not connected to Redis → Check REDIS_URL in .env
- ComfyUI unreachable → Check COMFYUI_URL in .env
- Crash recovery running → Wait 30 seconds for recovery to complete

**Fix:**
```bash
docker-compose restart worker
docker-compose logs -f worker
```

### ComfyUI Not Starting

**Check logs:**
```bash
docker-compose logs comfyui
```

**Common issues:**
- GPU not detected → Verify nvidia-docker installed
- Out of memory → Reduce model size or increase GPU memory
- Models downloading → Wait 2-3 minutes for first-time download

**Verify GPU:**
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Port Conflicts

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find process using port
lsof -i :8000
# or
netstat -tulpn | grep 8000

# Kill process or change port in docker-compose.yml
docker-compose down
# Edit docker-compose.yml: ports: ["8001:8000"]
docker-compose up -d
```

### Redis Connection Errors

**Error:** `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# Check Redis is healthy
docker-compose exec redis redis-cli ping
# Should return: PONG

# Restart Redis
docker-compose restart redis
```

### MinIO Bucket Not Found

**Error:** `Bucket 'comfyui-artifacts' does not exist`

**Solution:**
```bash
# Create bucket manually
docker-compose exec minio mc alias set myminio http://localhost:9000 minioadmin minioadmin
docker-compose exec minio mc mb myminio/comfyui-artifacts
docker-compose exec minio mc anonymous set download myminio/comfyui-artifacts
```

---

## Configuration

### Environment Variables (.env)

**Minimal configuration:**
```env
# Redis
REDIS_URL=redis://redis:6379

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=comfyui-artifacts

# ComfyUI
COMFYUI_URL=http://comfyui:8188

# Features
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
JOBS_ENABLED=true
```

**Production configuration:**
```env
# Use managed services
REDIS_URL=redis://:password@your-redis.cloud:6379
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=your-aws-access-key
MINIO_SECRET_KEY=your-aws-secret-key
MINIO_USE_SSL=true

# Security
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## What Each Service Does

| Service | Purpose | Required | Port |
|---------|---------|----------|------|
| **redis** | Job queue, cache, rate limiting | Yes | 6379 |
| **minio** | Artifact storage (S3-compatible) | Yes | 9000, 9001 |
| **api** | FastAPI REST API | Yes | 8000 |
| **worker** | Process jobs from queue | Yes | - |
| **comfyui** | GPU image generation | Optional | 8188 |

**Without ComfyUI:**
- ✅ API works
- ✅ Jobs can be submitted
- ✅ Jobs are queued
- ❌ Jobs won't complete (no backend to process them)

**With ComfyUI:**
- ✅ Everything works end-to-end
- ✅ Jobs complete successfully
- ✅ Images are generated and stored

---

## Next Steps

After successful deployment:

1. **Week 1: Validate Functionality**
   - Run integration tests: `poetry run pytest tests/integration/ -v`
   - Submit test jobs
   - Monitor metrics: http://localhost:8000/metrics
   - Check logs: `docker-compose logs -f`

2. **Week 2: Performance Testing**
   - Load testing (see ROADMAP.md Option 4)
   - Monitor resource usage: `docker stats`
   - Tune worker concurrency
   - Optimize Redis/MinIO

3. **Production Deployment**
   - Follow [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
   - Use managed services (AWS ElastiCache, S3)
   - Set up monitoring (Prometheus + Grafana)
   - Configure SSL/HTTPS

---

## Useful Commands Cheatsheet

```bash
# Start everything
docker-compose up -d

# Start without ComfyUI
docker-compose up -d redis minio api worker

# View logs
docker-compose logs -f api worker

# Check status
docker-compose ps

# Restart service
docker-compose restart api

# Scale workers
docker-compose up -d --scale worker=3

# Stop everything
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Clean everything (DESTRUCTIVE)
docker-compose down -v
docker system prune -a

# Run validation
./scripts/validate.sh

# View metrics
curl http://localhost:8000/metrics

# Health check
curl http://localhost:8000/health
```

---

## Success Criteria

✅ **Deployment Successful When:**
- All containers running: `docker-compose ps` shows "Up"
- Health check passes: `curl http://localhost:8000/health` returns `{"status":"healthy"}`
- Validation passes: `./scripts/validate.sh` shows 100% pass rate
- Can create users and API keys
- Can submit jobs (even if ComfyUI not running)
- Metrics endpoint working: `curl http://localhost:8000/metrics`

---

**Questions?** Check:
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Full deployment guide
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - Cloud deployment
- [DOCKER.md](DOCKER.md) - Detailed Docker documentation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues

**Status:** ✅ Ready to deploy with Docker Compose!
