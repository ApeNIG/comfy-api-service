# ComfyUI Setup Guide

**Goal:** Add GPU-powered image generation to your running API service

**Current Status:** ✅ API, Redis, MinIO, Worker all running
**Missing:** ComfyUI backend to actually generate images

---

## 🎯 Quick Decision Tree

### Do you have an NVIDIA GPU?

**Check on Windows:**
```powershell
nvidia-smi
```

**If you see GPU info** → You can run ComfyUI locally with Docker
**If you see "command not found"** → You have 3 options below

---

## Option 1: Run ComfyUI Locally (Best for Development)

### Requirements:
- ✅ NVIDIA GPU (GTX 1060 6GB minimum, RTX 3060+ recommended)
- ✅ NVIDIA Docker runtime installed
- ✅ 20GB+ free disk space (for models)

### Step 1: Check GPU Support

```powershell
# Check if nvidia-smi works
nvidia-smi

# Check if Docker can see GPU
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

**If both work** → Continue to Step 2
**If either fails** → See "Install NVIDIA Docker Runtime" below

### Step 2: Start ComfyUI

**Note**: We're using `ghcr.io/ai-dock/comfyui:latest` as a reliable alternative to the yanwk image.

```powershell
# Navigate to your project
cd C:\Users\sibag\desktop\BUILD\comfy-api-service

# Pull the ComfyUI image (first time only)
docker pull ghcr.io/ai-dock/comfyui:latest

# Start ComfyUI
docker-compose up -d comfyui

