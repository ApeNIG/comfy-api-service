# Troubleshooting Guide

Common issues and solutions for the ComfyUI API Service.

---

## Quick Diagnostics

Run these commands first to check system health:

```bash
# Check all containers are running
docker compose ps

# Check API health
curl http://localhost:8000/health

# Check logs for errors
docker compose logs --tail=50 api worker comfyui
```

---

## Image Generation Issues

### Issue: Worker Uploads 0-Byte Files

**Symptoms:**
- Job status shows "succeeded"
- Presigned URL points to empty file (0 bytes)
- No actual image data

**Root Cause:** Worker not downloading from ComfyUI (fixed in commit b954fe3)

**Solution:**

Check if you're running the latest code:

```bash
git pull origin main
docker compose build api worker --no-cache
docker compose up -d --force-recreate api worker
```

**Verify fix is deployed:**

```bash
docker exec comfyui-worker grep "Downloaded.*bytes" /app/apps/worker/main.py
# Should show: logger.info(f"[{job_id}] Downloaded {len(image_bytes)} bytes")
```

**Check worker logs:**

```bash
docker compose logs -f worker

# Should see:
# [j_xxx] Downloading image from: http://comfyui:8188/view?...
# [j_xxx] Downloaded 404202 bytes
# [j_xxx] Uploaded 404202 bytes to MinIO
```

---

### Issue: Workflow Validation Failed (HTTP 400)

**Symptoms:**
```json
{
  "error": {
    "type": "prompt_outputs_failed_validation",
    "message": "Workflow validation failed"
  }
}
```

**Root Cause:** Model or sampler not available in ComfyUI

**Solution:**

**1. Check available models:**

```bash
docker exec comfyui-backend ls -lh /opt/ComfyUI/models/checkpoints/

# Should show:
# v1-5-pruned-emaonly.ckpt
```

**2. Use correct model in request:**

```json
{
  "model": "v1-5-pruned-emaonly.ckpt",
  "sampler": "euler_ancestral"
}
```

**3. Verify API defaults match (apps/api/models/requests.py):**

```python
model: str = Field(default="v1-5-pruned-emaonly.ckpt")
EULER_A = "euler_ancestral"  # NOT "euler_a"
```

---

### Issue: Jobs Timing Out

**Symptoms:**
```
Job j_xxx did not complete within 600.0s
```

**Root Cause:** CPU mode or complex generation taking longer than timeout

**Check generation time:**

```bash
docker compose logs comfyui | grep "Prompt executed"
```

**Solution:**

**For CPU Mode** - Increase timeout:

Edit [apps/api/config.py](apps/api/config.py):
```python
comfyui_timeout: float = 1200.0  # 20 minutes for complex jobs
```

Rebuild:
```bash
docker compose build api --no-cache
docker compose up -d --force-recreate api
```

**Or reduce complexity:**

```json
{
  "steps": 10,     // Reduce from 20
  "width": 512,    // Keep small
  "height": 512
}
```

**Performance benchmarks:**

| Mode | Resolution | Steps | Time |
|------|------------|-------|------|
| GPU (RTX 3060) | 512x512 | 20 | ~5s |
| CPU (Quadro P2000) | 512x512 | 10 | ~9 min |
| CPU (Quadro P2000) | 512x512 | 20 | ~18 min |

---

### Issue: Generated Image is Corrupted or Invalid

**Symptoms:**
- Image won't open
- Shows broken image icon
- File size is tiny (<1KB)

**Diagnosis:**

```bash
# Check actual file in MinIO container
docker exec comfyui-minio ls -lh /data/comfyui-artifacts/jobs/j_xxx/

# Download and check with file command
curl "http://localhost:9000/comfyui-artifacts/jobs/j_xxx/image_0.png?..." -o test.png
file test.png
# Should show: PNG image data, 512 x 512, ...
```

**Common causes:**

1. **Worker uploaded before download completed** - Fixed in commit b954fe3
2. **Network interruption during download** - Check ComfyUI connectivity
3. **MinIO storage issue** - Check MinIO health

---

## Docker and Deployment Issues

### Issue: Code Changes Not Taking Effect

**Symptoms:**
- Modified code but behavior unchanged
- Old bugs still present after fix

**Root Cause:** Docker layer caching or old container still running

**Solution:**

**Correct rebuild sequence:**

```bash
# 1. Build with no cache
docker compose build api worker --no-cache

# 2. Force recreate containers (not just restart!)
docker compose up -d --force-recreate api worker
```

**Verify code is updated:**

```bash
# Check deployed code matches your changes
docker exec comfyui-worker cat /app/apps/worker/main.py | grep "your_change"
```

