# ComfyUI Setup Guide

## Quick Start

Creator requires a ComfyUI instance for AI image generation. You have three options:

## Option 1: Local ComfyUI (Recommended for Development)

### Requirements
- Python 3.10+
- 8GB+ RAM
- GPU with 4GB+ VRAM (optional but highly recommended)

### Installation

```bash
# 1. Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# 2. Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# 3. Download a model
# Option A: SD 1.5 (4GB VRAM, faster)
cd models/checkpoints
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt

# Option B: SDXL (8GB+ VRAM, higher quality)
wget https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors

cd ../..

# 4. Start ComfyUI
python main.py --listen 0.0.0.0 --port 8188
```

### Configure Creator

```bash
# Update .env in Creator project
echo "COMFYUI_URL=http://localhost:8188" >> .env
```

### Test Connection

```bash
# In Creator project directory
python scripts/test_comfyui_connection.py
```

You should see: ✅ ComfyUI is accessible and healthy!

## Option 2: RunPod GPU Cloud

### Setup

1. **Create RunPod Account**
   - Go to https://runpod.io
   - Sign up and add credits ($10 minimum)

2. **Deploy Pod**
   ```
   - Click "Deploy"
   - Select "GPU Pods"
   - Choose template: "RunPod Pytorch" or "ComfyUI"
   - Select GPU: RTX 4000 Ada (16GB VRAM) recommended
   - Click "Deploy On-Demand"
   ```

3. **Install ComfyUI** (if not using ComfyUI template)
   ```bash
   # In RunPod web terminal
   cd /workspace
   git clone https://github.com/comfyanonymous/ComfyUI.git
   cd ComfyUI
   pip install -r requirements.txt

   # Download model
   cd models/checkpoints
   wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt
   cd ../..
   ```

4. **Start ComfyUI**
   ```bash
   python main.py --listen 0.0.0.0 --port 8188
   ```

5. **Get Proxy URL**
   - In RunPod dashboard, click "Connect"
   - Copy the URL ending in `-8188.proxy.runpod.net`
   - Example: `https://jfmkqw45px5o3x-8188.proxy.runpod.net`

6. **Configure Creator**
   ```bash
   # Update .env
   echo "COMFYUI_URL=https://your-pod-id-8188.proxy.runpod.net" >> .env
   ```

### Important Notes
- **Cost**: ~$0.30-0.50/hour depending on GPU
- **Stop when not using**: Pause pod when not generating to save money
- **Data persistence**: Use network volumes to keep models between sessions

## Option 3: Other Cloud Providers

ComfyUI works on any cloud platform with GPU support:

### AWS EC2
- Use `g4dn.xlarge` instance (NVIDIA T4)
- Follow local installation steps
- Configure security group to allow port 8188

### Google Cloud Compute
- Use `n1-standard-4` with NVIDIA T4
- Follow local installation steps
- Configure firewall rules

### Vast.ai / Lambda Labs
- Similar to RunPod
- Cheaper but less reliable
- Follow RunPod instructions

## Troubleshooting

### Connection Issues

```bash
# Test if ComfyUI is accessible
curl http://localhost:8188/system_stats

# Or for RunPod
curl https://your-pod-id-8188.proxy.runpod.net/system_stats
```

### Common Errors

**"No module named 'tqdm'"**
```bash
pip install tqdm
```

**"Out of memory"**
- Use smaller model (SD 1.5 instead of SDXL)
- Reduce resolution in workflow
- Lower batch size

**"Model not found"**
```bash
# Check models directory
ls ComfyUI/models/checkpoints/

# Download SD 1.5 if missing
cd ComfyUI/models/checkpoints
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt
```

**"404 Not Found" when generating**
- ComfyUI crashed or stopped
- Restart: `python main.py --listen 0.0.0.0 --port 8188`

## Performance Tips

### GPU Selection
- **Development**: RTX 3060 (12GB) or better
- **Production**: RTX 4090 or A100 for fastest generation
- **Budget**: GTX 1660 Ti (6GB) works for SD 1.5

### Optimization
```bash
# Enable xformers for faster generation
pip install xformers

# Use lower precision
python main.py --listen 0.0.0.0 --port 8188 --fp16-vae
```

### Model Recommendations
- **Hero backgrounds**: SD 1.5 is sufficient
- **Detailed illustrations**: Use SDXL
- **Portraits**: Use SD 1.5 + Adetailer custom node

## Next Steps

Once ComfyUI is running:

1. **Test connection**: `python scripts/test_comfyui_connection.py`
2. **Generate hero images**: `python scripts/generate_hero_images.py`
3. **Explore workflows**: See [COMFYUI_WORKFLOW_GUIDE.md](COMFYUI_WORKFLOW_GUIDE.md)
4. **Control workflows**: See [WORKFLOW_CONTROL_FAQ.md](WORKFLOW_CONTROL_FAQ.md)

## Resources

- **ComfyUI Docs**: https://github.com/comfyanonymous/ComfyUI
- **Model Hub**: https://huggingface.co/models?pipeline_tag=text-to-image
- **Custom Nodes**: https://github.com/ltdrdata/ComfyUI-Manager
- **Workflows**: https://comfyworkflows.com/

---

Need help? Check the Creator docs or open an issue!
