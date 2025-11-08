# Demo Quick Start Guide

Get started with the ComfyUI Image Generator demo in 3 minutes!

## 30-Second Setup

```bash
# 1. Install the SDK (if not already installed)
cd sdk/python && pip install -e . && cd ../..

# 2. Run the demo in interactive mode
python demo/image_generator.py
```

That's it! You're ready to generate images.

## Your First Image (1 minute)

### Option 1: Interactive Mode

```bash
python demo/image_generator.py
```

Then follow the prompts:
```
Select option (1-5): 1
Enter prompt: A sunset over mountains
Width [512]: [press Enter]
Height [512]: [press Enter]
Steps [20]: [press Enter]
Number of images [1]: [press Enter]
```

The app will:
1. Show you the estimated cost ($0.000125 for RTX 4000 Ada)
2. Generate the image
3. Save it to `generated_images/`
4. Show you a summary

### Option 2: Command Line

```bash
python demo/image_generator.py --prompt "A sunset over mountains"
```

Done! Check `generated_images/` for your image.

## 5 Useful Commands

### 1. Generate a Specific Size Image

```bash
python demo/image_generator.py \
  --prompt "A futuristic city" \
  --width 1024 \
  --height 1024
```

### 2. Generate Multiple Images

```bash
python demo/image_generator.py \
  --prompt "Abstract art" \
  --num-images 4
```

### 3. Check Your Usage Stats

```bash
python demo/image_generator.py --stats
```

### 4. Project Monthly Costs

```bash
# For 100 images/day
python demo/image_generator.py --project 100
```

### 5. Fast Generation (Skip Cost Estimation)

```bash
python demo/image_generator.py \
  --prompt "A cat" \
  --no-estimate
```

## Understanding Costs

The demo shows you costs **before** generating:

```
============================================================
                   Cost Estimation
============================================================

GPU Type:        rtx_4000_ada
Hourly Rate:     $0.15/hour
Est. Time:       3s per image
Total Time:      3s
Cost per Image:  $0.000125
Total Cost:      $0.000125

✓ Very affordable! Less than $0.001
```

**Key takeaway:** A typical 512x512 image costs **$0.000125** (~1/8 of a penny)

### Monthly Cost Examples

| Images/Day | Monthly Images | Monthly Cost |
|------------|----------------|--------------|
| 10         | 300            | $0.38        |
| 100        | 3,000          | $3.75        |
| 500        | 15,000         | $18.75       |
| 1000       | 30,000         | $37.50       |

## Common Issues

### "comfyui_client not installed"

```bash
cd sdk/python
pip install -e .
```

### "Connection refused"

The API needs to be running. Check with:
```bash
docker ps | grep comfyui-api
```

If not running:
```bash
docker compose up -d api
```

### "Generation is very slow"

You're using CPU mode (free but slow: ~9 minutes per image).

For 100x faster generation:
- Deploy GPU backend: See [RUNPOD_DEPLOYMENT_GUIDE.md](../RUNPOD_DEPLOYMENT_GUIDE.md)
- Cost: ~$0.15/hour, only when running
- Speed: ~3 seconds per image (vs 9 minutes on CPU)

## What's Included

The demo showcases these SDK features:

1. **Cost Estimation** - `client.estimate_cost()`
2. **Image Generation** - `client.generate()`
3. **Progress Tracking** - `job.wait_for_completion(progress_callback=...)`
4. **Statistics** - `client.get_stats()`
5. **Monthly Projections** - `client.project_monthly_cost()`
6. **GPU Configuration** - `client.configure_gpu()`
7. **Error Handling** - Try/catch with custom exceptions

## Next Steps

### Explore Interactive Mode

```bash
python demo/image_generator.py
```

Try all 5 menu options to see the full feature set.

### Read the Full Documentation

- [demo/README.md](README.md) - Complete demo documentation
- [../sdk/python/README.md](../sdk/python/README.md) - SDK reference
- [../MONITORING_SETUP.md](../MONITORING_SETUP.md) - Monitoring API

### Build Your Own App

Use the demo code as a starting point:
- The demo is fully commented
- Shows best practices
- Demonstrates error handling
- Includes progress callbacks

### Try Advanced Features

```bash
# High-quality, large images
python demo/image_generator.py \
  --prompt "Professional landscape photo" \
  --width 1920 \
  --height 1080 \
  --steps 50

# Batch generation
python demo/image_generator.py \
  --prompt "Character concept art" \
  --num-images 10 \
  --steps 30
```

## Tips

1. **Start Small** - Test with 512x512 images first
2. **Check Costs** - Always review the cost estimation
3. **Use Progress** - Enable progress to see real-time updates
4. **Save Everything** - All images are auto-saved with timestamps
5. **Monitor Usage** - Run `--stats` periodically to track spending

## Examples for Different Use Cases

### For Artists

```bash
# Generate concept art variations
python demo/image_generator.py \
  --prompt "Fantasy character design, detailed armor" \
  --width 768 \
  --height 768 \
  --steps 30 \
  --num-images 8
```

### For Marketers

```bash
# Generate social media images
python demo/image_generator.py \
  --prompt "Product advertisement, modern minimalist" \
  --width 1080 \
  --height 1080 \
  --num-images 5
```

### For Developers

```python
from comfyui_client import ComfyUIClient

client = ComfyUIClient("http://localhost:8000")

# Estimate first
cost = client.estimate_cost(512, 512, 20)
print(f"Cost: ${cost['estimated_cost_usd']:.6f}")

# Generate if affordable
if cost['estimated_cost_usd'] < 0.01:
    job = client.generate(prompt="Test image", width=512, height=512)
    result = job.wait_for_completion()
    result.download_image("test.png")
```

### For Data Scientists

```bash
# Generate training data
for i in {1..100}; do
  python demo/image_generator.py \
    --prompt "Random object $i" \
    --no-estimate \
    --output training_data
done
```

## Getting Help

- Full demo docs: [demo/README.md](README.md)
- SDK docs: [../sdk/python/README.md](../sdk/python/README.md)
- API docs: [../MONITORING_SETUP.md](../MONITORING_SETUP.md)
- Deployment: [../RUNPOD_DEPLOYMENT_GUIDE.md](../RUNPOD_DEPLOYMENT_GUIDE.md)

## Summary

You now have a fully functional image generator that:
- ✅ Generates images from text prompts
- ✅ Estimates costs before generating
- ✅ Tracks progress in real-time
- ✅ Saves images automatically
- ✅ Shows usage statistics
- ✅ Projects monthly costs

**Try it now:**
```bash
python demo/image_generator.py --prompt "Your imagination here"
```

Happy generating! 🎨