# Watch it download models (first time only, takes 5-10 minutes)
docker-compose logs -f comfyui
```

**You'll see:**
```
Downloading model: v1-5-pruned-emaonly.safetensors
Progress: [################] 100%
ComfyUI started successfully
Server running on http://0.0.0.0:8188
```

### Step 3: Verify ComfyUI is Running

```powershell
# Check if it's accessible
curl http://localhost:8188/system_stats
```

**Expected response:**
```json
{
  "system": {
    "os": "nt",
    "python_version": "3.10.6",
    "pytorch_version": "2.0.1+cu118"
  },
  "devices": [
    {
      "name": "NVIDIA GeForce RTX 3060",
      "type": "cuda",
      "index": 0,
      "vram_total": 12884901888,
      "vram_free": 12345678912
    }
  ]
}
```

### Step 4: Test End-to-End

Open your browser to http://localhost:8000/docs and:

1. Click on **POST `/api/v1/jobs`**
2. Click "Try it out"
3. Paste this JSON:
```json
{
  "prompt": "A beautiful sunset over mountains, golden hour, photorealistic",
  "model": "v1-5-pruned-emaonly.safetensors",
  "width": 512,
  "height": 512,
  "steps": 20
}
```
4. Click "Execute"
5. Copy the `job_id` from the response
6. Go to **GET `/api/v1/jobs/{job_id}`**
7. Paste your job_id
8. Click "Execute"
9. Wait 20-30 seconds, click "Execute" again
10. You should see `"status": "succeeded"` with an artifact URL!

---

## Option 2: Use Cloud GPU (Recommended for Production)

If you don't have a local GPU, you can run ComfyUI on a cloud GPU instance.

### Best Options:

#### A. RunPod (Easiest, ~$0.20/hour)
```bash
# 1. Sign up at runpod.io
# 2. Deploy "ComfyUI" template
# 3. Get the public URL (e.g., https://abc123-8188.proxy.runpod.net)
# 4. Update your .env file:
COMFYUI_URL=https://abc123-8188.proxy.runpod.net
# 5. Restart API and Worker
docker-compose restart api worker
```

#### B. AWS EC2 with GPU (~$0.50/hour)
```bash
# 1. Launch g4dn.xlarge instance (1x T4 GPU, 16GB RAM)
# 2. Install Docker + NVIDIA runtime
# 3. Run ComfyUI container:
docker run -d --gpus all -p 8188:8188 \
  -v ~/comfyui/models:/app/models \
  yanwk/comfyui-boot:latest

# 4. Get public IP (e.g., 54.123.45.67)
# 5. Update .env:
COMFYUI_URL=http://54.123.45.67:8188
# 6. Restart API and Worker
```

#### C. Vast.ai (Cheapest, ~$0.15/hour)
```bash
# 1. Sign up at vast.ai
# 2. Rent a GPU instance with Docker
# 3. SSH in and run ComfyUI
# 4. Expose port 8188
# 5. Update .env with instance URL
```

---

## Option 3: Run ComfyUI Without Docker (Advanced)

If Docker GPU isn't working, you can run ComfyUI directly:

### Step 1: Install ComfyUI

```powershell
# Navigate to a folder outside your project
cd C:\Users\sibag\

# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Download a model (Stable Diffusion 1.5)
# Download from: https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
# Put it in: ComfyUI\models\checkpoints\
```

### Step 2: Start ComfyUI

```powershell
# Start the server
python main.py --listen 0.0.0.0 --port 8188
```

### Step 3: Update Your .env

```bash
# In C:\Users\sibag\desktop\BUILD\comfy-api-service\.env
COMFYUI_URL=http://localhost:8188
```

### Step 4: Restart Services

```powershell
cd C:\Users\sibag\desktop\BUILD\comfy-api-service
docker-compose restart api worker
```

---

## Option 4: CPU Mode (Fallback for Unsupported GPUs)

### When to Use CPU Mode

Use CPU mode if:
- ❌ No NVIDIA GPU available
- ❌ GPU compute capability too old (< 7.0 required for PyTorch 2.0+)
- ❌ NVIDIA Docker runtime not working
- ✅ You want to test the API without GPU

**Example:** Quadro P2000 has compute capability 6.1, which PyTorch 2.0.1 doesn't support. CPU mode is the solution.

### Performance Expectations

**CPU mode is 10-20x slower than GPU:**

| Image Size | Steps | GPU Time | CPU Time |
|------------|-------|----------|----------|
| 512x512 | 10 | ~3s | ~9 min |
| 512x512 | 20 | ~5s | ~18 min |
| 1024x1024 | 20 | ~15s | ~60 min |

**Recommendation:** Use 512x512 with 10-15 steps for testing in CPU mode.

### Enabling CPU Mode

**Already configured in docker-compose.yml:**

```yaml
comfyui:
  image: ghcr.io/ai-dock/comfyui:latest
  command: /opt/ai-dock/bin/supervisor-comfyui.sh --cpu
  # ... rest of config
```

The `--cpu` flag enables CPU-only mode.

### Configuration Changes for CPU Mode

**1. Increase Timeout** (already done in commit b954fe3)

[apps/api/config.py:38](apps/api/config.py#L38):
```python
comfyui_timeout: float = 600.0  # 10 minutes for CPU mode
```

**2. Reduce Steps for Testing**

When testing in CPU mode, use fewer steps:

```json
{
  "prompt": "A beautiful sunset",
  "width": 512,
  "height": 512,
  "steps": 10,
  "model": "v1-5-pruned-emaonly.safetensors"
}
```

### Starting ComfyUI in CPU Mode

```bash
# Start ComfyUI with CPU flag (already configured)
docker compose up -d comfyui

# Monitor startup (first time downloads models)
docker compose logs -f comfyui

# Wait for: "Starting server..."
# Takes 2-3 minutes on first run
```

### Verifying CPU Mode is Active

```bash
# Check ComfyUI logs
docker compose logs comfyui | grep cpu

# You should see: "Running in CPU mode"
```

### Testing CPU Mode

**Submit a fast test job (10 steps):**

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A sunset over mountains",
    "width": 512,
    "height": 512,
    "steps": 10
  }'
```

**Expected timeline:**
- Job accepted: Immediately
- Job started: Within 5 seconds
- Job completed: 8-10 minutes later
- Image size: ~400KB PNG

**Check status:**

```bash
# Replace JOB_ID with your actual job ID
curl http://localhost:8000/api/v1/jobs/JOB_ID

# Status progression:
# "queued" → "processing" → "succeeded" (after ~9 minutes)
```

### CPU Mode Benchmarks (Verified)

**Hardware:** Quadro P2000 (compute 6.1, unsupported by PyTorch 2.0+)

**Test Results:**
- Model: v1-5-pruned-emaonly.safetensors
- Resolution: 512x512
- Steps: 10
- Time: 534 seconds (~9 minutes)
- Output: 404,202 bytes (395 KB PNG)
- Status: succeeded ✅

### Troubleshooting CPU Mode

**Issue: "CUDA out of memory" in CPU mode**

This shouldn't happen in CPU mode. Check:
```bash
docker compose logs comfyui | grep -i "cpu\|cuda"
```

Verify `--cpu` flag is present in the command.

**Issue: Jobs taking > 15 minutes**

This is normal for:
- Steps > 15
- Resolution > 512x512
- Complex prompts

Reduce parameters:
```json
{
  "steps": 10,
  "width": 512,
  "height": 512
}
```

**Issue: Jobs timing out at 10 minutes**

The timeout is configured for 600s (10 minutes). For 20-step generations:

```bash
# Temporarily increase timeout in .env
COMFYUI_TIMEOUT=1200  # 20 minutes

# Restart services
docker compose restart api worker
```

---

## Troubleshooting

### Issue 1: "docker: Error response from daemon: could not select device driver"

**Cause:** NVIDIA Docker runtime not installed

**Fix (Windows with WSL2):**
```powershell
# 1. Install NVIDIA drivers for your GPU
# Download from: https://www.nvidia.com/Download/index.aspx

# 2. Install NVIDIA Container Toolkit in WSL2
wsl
sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
exit

# 3. Try again
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Issue 2: "Connection refused to ComfyUI"

**Check if ComfyUI is running:**
```powershell
docker-compose ps comfyui
# Should show "Up" status

docker-compose logs comfyui
# Look for "Server running on http://0.0.0.0:8188"
```

**Test directly:**
```powershell
curl http://localhost:8188/system_stats
```

### Issue 3: Models not downloading

**Manual download:**
1. Go to https://huggingface.co/runwayml/stable-diffusion-v1-5
2. Download `v1-5-pruned-emaonly.safetensors` (4GB)
3. Put it in ComfyUI's models folder:
   - Docker: Copy into container
   - Local: `ComfyUI\models\checkpoints\`

### Issue 4: Out of memory errors

**Reduce image size:**
```json
{
  "width": 256,
  "height": 256,
  "steps": 15
}
```

**Or reduce batch size:**
```json
{
  "num_images": 1
}
```

---

## Verifying It Works

### Test 1: Direct ComfyUI Access

Open browser to: http://localhost:8188

You should see the ComfyUI web interface.

### Test 2: API Health Check

```bash
curl http://localhost:8000/health
```

Should show:
```json
{
  "status": "healthy",
  "comfyui_status": "connected"  # <-- Should be "connected"
}
```

### Test 3: Submit a Job

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A sunset",
    "width": 512,
    "height": 512
  }'
```

**Response:**
```json
{
  "job_id": "job_abc123",
  "status": "queued"
}
```

### Test 4: Check Job Status

```bash
# Wait 20-30 seconds, then:
curl http://localhost:8000/api/v1/jobs/job_abc123
```

**Should see:**
```json
{
  "job_id": "job_abc123",
  "status": "succeeded",
  "result": {
    "artifacts": [
      {
        "url": "http://localhost:9000/comfyui-artifacts/jobs/job_abc123/image_0.png?..."
      }
    ]
  }
}
```

### Test 5: Download the Image

Copy the artifact URL and paste it in your browser. You should see your generated image!

---

## What Models Are Available?

After ComfyUI downloads models, you can use:

| Model | File Size | Best For |
|-------|-----------|----------|
| `v1-5-pruned-emaonly.safetensors` | 4GB | General purpose, fast |
| `dreamshaper_8.safetensors` | 2GB | Artistic, stylized |
| `realisticVisionV51_v51VAE.safetensors` | 5GB | Photorealistic |

To use a specific model, just pass it in the request:

```json
{
  "prompt": "A sunset",
  "model": "dreamshaper_8.safetensors"
}
```

---

## Next Steps After ComfyUI is Running

Once you have ComfyUI working:

1. **Test different prompts** - See what styles work best
2. **Try different models** - Each has a unique style
3. **Experiment with parameters** - Steps, CFG scale, samplers
4. **Enable authentication** - Set `AUTH_ENABLED=true` in `.env`
5. **Monitor metrics** - Watch Prometheus metrics at `/metrics`
6. **Scale workers** - Add more workers for parallel processing

---

## Performance Benchmarks

**Expected generation times:**

| GPU | Resolution | Steps | Time |
|-----|------------|-------|------|
| RTX 3060 (12GB) | 512x512 | 20 | ~15s |
| RTX 3060 (12GB) | 1024x1024 | 20 | ~45s |
| RTX 4090 (24GB) | 512x512 | 20 | ~5s |
| RTX 4090 (24GB) | 1024x1024 | 20 | ~15s |
| Cloud (T4) | 512x512 | 20 | ~20s |

---

## Cost Estimates

**Local GPU:** Free (electricity only)

**Cloud GPU:**
- RunPod: $0.20/hour (~$150/month 24/7)
- AWS g4dn.xlarge: $0.50/hour (~$360/month 24/7)
- Vast.ai: $0.15/hour (~$110/month 24/7)

**Tip:** For development, use spot instances or pause when not needed!

---

## Summary

You have 3 options:
1. ✅ **Local GPU with Docker** - Best for development, free
2. ✅ **Cloud GPU** - Best for production, ~$100-300/month
3. ✅ **Local GPU without Docker** - Backup if Docker GPU fails

**Pick the one that works for you and let's get images generating!** 🎨

---

**Questions?** See [ARCHITECTURE_EXPLAINED.md](ARCHITECTURE_EXPLAINED.md) to understand how ComfyUI fits into the system.
