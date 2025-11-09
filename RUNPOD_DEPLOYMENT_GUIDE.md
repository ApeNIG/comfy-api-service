# RunPod GPU Deployment Guide

**Goal:** Deploy ComfyUI on a RunPod GPU instance and connect it to your API service

**Cost:** ~$0.12/hour (Spot) or ~$0.20/hour (On-Demand) - **only when running**

---

## Quick Summary

- ✅ **No charges when stopped** - You only pay when the pod is actively running
- ✅ **Per-second billing** - No minimum runtime charges
- ✅ **Expected cost:** $15-30/month for development (4 hours/day usage)
- ✅ **Auto-stop feature** - Automatically stop after idle period
- ✅ **Fast startup** - Resume in ~30 seconds

---

## Step 1: Create RunPod Account

### 1.1 Sign Up
1. Go to https://runpod.io
2. Click "Sign Up"
3. Create account (email or GitHub)
4. Verify email address

### 1.2 Add Payment Method
1. Go to "Billing" in sidebar
2. Add credit card or cryptocurrency
3. Add initial credits ($10 minimum recommended)

### 1.3 Set Up Billing Alerts (Optional but Recommended)
```
Settings → Billing → Budget Alerts
- Set daily limit: $2
- Set monthly limit: $50
- Email notifications: Enabled
```

---

## Step 2: Deploy ComfyUI Pod

### 2.1 Choose Pod Type

**For Development/Testing (Recommended):**
- Type: **Spot Instance**
- GPU: **RTX 4000 Ada** or **RTX 3060**
- Cost: ~$0.12-0.15/hour
- Risk: Can be interrupted (rare for these GPUs)

**For Production:**
- Type: **On-Demand**
- GPU: **RTX 4090** or **A40**
- Cost: ~$0.40-0.60/hour
- Guarantee: No interruptions

### 2.2 Create Pod from Template

1. **Navigate to Pods:**
   - Click "Pods" in sidebar
   - Click "+ Deploy"

2. **Select Template:**
   - Search for "ComfyUI"
   - Select "ComfyUI" official template
   - Or use custom Docker image: `ghcr.io/ai-dock/comfyui:latest`

3. **Configure Pod:**
   ```
   Pod Name: comfyui-api-backend
   GPU Type: RTX 4000 Ada (or RTX 3060)
   GPU Count: 1
   Container Disk: 20 GB (minimum)
   Volume Disk: 50 GB (for models)

   Expose HTTP Ports: 8188
   Expose TCP Ports: (leave empty)
   ```

4. **Environment Variables:**
   ```bash
   # Optional: Pre-download Stable Diffusion 1.5
   PRELOAD_MODELS=true
   MODEL_URL=https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt
   ```

5. **Advanced Settings:**
   ```
   ✅ Enable Auto-Stop after 30 minutes idle
   ✅ Enable SSH (for debugging)
   ❌ Enable Jupyter (not needed)
   ```

6. **Click "Deploy On-Demand"** or **"Deploy Spot"**

### 2.3 Wait for Deployment

**Timeline:**
- Pod creation: ~30 seconds
- Container startup: ~60 seconds
- Model download (first time): ~5-10 minutes
- Total first deployment: ~10-15 minutes
- Subsequent starts: ~30 seconds

**Status progression:**
```
Creating Pod → Starting → Running → Ready
```

---

## Step 3: Get Your ComfyUI URL

### 3.1 Find Pod URL

1. Go to "Pods" page
2. Click on your pod (should show "Running")
3. Look for "Connect" section
4. Copy the **HTTP Service URL**

**Example URLs:**
```
https://abc12345-8188.proxy.runpod.net
https://xyz67890-8188.proxy.runpod.net
```

**Important:** The URL format is:
```
https://{POD_ID}-8188.proxy.runpod.net
```

The `8188` is the ComfyUI port, automatically exposed.

### 3.2 Verify ComfyUI is Running

**Test in browser:**
```
Open: https://YOUR-POD-ID-8188.proxy.runpod.net
```

You should see the ComfyUI web interface!

**Test via API:**
```bash
curl https://YOUR-POD-ID-8188.proxy.runpod.net/queue
```

**Expected response:**
```json
{
  "queue_running": [],
  "queue_pending": []
}
```

---