**Wrong way (won't work):**

```bash
docker compose build worker
docker compose restart worker  # ❌ Still uses old container
```

---

### Issue: Containers Won't Start

**Symptoms:**
```bash
docker compose ps
# Shows "Exited" or "Restarting"
```

**Diagnosis:**

```bash
# Check why container exited
docker compose logs api
docker compose logs worker
docker compose logs comfyui
```

**Common causes:**

**1. Port already in use:**

```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

Solution:
```bash
# Find what's using port 8000
lsof -i :8000
# or on Windows:
netstat -ano | findstr :8000

# Kill the process or change port in docker-compose.yml
```

**2. Missing environment variables:**

```
Error: REDIS_URL is required
```

Solution:
```bash
# Check .env file exists
ls -la .env

# Copy from example if missing
cp .env.example .env
```

**3. Out of disk space:**

```bash
docker system df

# Clean up if needed
docker system prune -a --volumes
```

---

### Issue: Cannot Connect Between Services

**Symptoms:**
- API cannot reach ComfyUI
- Worker cannot reach Redis
- "Connection refused" errors

**Diagnosis:**

**1. Check all services are on same network:**

```bash
docker compose ps
# All should show "Up" status

docker network inspect comfy-api-service_default
# Should list all containers
```

**2. Test connectivity from inside containers:**

```bash
# From API to ComfyUI
docker exec comfyui-api curl http://comfyui:8188/queue

# From API to Redis
docker exec comfyui-api redis-cli -h redis ping

# From API to MinIO
docker exec comfyui-api curl http://minio:9000/minio/health/live
```

**3. Check service names in .env:**

```bash
# Inside containers, use service names (not localhost)
COMFYUI_URL=http://comfyui:8188  # ✅ Correct
REDIS_URL=redis://redis:6379     # ✅ Correct

# NOT:
COMFYUI_URL=http://localhost:8188  # ❌ Won't work
```

---

## ComfyUI Issues

### Issue: ComfyUI Won't Start

**Symptoms:**
```bash
docker compose logs comfyui
# Shows errors or exits immediately
```

**Common causes:**

**1. GPU not available (when not using --cpu flag):**

```
RuntimeError: CUDA out of memory
# or
RuntimeError: No CUDA GPUs are available
```

Solution - Use CPU mode:
```yaml
# docker-compose.yml
comfyui:
  command: /opt/ai-dock/bin/supervisor-comfyui.sh --cpu
```

**2. Model download failed:**

```
Error: Cannot find model v1-5-pruned-emaonly.ckpt
```

Solution:
```bash
# Manually download model
docker exec comfyui-backend bash -c "
cd /opt/ComfyUI/models/checkpoints && \
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt
"

# Check it's there
docker exec comfyui-backend ls -lh /opt/ComfyUI/models/checkpoints/
```

**3. Out of memory (CPU mode):**

```
Killed
```

Solution - Increase Docker memory:
- Docker Desktop → Settings → Resources → Memory
- Set to at least 8GB for CPU mode

---

### Issue: ComfyUI Health Check Failing

**Symptoms:**
```json
{
  "comfyui_status": "disconnected"
}
```

**Diagnosis:**

```bash
# Check if ComfyUI is actually running
docker compose ps comfyui
# Should show "Up"

# Test ComfyUI directly
curl http://localhost:8188/queue
# Should return JSON

# From inside API container
docker exec comfyui-api curl http://comfyui:8188/queue
# Should return JSON
```

**If curl works but health check fails:**

Check health_check implementation in [apps/api/services/comfyui_client.py:114-143](apps/api/services/comfyui_client.py#L114-L143):

```python
# Should have retry logic with multiple endpoints
endpoints = ["/queue", "/system_stats", "/"]
for attempt in range(5):
    for endpoint in endpoints:
        try:
            response = await health_client.get(endpoint)
            if response.status_code == 200:
                return True
```

---

## Storage Issues (MinIO/S3)

### Issue: Cannot Access Generated Images

**Symptoms:**
- Presigned URL returns 403 Forbidden
- URL returns "Access Denied"

**Root Cause:** Presigned URL expired or MinIO configuration

**Diagnosis:**

```bash
# Check MinIO is running
docker compose ps minio
# Should show "Up (healthy)"

# Test MinIO health
curl http://localhost:9000/minio/health/live
# Should return 200 OK

# Check bucket exists
docker exec comfyui-minio mc ls local/comfyui-artifacts
```

**Solution:**

**1. Presigned URLs expire (default 1 hour):**

Request a new URL:
```bash
curl http://localhost:8000/api/v1/jobs/j_xxx
# Get fresh artifact URL
```

**2. MinIO credentials wrong:**

Check [.env](.env):
```bash
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

**3. Bucket policy issue:**

```bash
# Set bucket to public read (for testing)
docker exec comfyui-minio mc anonymous set download local/comfyui-artifacts
```

---

### Issue: MinIO Console Won't Load

**Symptoms:**
- http://localhost:9001 times out
- Cannot login to MinIO console

**Solution:**

```bash
# Check MinIO is listening on both ports
docker compose ps minio
# Should show: 0.0.0.0:9000->9000/tcp, 0.0.0.0:9001->9001/tcp

# Verify ports are mapped
docker port comfyui-minio
# Should show:
# 9000/tcp -> 0.0.0.0:9000
# 9001/tcp -> 0.0.0.0:9001

# Check logs
docker compose logs minio
```

Default credentials: `minioadmin` / `minioadmin`

---

## Redis Issues

### Issue: Jobs Not Processing

**Symptoms:**
- Jobs stuck in "queued" status
- Worker logs show nothing

**Diagnosis:**

```bash
# Check Redis is running
docker compose ps redis
# Should show "Up (healthy)"

# Check worker is running
docker compose ps worker
# Should show "Up"

# Check Redis queue
docker exec comfyui-redis redis-cli KEYS "*"
# Should show queue keys

# Check worker logs
docker compose logs -f worker
# Should show job processing
```

**Solution:**

**1. Worker crashed:**

```bash
docker compose restart worker
docker compose logs -f worker
```

**2. Redis connection issue:**

```bash
# Test Redis from worker
docker exec comfyui-worker redis-cli -h redis ping
# Should return: PONG
```

**3. Jobs in dead letter queue:**

```bash
# Check for failed jobs
docker exec comfyui-redis redis-cli KEYS "arq:queue*"

# Flush and retry
docker exec comfyui-redis redis-cli FLUSHALL
```

---

## Devcontainer Issues

### Issue: Cannot Access Services from Host

**Symptoms:**
- `curl http://localhost:8000` fails from Windows/Mac host
- Works from inside devcontainer

**Root Cause:** Running Docker Compose inside VSCode devcontainer creates nested network

**Solution:**

**Test from inside Docker network:**

```bash
# From host terminal
docker exec comfyui-api curl http://localhost:8000/health
```

**Or forward ports in devcontainer:**

`.devcontainer/devcontainer.json`:
```json
{
  "forwardPorts": [8000, 9000, 9001, 8188]
}
```

Then access via forwarded ports in VSCode.

---

## Performance Issues

### Issue: Image Generation Very Slow

**Expected times:**

| Hardware | Mode | 512x512 @ 20 steps |
|----------|------|-------------------|
| RTX 3060 | GPU | ~5 seconds |
| RTX 4090 | GPU | ~2 seconds |
| Quadro P2000 | CPU | ~18 minutes |
| No GPU | CPU | ~15-20 minutes |

**If slower than expected:**

**1. Check if GPU is actually being used:**

```bash
# Should show GPU activity during generation
nvidia-smi

# Check ComfyUI logs
docker compose logs comfyui | grep -i "cpu\|gpu\|cuda"
```

**2. Check CPU mode flag:**

```bash
docker compose config | grep command
# Should NOT show --cpu if you have compatible GPU
```

**3. Reduce complexity:**

```json
{
  "steps": 10,      // Default 20
  "width": 512,     // Lower if needed
  "height": 512
}
```

---

## Logging and Debugging

### Useful Debugging Commands

```bash
# Follow all logs in real-time
docker compose logs -f

# Check specific service
docker compose logs -f worker

# Get last 100 lines
docker compose logs --tail=100 api

# Search logs
docker compose logs api | grep ERROR

# Check container resource usage
docker stats

# Inspect container
docker inspect comfyui-api

# Execute command in container
docker exec -it comfyui-worker bash

# Check environment variables
docker exec comfyui-api env | grep COMFYUI
```

### Enable Debug Logging

Edit [apps/api/main.py](apps/api/main.py):

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Rebuild and restart:
```bash
docker compose build api --no-cache
docker compose up -d --force-recreate api
```

---

## Getting Help

If none of these solutions work:

1. **Check recent commits:** `git log --oneline`
2. **Review BUGFIXES.md:** Known issues and solutions
3. **Check the logs:** Full container logs often reveal the issue
4. **Test components individually:**
   - Health: `curl http://localhost:8000/health`
   - Redis: `docker exec comfyui-redis redis-cli ping`
   - MinIO: `curl http://localhost:9000/minio/health/live`
   - ComfyUI: `curl http://localhost:8188/queue`

---

## Common Error Messages Reference

| Error Message | Location | Solution |
|---------------|----------|----------|
| "Worker uploading 0 bytes" | Worker logs | Update to commit b954fe3 or later |
| "prompt_outputs_failed_validation" | API response | Check model/sampler match ComfyUI |
| "did not complete within 600s" | Worker logs | Increase timeout or reduce steps |
| "ComfyUI service not available" | API response | Check ComfyUI is running |
| "Connection refused" | Any | Check service networking |
| "Port already allocated" | Docker compose | Kill process using port |
| "CUDA out of memory" | ComfyUI logs | Use CPU mode or reduce resolution |
| "No module named" | Container logs | Rebuild with --no-cache |

---

**See Also:**
- [BUGFIXES.md](BUGFIXES.md) - Detailed bug reports and fixes
- [COMFYUI_SETUP_GUIDE.md](COMFYUI_SETUP_GUIDE.md) - ComfyUI setup and CPU mode
- [QUICKSTART_WALKTHROUGH.md](QUICKSTART_WALKTHROUGH.md) - Getting started guide
