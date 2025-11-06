# ComfyUI API Service - Quick Start Guide

**Get started in 5 minutes!**

---

## What is This?

A REST API wrapper for ComfyUI that lets you generate AI images programmatically without using the UI.

```bash
# Instead of clicking buttons in ComfyUI's web interface...
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset over mountains"}'
```

---

## Prerequisites

- Python 3.11+
- Poetry (for dependency management)
- ComfyUI installed and configured
- At least one Stable Diffusion model

---

## Quick Start

### 1. Install Dependencies

```bash
cd /workspaces/comfy-api-service
poetry install
```

### 2. Start ComfyUI (Terminal 1)

```bash
cd /workspaces/ComfyUI
python3 main.py --cpu --listen 0.0.0.0 --port 8188
```

### 3. Start API Service (Terminal 2)

```bash
cd /workspaces/comfy-api-service
poetry run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test It!

```bash
# Check if services are running
curl http://localhost:8000/health

# Generate your first image
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cat sitting on a windowsill, oil painting style",
    "width": 512,
    "height": 512,
    "steps": 20
  }'
```

---

## Interactive Documentation

Open your browser and go to:

**Swagger UI:** http://localhost:8000/docs
**ReDoc:** http://localhost:8000/redoc

Try the API directly from your browser!

---

## Example Usage

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/generate",
    json={
        "prompt": "A majestic mountain landscape",
        "width": 1024,
        "height": 1024,
        "steps": 30
    }
)

result = response.json()
print(f"Generated! Image URL: {result['image_url']}")
```

### JavaScript

```javascript
fetch('http://localhost:8000/api/v1/generate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'A majestic mountain landscape',
    width: 1024,
    height: 1024,
    steps: 30
  })
})
.then(res => res.json())
.then(data => console.log('Generated!', data.image_url));
```

### cURL (Advanced)

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A cyberpunk city at night, neon lights, rain",
    "negative_prompt": "blurry, low quality",
    "width": 1024,
    "height": 1024,
    "steps": 30,
    "cfg_scale": 7.5,
    "sampler": "euler_a",
    "seed": 42,
    "model": "sd_xl_base_1.0.safetensors"
  }' | jq .
```

---

## Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/models` | GET | List available models |
| `/api/v1/generate` | POST | Generate single image |
| `/api/v1/generate/batch` | POST | Generate multiple images |
| `/docs` | GET | Interactive API docs |

---

## Common Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `prompt` | string | required | 1-5000 chars | What to generate |
| `negative_prompt` | string | null | 0-2000 chars | What to avoid |
| `width` | int | 512 | 64-2048 (÷8) | Image width |
| `height` | int | 512 | 64-2048 (÷8) | Image height |
| `steps` | int | 20 | 1-150 | Quality/speed tradeoff |
| `cfg_scale` | float | 7.0 | 1.0-30.0 | Prompt adherence |
| `sampler` | string | "euler_a" | see below | Sampling algorithm |
| `seed` | int | random | -1 or 0+ | For reproducibility |
| `model` | string | "sd_xl_base_1.0..." | - | Model checkpoint |

### Available Samplers

- `euler`, `euler_a` (recommended for beginners)
- `heun`, `dpm_2`, `dpm_2_a`
- `dpm_plus_plus_2s_a`, `dpm_plus_plus_2m`, `dpm_plus_plus_sde`
- `lms`, `ddim`, `uni_pc`

---

## Troubleshooting

### "ComfyUI service is not available"

**Solution:** Make sure ComfyUI is running on port 8188

```bash
curl http://localhost:8188/system_stats
```

### "Width must be divisible by 8"

**Solution:** Use dimensions like 512, 768, 1024, not 513 or 1000

### API won't start

**Solution:** Install dependencies

```bash
poetry install
```

### Permission errors

**Solution:** Make scripts executable

```bash
chmod +x .devcontainer/*.sh
```

---

## Documentation

Comprehensive documentation available:

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and patterns
- **[API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)** - Detailed testing procedures
- **[DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)** - Development history and decisions
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Complete implementation details

---

## Next Steps

1. **Read the testing guide:** [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)
2. **Understand the architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Try different parameters** in the interactive docs
4. **Generate images** with various prompts and settings
5. **Integrate into your application** using the examples above

---

## Need Help?

- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **Testing Guide:** [API_TESTING_GUIDE.md](API_TESTING_GUIDE.md)
- **Architecture:** [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Features

✅ RESTful API for image generation
✅ Full parameter control
✅ Batch processing
✅ Health monitoring
✅ Model discovery
✅ Interactive documentation
✅ Async/non-blocking
✅ Error handling
✅ Type validation
✅ OpenAPI schema

---

**Version:** 1.0.0
**Status:** ✅ Ready for testing
**Last Updated:** 2025-11-06