## Step 4: Connect to Your API Service

### 4.1 Update .env File

Edit your local `.env` file:

```bash
# OLD (local ComfyUI)
COMFYUI_URL=http://localhost:8188

# NEW (RunPod)
COMFYUI_URL=https://YOUR-POD-ID-8188.proxy.runpod.net
```

**Replace `YOUR-POD-ID-8188.proxy.runpod.net` with your actual URL!**

### 4.2 Update Timeout (Optional)

RunPod GPUs are fast, but network latency is higher:

```bash
# Increase timeout slightly for cloud latency
COMFYUI_TIMEOUT=120.0  # 2 minutes (default was 600s for CPU mode)
```

### 4.3 Restart API and Worker

```bash
# Navigate to your project
cd /workspaces/comfy-api-service

# Restart services to pick up new .env
docker compose restart api worker

# Verify they restarted
docker compose ps
```

### 4.4 Verify Connection

**Test health endpoint:**
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "api_version": "1.0.1",
  "comfyui_status": "connected",  // ✅ Should be "connected"!
  "redis_status": "connected",
  "minio_status": "connected"
}
```

**If `comfyui_status` is "disconnected":**
1. Check COMFYUI_URL in .env is correct (https, not http)
2. Check RunPod pod is "Running" status
3. Check ComfyUI web interface loads in browser
4. Check API logs: `docker compose logs api`

---

## Step 5: Test Image Generation

### 5.1 Submit Test Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains, golden hour, photorealistic",
    "width": 512,
    "height": 512,
    "steps": 20,
    "model": "v1-5-pruned-emaonly.ckpt"
  }'
```

**Expected response:**
```json
{
  "job_id": "j_abc123xyz",
  "status": "queued",
  "created_at": "2025-11-08T12:34:56.789Z"
}
```

### 5.2 Monitor Job Progress

**Copy your job_id and check status:**
```bash
# Replace with your actual job_id
JOB_ID=j_abc123xyz

# Check status (repeat every few seconds)
curl http://localhost:8000/api/v1/jobs/$JOB_ID
```

**Expected timeline (GPU mode):**
- Queued → Processing: ~1 second
- Processing → Succeeded: ~3-5 seconds (RTX 4000 Ada)
- Total time: **~5-10 seconds** (vs 9 minutes in CPU mode!)

### 5.3 Download Generated Image

**When status is "succeeded":**
```json
{
  "job_id": "j_abc123xyz",
  "status": "succeeded",
  "result": {
    "artifacts": [
      {
        "url": "http://localhost:9000/comfyui-artifacts/jobs/j_abc123xyz/image_0.png?...",
        "seed": 123456789,
        "width": 512,
        "height": 512
      }
    ]
  }
}
```

**Download the image:**
```bash
# Copy the artifact URL from the response
curl "ARTIFACT_URL_HERE" -o generated_image.png

# Open it
# Windows: start generated_image.png
# Mac: open generated_image.png
# Linux: xdg-open generated_image.png
```

---

## Step 6: Managing Your Pod (Cost Control)

### 6.1 Stop Pod When Not in Use

**Via RunPod Dashboard:**
1. Go to "Pods" page
2. Find your pod
3. Click "Stop Pod" button
4. **Billing stops immediately!**

**Via API (Advanced):**
```bash
curl -X POST https://api.runpod.io/v2/pods/YOUR_POD_ID/stop \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 6.2 Start Pod When Needed

**Via RunPod Dashboard:**
1. Go to "Pods" page
2. Find your stopped pod
3. Click "Start Pod" button
4. Wait ~30 seconds for "Running" status
5. **Same URL, same models!**

**Update your API service:**
```bash
# No .env changes needed - URL stays the same!
# Just verify connection
curl http://localhost:8000/health
```

### 6.3 Enable Auto-Stop (Recommended)

**Edit pod settings:**
```
Settings → Auto-Stop
- Enable: ✅ Yes
- Idle time: 30 minutes
- Check interval: 5 minutes
```

**What this does:**
- Pod monitors GPU/CPU usage
- If idle for 30 minutes, automatically stops
- **Saves money during lunch breaks, overnight, weekends**

**Example savings:**
```
Without auto-stop: 24 hours × $0.15 = $3.60/day
With auto-stop (4 hours actual use): 4 hours × $0.15 = $0.60/day
Savings: $3.00/day = $90/month! 🎉
```

### 6.4 Monitor Costs

**Real-time cost tracking:**
1. Go to "Billing" page
2. View "Current Balance"
3. View "Daily Usage" chart
4. Set up alerts for budget limits

**Check pod runtime:**
```bash
# Via RunPod dashboard
Pods → Your Pod → "Runtime: 2h 34m"
```

---

## Step 7: Production Hardening

### 7.1 Enable Authentication (Critical for Production)

**Update .env:**
```bash
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true
```

**Generate API key:**
```bash
# From inside API container
docker exec comfyui-api python -c "
from apps.api.auth import create_api_key
key = create_api_key('production-client', 'PRO')
print(f'API Key: {key}')
"
```

**Restart services:**
```bash
docker compose restart api worker
```

**Test with API key:**
```bash
API_KEY=your-generated-key-here

curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"prompt": "test", "width": 512, "height": 512}'
```

### 7.2 Secure RunPod Pod

**Restrict access:**
```
Pod Settings → Network
- Disable public HTTP access
- Enable only API access from your server IP
```

**Or use RunPod VPN:**
- Set up RunPod's network isolation
- Access pod only via VPN tunnel

### 7.3 Set Up Monitoring

**Enable logging:**
```bash
# Add to .env
LOG_LEVEL=INFO
LOG_FORMAT=json
METRICS_ENABLED=true
```

**Monitor metrics:**
```bash
# Check Prometheus metrics
curl http://localhost:8000/metrics

# Key metrics:
# - generation_total: Total images generated
# - generation_latency_seconds: Generation time
# - comfy_queue_depth: Jobs waiting
```

---

## Cost Optimization Strategies

### Strategy 1: Spot Instances for Development
```
Cost: $0.12/hour
Usage: 4 hours/day × 20 days
Monthly: $9.60

vs On-Demand: $0.20/hour × 4 hours × 20 days = $16/month
Savings: $6.40/month (40% cheaper)
```

### Strategy 2: Auto-Stop After Idle
```
Without auto-stop: 8 hours/day × $0.12 = $0.96/day
With auto-stop: 4 hours/day × $0.12 = $0.48/day
Savings: 50%
```

### Strategy 3: Smaller GPU for Testing
```
RTX 3060 (12GB): $0.10/hour - Good for 512x512
RTX 4000 Ada (20GB): $0.15/hour - Good for 1024x1024
RTX 4090 (24GB): $0.40/hour - Best for production

For development: Use RTX 3060 → Save $0.05/hour
Monthly savings: $0.05 × 80 hours = $4/month
```

### Strategy 4: RunPod Serverless (Low Volume)
```
If generating <100 images/day:

Pod: 4 hours × $0.15 = $0.60/day = $18/month
Serverless: 100 images × 5s × $0.0002/s = $0.10/day = $3/month

Savings: $15/month!

Best for: Testing, demos, low-volume production
```

---

## Troubleshooting

### Issue 1: "comfyui_status: disconnected"

**Diagnosis:**
```bash
# Test RunPod URL directly
curl https://YOUR-POD-ID-8188.proxy.runpod.net/queue

# Check .env has correct URL
grep COMFYUI_URL .env

# Check API logs
docker compose logs api | grep -i comfyui
```

**Fix:**
1. Verify URL is `https://` not `http://`
2. Verify pod is "Running" in RunPod dashboard
3. Verify URL includes `-8188.proxy.runpod.net`
4. Restart API: `docker compose restart api`

### Issue 2: Pod Starts Then Stops Immediately

**Cause:** Insufficient disk space or memory

**Fix:**
```
Edit Pod → Configuration
- Increase Container Disk: 30 GB
- Increase Volume Disk: 100 GB
- Restart pod
```

### Issue 3: "Model not found" Error

**Cause:** Model not downloaded yet

**Fix:**
```bash
# SSH into pod
ssh YOUR_POD_ID@ssh.runpod.io

# Check models
ls -lh /workspace/ComfyUI/models/checkpoints/

# Download model manually
cd /workspace/ComfyUI/models/checkpoints/
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt
```

### Issue 4: Slow Image Generation

