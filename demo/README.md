# ComfyUI Image Generator Demo

A feature-rich command-line application demonstrating the ComfyUI Python SDK capabilities.

## Features

- **Interactive Image Generation** - Generate images with custom prompts and parameters
- **Cost Estimation** - See estimated costs before generating
- **Real-time Progress** - Visual progress tracking during generation
- **Usage Statistics** - View total jobs, costs, and success rates
- **Monthly Projections** - Project costs based on expected usage
- **GPU Configuration** - Switch between different GPU types
- **Batch Generation** - Generate multiple images at once
- **Error Handling** - Robust error handling with helpful messages

## Installation

### 1. Install the SDK

```bash
cd sdk/python
pip install -e .
```

### 2. Make the demo executable

```bash
chmod +x demo/image_generator.py
```

## Usage

### Interactive Mode

Run without arguments to enter interactive mode:

```bash
python demo/image_generator.py
```

You'll see a menu with options:
```
Options:
  1. Generate an image
  2. View usage statistics
  3. Project monthly costs
  4. Configure GPU type
  5. Exit
```

### Command-Line Mode

Generate images directly from the command line:

```bash
# Basic generation
python demo/image_generator.py --prompt "A sunset over mountains"

# Custom parameters
python demo/image_generator.py \
  --prompt "A futuristic city at night" \
  --width 1024 \
  --height 1024 \
  --steps 30 \
  --num-images 4

# Different API URL
python demo/image_generator.py \
  --url http://172.19.0.6:8000 \
  --prompt "A cat wearing sunglasses"

# With API key (if authentication enabled)
python demo/image_generator.py \
  --api-key your-api-key-here \
  --prompt "Abstract art"
```

### View Statistics

```bash
python demo/image_generator.py --stats
```

Output:
```
============================================================
                   Usage Statistics
============================================================

Total Jobs:        25
Successful:        24
Failed:            1
Success Rate:      96.0%
Images Generated:  48
Total Cost:        $0.062400
Total Runtime:     0.42 hours
Avg Time/Image:    3.2s
Avg Cost/Image:    $0.001300
```

### Project Monthly Costs

```bash
# Project costs for 100 images/day
python demo/image_generator.py --project 100

# Project costs for 500 images/day
python demo/image_generator.py --project 500
```

Output:
```
============================================================
              Monthly Cost Projection
============================================================

Images per Day:    100
Monthly Images:    3000
Daily Runtime:     0.08 hours
Monthly Runtime:   2.5 hours
Daily Cost:        $0.0125
Monthly Cost:      $3.75
Cost per Image:    $0.000125
```

## Command-Line Options

```
--url URL              ComfyUI API URL (default: http://localhost:8000)
--api-key KEY          API key (if authentication enabled)

Generation Parameters:
--prompt TEXT          Image generation prompt
--width N              Image width (default: 512)
--height N             Image height (default: 512)
--steps N              Diffusion steps (default: 20)
--num-images N         Number of images (default: 1)
--output DIR           Output directory (default: generated_images)

Modes:
--stats                Show usage statistics
--project N            Project monthly costs for N images/day
--no-estimate          Skip cost estimation before generating
--no-progress          Disable progress display
```

## Examples

### Example 1: Quick Generation

```bash
python demo/image_generator.py \
  --prompt "A serene lake at sunrise" \
  --no-estimate
```

### Example 2: High-Quality Batch

```bash
python demo/image_generator.py \
  --prompt "Professional headshot photo" \
  --width 1024 \
  --height 1024 \
  --steps 50 \
  --num-images 10 \
  --output headshots
```

### Example 3: Cost Analysis

```bash
# Check current stats
python demo/image_generator.py --stats

# Project costs for expected usage
python demo/image_generator.py --project 200

# Generate with cost estimation
python demo/image_generator.py \
  --prompt "Marketing banner design" \
  --width 1920 \
  --height 1080
```

## Interactive Mode Walkthrough

### 1. Start Interactive Mode

```bash
python demo/image_generator.py
```

### 2. Generate an Image

```
Select option (1-5): 1
Enter prompt: A magical forest with glowing mushrooms
Width [512]: 768
Height [512]: 768
Steps [20]: 30
Number of images [1]: 2
```

The app will:
1. Show cost estimation
2. Ask for confirmation if cost is high
3. Submit the job
4. Show real-time progress
5. Download and save images
6. Display summary

### 3. View Statistics

```
Select option (1-5): 2
```

See all your usage statistics.

### 4. Project Monthly Costs

```
Select option (1-5): 3
Expected images per day [100]: 150
```

See projected monthly costs based on your usage pattern.

### 5. Configure GPU Type

```
Select option (1-5): 4

Available GPU types:
  - cpu: $0.00/hour (current)
  - rtx_3060: $0.10/hour
  - rtx_4000_ada: $0.15/hour
  - rtx_4090: $0.40/hour
  - a40: $0.50/hour
  - local_gpu: $0.00/hour

Enter GPU type: rtx_4000_ada
```

