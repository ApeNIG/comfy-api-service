# Get Started in 2 Minutes

**You just saw the API working!** Now let's get the full stack running with all features.

---

## What You Need

✅ **Docker** installed on your host machine
✅ **Docker Compose** installed
✅ **8GB RAM** minimum
✅ **(Optional) NVIDIA GPU** for image generation

---

## 3 Steps to Full Functionality

### Step 1: Copy Environment File (5 seconds)

```bash
cp .env.example .env
```

That's it! The defaults work for local testing.

### Step 2: Start Services (1 command, 30 seconds)

```bash
docker-compose up -d redis minio api worker
```

**What this starts:**
- ✅ **Redis** - Job queue, caching, rate limiting
- ✅ **MinIO** - S3-compatible artifact storage
- ✅ **API** - FastAPI REST API (port 8000)
- ✅ **Worker** - Background job processor

### Step 3: Verify It's Working (10 seconds)

```bash
# Check all services are running
docker-compose ps

# Test health endpoint
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "api_version": "1.0.0",
  "comfyui_status": "disconnected",
  ...
}
```

---

## You're Done! 🎉

**Your API is now running with:**
- ✅ Job queue (Redis)
- ✅ Artifact storage (MinIO)
- ✅ API server
- ✅ Worker process
- ✅ Authentication (enabled)
- ✅ Rate limiting (enabled)
- ✅ Monitoring (Prometheus metrics)

**Access your API:**
- **API Docs:** http://localhost:8000/docs ← **Open this!**
- **Health:** http://localhost:8000/health
- **Metrics:** http://localhost:8000/metrics
- **MinIO Console:** http://localhost:9001 (admin/minioadmin)

---

## Test End-to-End Functionality

### 1. Create Admin User

```bash
curl -X POST http://localhost:8000/admin/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "role": "internal"
  }'
```

**Copy the `user_id` from the response!**

### 2. Create API Key

```bash
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_ID_FROM_STEP_1",
    "name": "Test Key"
  }'
```

**Copy the `api_key` from the response - it won't be shown again!**

### 3. Submit a Job

```bash
export API_KEY="YOUR_API_KEY_HERE"

curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "model": "dreamshaper_8.safetensors",
    "width": 512,
    "height": 512
  }'
```

**Copy the `job_id` from the response!**

### 4. Check Job Status

```bash
curl http://localhost:8000/api/v1/jobs/YOUR_JOB_ID \
  -H "Authorization: Bearer $API_KEY"
```

**Status will be:**
- `queued` - Waiting for worker (if ComfyUI not running)
- `running` - Being processed
- `succeeded` - Complete! (if ComfyUI is running)
- `failed` - Error occurred

---

## What's Working vs. What's Not

### ✅ Working Now:
- API endpoints (all of them!)
- Job submission and queueing
- User and API key management
- Authentication and authorization
- Rate limiting (try exceeding the limit!)
- Metrics and monitoring
- Health checks
- Idempotency
- Job cancellation
- Crash recovery

### ❌ Not Working Yet:
- **Actual image generation** - Requires ComfyUI with GPU

**Why?** Jobs will be queued but won't complete because there's no ComfyUI backend to process them. This is fine for testing the API itself!

---

## Add ComfyUI for Full Image Generation (Optional)

**Requirements:** NVIDIA GPU with Docker GPU support

```bash
# 1. Verify GPU support
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# 2. Start ComfyUI
docker-compose up -d comfyui

# 3. Wait for models to download (2-3 minutes first time)
docker-compose logs -f comfyui

# 4. Verify it's ready
curl http://localhost:8188/system_stats
```

Now jobs will complete and generate actual images!

---

## View What's Happening

### Watch Logs

```bash
# All services
docker-compose logs -f

# Just API and Worker
docker-compose logs -f api worker

# Just Worker (to see job processing)
docker-compose logs -f worker
```

### Check Service Status

```bash
docker-compose ps
```

### Monitor Metrics

```bash
# View raw Prometheus metrics
curl http://localhost:8000/metrics

# Or set up Grafana (optional)
docker run -d -p 3000:3000 grafana/grafana:latest
# Open http://localhost:3000 (admin/admin)
```

---

## Stop Services

```bash
# Stop everything (data preserved)
docker-compose down

# Stop and remove data (DESTRUCTIVE!)
docker-compose down -v
```

---

## Automated Deployment (Alternative)

Instead of manual steps, use the automated script:

```bash
./scripts/deploy.sh staging
```

This does everything automatically:
- ✅ Checks prerequisites
- ✅ Builds images
- ✅ Starts services
- ✅ Runs smoke tests
- ✅ Creates admin user/API key
- ✅ Displays URLs

Then validate:

```bash
./scripts/validate.sh
```

---

## Troubleshooting

### Port Already in Use

**Error:** `Bind for 0.0.0.0:8000 failed`

**Fix:**
```bash
# Find what's using port 8000
lsof -i :8000

# Kill it or change port in docker-compose.yml
docker-compose down
# Edit docker-compose.yml: "8001:8000"
docker-compose up -d
```

### Services Won't Start

**Fix:**
```bash
# Check Docker is running
docker ps

# Restart Docker daemon
# (varies by OS - check Docker docs)

# Try again
docker-compose up -d
```

### Jobs Stuck in Queue

**This is expected without ComfyUI!** Jobs will stay `queued` until you add the ComfyUI backend.

To add it:
```bash
docker-compose up -d comfyui
```

---

## What's Next?

1. ✅ **You're running the full API!** Explore http://localhost:8000/docs

2. **Try the features:**
   - Create users with different roles (FREE, PRO, INTERNAL)
   - Test rate limiting (exceed your quota)
   - Submit multiple jobs
   - Cancel a job
   - Test idempotency (submit same job twice with same key)

3. **Production deployment:**
   - See [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) for detailed docs
   - See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) for AWS/GCP/Azure

4. **Add features:**
   - See [ROADMAP.md](ROADMAP.md) for Options 3-6:
     - Usage analytics & billing
     - Load testing & optimization
     - Documentation & SDK
     - Security hardening

---

## Quick Reference

| What | URL | Credentials |
|------|-----|-------------|
| **API Docs** | http://localhost:8000/docs | None |
| **API Health** | http://localhost:8000/health | None |
| **Metrics** | http://localhost:8000/metrics | None |
| **MinIO Console** | http://localhost:9001 | admin/minioadmin |
| **ComfyUI** | http://localhost:8188 | None |

---

## Commands Cheatsheet

```bash
# Start services
docker-compose up -d redis minio api worker

# Start with ComfyUI
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api worker

# Restart service
docker-compose restart api

# Stop everything
docker-compose down

# Clean everything
docker-compose down -v

# Run validation
./scripts/validate.sh
```

---

**Status:** ✅ Ready to run!

**Next:** Run `docker-compose up -d redis minio api worker` on your host machine with Docker installed!
