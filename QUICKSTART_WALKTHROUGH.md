# Quick Start Walkthrough

**Goal:** Get your ComfyUI API Service running in 3 steps

**Important:** Run these commands on your **host machine** (where Docker is installed), NOT in the dev container terminal.

---

## Prerequisites Check

Before starting, verify you have:

```bash
# Check Docker is installed
docker --version
# Should show: Docker version 20.x or higher

# Check Docker Compose is available
docker compose version
# Should show: Docker Compose version v2.x or higher
```

If these commands don't work, you need to install Docker Desktop first.

---

## Step 1: Environment Configuration (✅ Already Done!)

You already have a `.env` file. Let me show you what's configured:

**Location:** `/workspaces/comfy-api-service/.env`

**Key settings:**
- Redis: `localhost:6379` (will be auto-started)
- MinIO: `localhost:9000` (will be auto-started)
- ComfyUI: `localhost:8188` (optional - needs GPU)
- Auth: `disabled` (easy testing)
- Rate limiting: `disabled` (easy testing)

No changes needed! The defaults work perfectly for local testing.

---

## Step 2: Start the Services

Open a terminal **on your host machine** and navigate to the project directory:

```bash
# Navigate to your project (adjust path as needed)
cd /path/to/comfy-api-service

# Start services WITHOUT ComfyUI (no GPU needed)
docker compose up -d redis minio api worker
```

**What this does:**
1. ✅ Pulls Docker images (Redis, MinIO)
2. ✅ Builds your API and Worker images
3. ✅ Starts 4 containers in the background (`-d` = detached)
4. ✅ Creates a network for them to communicate

**Expected output:**
```
[+] Running 4/4
 ✔ Container comfyui-redis    Started
 ✔ Container comfyui-minio    Started
 ✔ Container comfyui-api      Started
 ✔ Container comfyui-worker   Started
```

**First time?** This will take 2-3 minutes to:
- Download Redis and MinIO images (~100MB total)
- Build your API/Worker images (~500MB)
- Start all services

---

## Step 3: Verify It's Working

### 3.1 Check Container Status

```bash
docker compose ps
```

**Expected output:**
```
NAME                IMAGE                      STATUS         PORTS
comfyui-api         comfy-api-service-api      Up (healthy)   0.0.0.0:8000->8000/tcp
comfyui-minio       minio/minio:latest         Up (healthy)   0.0.0.0:9000-9001->9000-9001/tcp
comfyui-redis       redis:7-alpine             Up (healthy)   0.0.0.0:6379->6379/tcp
comfyui-worker      comfy-api-service-worker   Up
```

All services should show `Up (healthy)` status.

### 3.2 Test Health Endpoint

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "api_version": "1.0.1",
  "timestamp": "2025-11-07T22:30:00Z",
  "comfyui_status": "disconnected",
  "redis_status": "connected",
  "minio_status": "connected",
  "features": {
    "jobs_enabled": true,
    "auth_enabled": false,
    "rate_limit_enabled": false,
    "websocket_enabled": true
  }
}
```

**Note:** `comfyui_status: "disconnected"` is expected - we didn't start ComfyUI (requires GPU).

### 3.3 Open API Documentation

Open your browser and go to:

👉 **http://localhost:8000/docs**

You'll see interactive Swagger UI with all available endpoints!

---

## 🎉 Success! What's Now Available

### Available Services:

| Service | URL | Purpose |
|---------|-----|---------|
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **Health Check** | http://localhost:8000/health | Service status |
| **Metrics** | http://localhost:8000/metrics | Prometheus metrics |
| **MinIO Console** | http://localhost:9001 | Storage admin (admin/minioadmin) |

### What You Can Do:

✅ **Submit jobs** (they'll queue but won't generate images without ComfyUI)
✅ **Test authentication** (currently disabled for easy testing)
✅ **Check metrics** (job counts, queue depth, etc.)
✅ **Explore API** (via /docs)

---

## Test the API (Quick Examples)

### Example 1: Submit a Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "width": 512,
    "height": 512
  }'
```

**Response:**
```json
{
  "job_id": "job_abc123xyz",
  "status": "queued",
  "created_at": "2025-11-07T22:30:00Z"
}
```

### Example 2: Check Job Status

```bash
# Replace JOB_ID with the ID from step 1
curl http://localhost:8000/api/v1/jobs/job_abc123xyz
```

**Response:**
```json
{
  "job_id": "job_abc123xyz",
  "status": "failed",
  "error": "ComfyUI backend is not available",
  "created_at": "2025-11-07T22:30:00Z"
}
```

**Expected:** Job will fail because ComfyUI isn't running. This is normal!

---

## View Logs (Debug Issues)

```bash
# View all logs
docker compose logs

# Follow logs in real-time
docker compose logs -f

# View specific service
docker compose logs -f api
docker compose logs -f worker
```

---

## Stop Services

```bash
# Stop all services (keeps data)
docker compose down

# Stop and remove all data (DESTRUCTIVE!)
docker compose down -v
```

---

## What About ComfyUI? (Optional)

**To generate actual images, you need:**

1. **NVIDIA GPU** with CUDA support
2. **nvidia-docker** runtime installed
3. Start ComfyUI:
   ```bash
   docker compose up -d comfyui
   ```

Without GPU, ComfyUI won't run - but **everything else works perfectly** for testing the API!

---

## Troubleshooting

### Issue: Port already in use

**Error:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Fix:**
```bash
# Find what's using the port
lsof -i :8000

# Kill the process or change the port in docker-compose.yml
# Change "8000:8000" to "8001:8000" to use port 8001 instead
```

### Issue: Services won't start

**Fix:**
```bash
# Check Docker is running
docker ps

# Restart Docker daemon (varies by OS)
# Then try again
docker compose up -d redis minio api worker
```

### Issue: API shows "unhealthy"

**Fix:**
```bash
# Check API logs
docker compose logs api

# Usually means Redis or MinIO isn't ready
# Wait 30 seconds and check again
docker compose ps
```

### Issue: Build fails

**Fix:**
```bash
# Clean build cache
docker compose build --no-cache api worker

# Then start services
docker compose up -d redis minio api worker
```

---

## Next Steps

Once services are running:

1. **Explore the API:** http://localhost:8000/docs
2. **Try submitting jobs** (they'll queue)
3. **Check metrics:** http://localhost:8000/metrics
4. **View MinIO console:** http://localhost:9001

**Want to add ComfyUI?** See [COMFYUI_SETUP_GUIDE.md](COMFYUI_SETUP_GUIDE.md)

**Production deployment?** See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)

---

## Summary Commands

```bash
# Start services
docker compose up -d redis minio api worker

# Check status
docker compose ps

# View logs
docker compose logs -f api worker

# Test health
curl http://localhost:8000/health

# Stop services
docker compose down
```

---

**Status:** Ready to run! 🚀

**Need help?** Open http://localhost:8000/docs and try the interactive examples!