Update the GPU type for accurate cost tracking.

## Output Structure

Generated images are saved to the output directory (default: `generated_images/`):

```
generated_images/
├── image_20251108_143022_0.png
├── image_20251108_143022_1.png
├── image_20251108_143155_0.png
└── ...
```

Filenames include timestamp and index for easy tracking.

## Error Handling

The app handles various error scenarios:

### Connection Errors
```bash
✗ Failed to connect to API: Failed to connect to http://localhost:8000
```

**Solution:** Ensure the API is running and accessible.

### Job Failures
```bash
✗ Job failed: Generation failed
Details: Out of memory
```

**Solution:** Try reducing image size or steps.

### Timeouts
```bash
✗ Job timed out after 10 minutes
```

**Solution:** Check API logs, reduce complexity, or increase timeout.

## Advanced Usage

### Using with Remote API

```bash
python demo/image_generator.py \
  --url https://your-api.example.com \
  --api-key YOUR_API_KEY \
  --prompt "Your prompt here"
```

### Batch Processing Script

```bash
#!/bin/bash
# Generate multiple different images

prompts=(
  "A sunset over mountains"
  "A futuristic city"
  "A serene lake"
  "A magical forest"
)

for prompt in "${prompts[@]}"; do
  python demo/image_generator.py \
    --prompt "$prompt" \
    --width 1024 \
    --height 1024 \
    --no-estimate
done
```

### Integration in Python Scripts

```python
from comfyui_client import ComfyUIClient

# Create client
client = ComfyUIClient("http://localhost:8000")

# Estimate cost
cost = client.estimate_cost(512, 512, 20)
print(f"Will cost: ${cost['estimated_cost_usd']:.6f}")

# Generate if affordable
if cost['estimated_cost_usd'] < 0.01:
    job = client.generate(
        prompt="A beautiful landscape",
        width=512,
        height=512,
        steps=20
    )

    result = job.wait_for_completion()
    result.download_image("output.png")
```

## Tips for Best Results

### 1. Cost Optimization

- Use **CPU mode** for testing (free, but slow)
- Use **RTX 4000 Ada** for production ($0.15/hour)
- Generate multiple images in one batch to reduce overhead
- Use lower steps (15-20) for drafts, higher (30-50) for final

### 2. Quality Settings

**Fast Draft:**
- Width/Height: 512x512
- Steps: 15-20
- Time: ~2-3 seconds (GPU)

**Standard Quality:**
- Width/Height: 512x512 or 768x768
- Steps: 20-30
- Time: ~3-5 seconds (GPU)

**High Quality:**
- Width/Height: 1024x1024
- Steps: 40-50
- Time: ~15-20 seconds (GPU)

**Production:**
- Width/Height: 1920x1080 or higher
- Steps: 50+
- Time: ~30-60 seconds (GPU)

### 3. Prompt Engineering

**Good prompts:**
- Be specific: "A red sports car on a mountain road at sunset"
- Include style: "oil painting of a..."
- Specify quality: "highly detailed", "professional photo"

**Avoid:**
- Vague prompts: "something cool"
- Conflicting descriptions
- Too many concepts in one prompt

## Troubleshooting

### Demo won't start

**Error:** `comfyui_client not installed`

**Solution:**
```bash
cd sdk/python
pip install -e .
```

### Can't connect to API

**Error:** `Connection refused`

**Solution:**
```bash
# Check if API is running
docker ps | grep comfyui-api

# Restart if needed
docker compose restart api

# Check logs
docker logs comfyui-api
```

### Images not downloading

**Error:** `Failed to download image`

**Solution:**
- Check MinIO is running
- Verify artifact URLs in job result
- Check network connectivity

### Slow generation

If generation is very slow (>1 minute for 512x512):
- You're likely using CPU mode
- Consider deploying GPU backend (see [RUNPOD_DEPLOYMENT_GUIDE.md](../RUNPOD_DEPLOYMENT_GUIDE.md))
- Or reduce image size/steps

## Next Steps

### Build on This Demo

1. **Add a Web Interface**
   - Use Flask/FastAPI
   - Real-time WebSocket updates
   - Image gallery

2. **Add More Features**
   - Negative prompts
   - ControlNet support
   - Image-to-image generation
   - Prompt templates

3. **Create a Service**
   - User accounts
   - Payment integration
   - API rate limiting
   - Usage quotas

### Deploy to Production

1. Enable authentication
2. Set up monitoring dashboard
3. Deploy RunPod GPU backend
4. Configure auto-scaling
5. Set up backup/recovery

## License

This demo application is part of the ComfyUI API Service project.

## Support

- API Documentation: [MONITORING_SETUP.md](../MONITORING_SETUP.md)
- SDK Documentation: [sdk/python/README.md](../sdk/python/README.md)
- Deployment Guide: [RUNPOD_DEPLOYMENT_GUIDE.md](../RUNPOD_DEPLOYMENT_GUIDE.md)
- Issues: Check the main project documentation
