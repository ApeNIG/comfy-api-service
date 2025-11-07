# Docker Compose Setup

This document describes how to run the ComfyUI API Service using Docker Compose.

---

## Quick Start

### Full Stack (Production-like)

Runs all services: Redis, MinIO, ComfyUI, API, and Worker.

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Stop all services
docker-compose down
```

**Requirements:**
- Docker with GPU support (for ComfyUI)
- NVIDIA Container Toolkit
- ~10GB disk space for models

**Services:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
- ComfyUI: http://localhost:8188
- Redis: localhost:6379

---

## Development Setup

### Option 1: Infrastructure Only (Recommended for Development)

Runs only Redis + MinIO. Run API/worker locally with Poetry.

```bash
# Start infrastructure
docker-compose -f docker-compose.dev.yml up -d

# In another terminal, run API locally
poetry run uvicorn apps.api.main:app --reload --port 8000

# In another terminal, run worker locally
poetry run arq apps.worker.main.WorkerSettings
```

**Benefits:**
- Fast iteration (no container rebuilds)
- Easy debugging
- Hot reload for API changes

---

### Option 2: Full Stack

Use the main docker-compose.yml for production-like testing.

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# Follow logs
docker-compose logs -f api worker
```

---

## Service Details

### Redis
- **Image:** redis:7-alpine
- **Port:** 6379
- **Purpose:** Job queue, caching, rate limiting
- **Health Check:** `redis-cli ping`

### MinIO
- **Image:** minio/minio:latest
- **Ports:** 9000 (API), 9001 (Console)
- **Credentials:** minioadmin / minioadmin
- **Purpose:** Artifact storage (S3-compatible)
- **Bucket:** comfyui-artifacts (auto-created in dev setup)

### ComfyUI
- **Image:** yanwk/comfyui-boot:latest
- **Port:** 8188
- **Purpose:** Image generation backend
- **GPU:** Requires NVIDIA GPU with Container Toolkit
- **Startup Time:** ~60 seconds (model loading)

### API
- **Build:** Local Dockerfile
- **Port:** 8000
- **Purpose:** FastAPI REST API
- **Environment:** Configured for containerized services

### Worker
- **Build:** Local Dockerfile
- **Command:** `arq apps.worker.main.WorkerSettings`
- **Purpose:** ARQ job processor
- **Concurrency:** Configurable (default: 2)

---

## Environment Variables

### API & Worker

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379` | Redis connection URL |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO server endpoint |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `COMFYUI_URL` | `http://comfyui:8188` | ComfyUI backend URL |
| `JOBS_ENABLED` | `true` | Enable async job queue |
| `AUTH_ENABLED` | `false` | Enable API key auth |
| `RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |

---

## Testing the Setup

### 1. Check Service Health

```bash
# Check all services are healthy
docker-compose ps

# Test Redis
redis-cli -h localhost -p 6379 ping
# Should return: PONG

# Test MinIO
curl http://localhost:9000/minio/health/live
# Should return: OK

# Test API
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}

# Test ComfyUI
curl http://localhost:8188/system_stats
# Should return: JSON with system stats
```

### 2. Submit a Test Job

```bash
# Submit a job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "model": "dreamshaper_8.safetensors",
    "width": 512,
    "height": 512
  }'

# Response: {"job_id": "abc123", ...}

# Check job status
curl http://localhost:8000/api/v1/jobs/abc123
```

### 3. Monitor Worker Logs

```bash
# Follow worker logs
docker-compose logs -f worker

# You should see:
# - Job picked up from queue
# - Progress updates
# - Artifact uploads
# - Job completion
```

---

## Troubleshooting

### ComfyUI Not Starting

**Symptom:** ComfyUI container exits or health check fails

**Solutions:**
1. Check GPU availability:
   ```bash
   nvidia-smi
   docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
   ```

2. Check ComfyUI logs:
   ```bash
   docker-compose logs comfyui
   ```

3. Increase startup timeout in health check:
   ```yaml
   start_period: 120s  # Give more time for model loading
   ```

### Worker Crash Recovery

**Symptom:** Jobs stuck in "running" state after worker crash

**Solution:** Restart worker - crash recovery runs automatically:
```bash
docker-compose restart worker

# Check logs
docker-compose logs worker | grep "crash recovery"
# Should show: "Crash recovery complete: failed=X, skipped=Y"
```

### MinIO Bucket Not Created

**Symptom:** API errors about missing bucket

**Solution:**
```bash
# Access MinIO console: http://localhost:9001
# Login: minioadmin / minioadmin
# Create bucket: comfyui-artifacts
# Set policy: Public (read-only)

# Or use mc CLI:
docker run --rm --network host minio/mc \
  mc mb local/comfyui-artifacts
```

### Redis Connection Refused

**Symptom:** API/worker can't connect to Redis

**Solution:**
```bash
# Check Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
redis-cli -h localhost -p 6379 ping
```

### API/Worker Can't Reach Services

**Symptom:** Connection refused errors in API/worker logs

**Solution:** Ensure services are on the same network:
```bash
# Check networks
docker network ls

# Inspect network
docker network inspect comfy-api-service_comfyui-network

# Verify all containers are connected
```

---

## Production Considerations

### 1. Security

**DO NOT use default credentials in production!**

```yaml
environment:
  # Change these!
  MINIO_ROOT_USER: ${MINIO_USER}
  MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}

  # Enable auth
  AUTH_ENABLED: true
  RATE_LIMIT_ENABLED: true
```

### 2. Persistence

Volumes are used for data persistence:
- `redis_data` - Redis persistence (AOF)
- `minio_data` - MinIO artifacts
- `comfyui_models` - Downloaded models (~5-10GB)
- `comfyui_output` - Generated images

**Backup important data:**
```bash
# Backup MinIO data
docker run --rm \
  -v comfy-api-service_minio_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/minio-backup.tar.gz /data
```

### 3. Scaling

**Scale workers horizontally:**
```bash
# Run 3 worker instances
docker-compose up -d --scale worker=3
```

**Scale API instances (with load balancer):**
```bash
# Use docker-compose with nginx/traefik
docker-compose up -d --scale api=3
```

### 4. Monitoring

Add Prometheus + Grafana for monitoring:
```bash
# Metrics available at:
curl http://localhost:8000/metrics

# Add to docker-compose.yml:
# - prometheus
# - grafana
# - node-exporter
```

---

## Cleanup

### Remove All Services

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: Deletes all data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Clean Development Setup

```bash
docker-compose -f docker-compose.dev.yml down -v
```

---

## Next Steps

- Read [SPRINT_2_PLAN.md](SPRINT_2_PLAN.md) for feature roadmap
- Check [SPRINT_1_TEST_RESULTS.md](SPRINT_1_TEST_RESULTS.md) for testing procedures
- See [README.md](README.md) for API usage examples
- Review [LIMITS.md](LIMITS.md) for rate limits and quotas (coming soon)

---

**Need Help?**
- API Documentation: http://localhost:8000/docs
- GitHub Issues: https://github.com/ApeNIG/comfy-api-service/issues