**Expected times on RTX 4000 Ada:**
- 512x512, 20 steps: ~3-5 seconds
- 1024x1024, 20 steps: ~10-15 seconds

**If slower:**
1. Check pod GPU is actually being used (not CPU fallback)
2. Check for other jobs running on same GPU
3. Upgrade to faster GPU (RTX 4090)

### Issue 5: Pod Interrupted (Spot Instance)

**What happens:**
- RunPod may interrupt spot instances when demand is high
- Your pod stops (billing stops too)
- All data in container disk is lost
- Volume disk (persistent) is preserved

**Fix:**
1. Restart pod (models on volume disk are preserved)
2. Or switch to On-Demand for guaranteed uptime

**Prevention:**
- Use Volume Disk for models (persistent)
- Use On-Demand for production
- Spot is fine for development (rare interruptions)

---

## Performance Benchmarks

### RTX 3060 (12GB) - Budget Option
| Resolution | Steps | Time | Cost/Image |
|------------|-------|------|------------|
| 512x512 | 10 | ~2s | $0.0006 |
| 512x512 | 20 | ~4s | $0.0011 |
| 1024x1024 | 20 | ~15s | $0.0042 |

### RTX 4000 Ada (20GB) - Recommended
| Resolution | Steps | Time | Cost/Image |
|------------|-------|------|------------|
| 512x512 | 10 | ~1.5s | $0.0006 |
| 512x512 | 20 | ~3s | $0.0013 |
| 1024x1024 | 20 | ~10s | $0.0042 |

### RTX 4090 (24GB) - Production
| Resolution | Steps | Time | Cost/Image |
|------------|-------|------|------------|
| 512x512 | 10 | ~0.8s | $0.0009 |
| 512x512 | 20 | ~1.5s | $0.0017 |
| 1024x1024 | 20 | ~5s | $0.0056 |

**Cost per 1000 images (512x512, 20 steps):**
- RTX 3060: $1.10
- RTX 4000 Ada: $1.30
- RTX 4090: $1.70

**vs CPU mode:** ~$30+ (9 minutes × $0.20/hour per image)

---

## Migration Checklist

### From Local CPU Mode to RunPod GPU

- [ ] Create RunPod account and add payment method
- [ ] Deploy ComfyUI pod (Spot or On-Demand)
- [ ] Wait for pod to reach "Running" status
- [ ] Copy pod URL (https://YOUR-POD-ID-8188.proxy.runpod.net)
- [ ] Update `.env` file with `COMFYUI_URL`
- [ ] Update `COMFYUI_TIMEOUT=120.0` (reduce from 600s)
- [ ] Restart API and Worker: `docker compose restart api worker`
- [ ] Test health: `curl http://localhost:8000/health`
- [ ] Submit test job and verify 5-10 second generation time
- [ ] Enable auto-stop after 30 minutes idle
- [ ] Set up billing alerts ($2/day, $50/month)
- [ ] Enable authentication for production (`AUTH_ENABLED=true`)

---

## Next Steps

### After RunPod is Working

1. **Enable Authentication** - See [SECURITY_TEST_REPORT.md](SECURITY_TEST_REPORT.md)
2. **Deploy Demo Interface** - Build minimal chat UI for testing
3. **Add Monitoring** - Set up Prometheus + Grafana
4. **Implement SDK** - Python wrapper for your API
5. **Scale Workers** - Add more workers for parallel processing
6. **Production Deployment** - See [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)

---

## Summary

**RunPod Billing:**
- ✅ **Only charged when running** (per-second billing)
- ✅ **Auto-stop saves money** (30 min idle → stop)
- ✅ **Expected cost:** $15-30/month for development
- ✅ **10-20x faster** than CPU mode (5s vs 9 minutes)

**Quick Start:**
```bash
# 1. Deploy RunPod pod (copy URL)
# 2. Update .env
COMFYUI_URL=https://YOUR-POD-ID-8188.proxy.runpod.net

# 3. Restart services
docker compose restart api worker

# 4. Test
curl http://localhost:8000/health
```

**Questions?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or RunPod docs at https://docs.runpod.io

---

**Status:** Ready to deploy! 🚀

**Estimated setup time:** 15-20 minutes (including model download)
**Expected performance:** 3-5 seconds per 512x512 image @ 20 steps
