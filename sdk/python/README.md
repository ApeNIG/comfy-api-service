# ComfyUI Python Client SDK

Official Python client for the ComfyUI API Service.

## Installation

```bash
# From source
cd sdk/python
pip install -e .

# Or install dependencies only
pip install requests
```

## Quick Start

```python
from comfyui_client import ComfyUIClient

# Initialize client
client = ComfyUIClient("http://localhost:8000")

# Generate an image
job = client.generate(
    prompt="A beautiful sunset over mountains, golden hour",
    width=512,
    height=512,
    steps=20
)

print(f"Job ID: {job.job_id}")

# Wait for completion
result = job.wait_for_completion()
print(f"Generated {len(result.artifacts)} images")

# Download the image
result.download_image(save_path="sunset.png")
print("Image saved to sunset.png")
```

## Features

- **Simple API** - Clean, intuitive interface
- **Cost Estimation** - Estimate costs before generating
- **Progress Tracking** - Poll job status with callbacks
- **Error Handling** - Comprehensive exception types
- **Type Hints** - Full type annotations for IDE support

## Examples

### Basic Image Generation

```python
from comfyui_client import ComfyUIClient

client = ComfyUIClient("http://localhost:8000")

# Generate image
job = client.generate(
    prompt="A sunset",
    width=512,
    height=512
)

# Wait and download
result = job.wait_for_completion()
result.download_image("output.png")
```

### With Progress Callback

```python
def progress_callback(status):
    print(f"Status: {status['status']}")
    if 'progress' in status:
        print(f"Progress: {status['progress']*100:.0f}%")

job = client.generate(prompt="A sunset")
result = job.wait_for_completion(progress_callback=progress_callback)
```

### Cost Estimation

```python
# Estimate cost before generating
cost = client.estimate_cost(
    width=512,
    height=512,
    steps=20,
    num_images=1
)

print(f"Estimated cost: ${cost['estimated_cost_usd']:.4f}")
print(f"Estimated time: {cost['estimated_time_seconds']}s")

# If cost is acceptable, proceed with generation
if cost['estimated_cost_usd'] < 0.01:
    job = client.generate(prompt="A sunset", width=512, height=512, steps=20)
```

### Multiple Images

```python
# Generate a batch
job = client.generate(
    prompt="A sunset",
    num_images=4
)

result = job.wait_for_completion()

# Download all images
for i, artifact in enumerate(result.artifacts):
    result.download_image(index=i, save_path=f"sunset_{i}.png")
```

### Advanced Parameters

```python
job = client.generate(
    prompt="A beautiful sunset",
    negative_prompt="blurry, low quality",
    width=1024,
    height=1024,
    steps=30,
    cfg_scale=8.0,
    sampler="dpmpp_2m",
    seed=12345,  # For reproducibility
    num_images=2
)
```

### Authentication

```python
# With API key
client = ComfyUIClient(
    "http://localhost:8000",
    api_key="your-api-key-here"
)

job = client.generate(prompt="A sunset")
```

### Check Statistics

```python
# Get usage stats
stats = client.get_stats()
print(f"Total jobs: {stats['total_jobs']}")
print(f"Total cost: ${stats['total_cost_usd']:.2f}")
print(f"Success rate: {stats['success_rate_percent']:.1f}%")

# Project monthly costs
projection = client.project_monthly_cost(
    images_per_day=100,
    avg_time_seconds=3.0
)
print(f"Monthly cost: ${projection['monthly_cost_usd']:.2f}")
```

### Error Handling

```python
from comfyui_client import (
    JobFailedError,
    TimeoutError,
    AuthenticationError
)

try:
    job = client.generate(prompt="A sunset")
    result = job.wait_for_completion(timeout=300)

except AuthenticationError:
    print("Invalid API key")

except JobFailedError as e:
    print(f"Job failed: {e.error_details}")

except TimeoutError as e:
    print(f"Job timed out after {e.elapsed_time}s")
```

### Configure GPU Type for Cost Tracking

```python
# Configure for RunPod RTX 4000 Ada
client.configure_gpu("rtx_4000_ada")

# Now cost estimates will use RTX 4000 Ada pricing
cost = client.estimate_cost(512, 512, 20)
# Estimated cost will be based on $0.15/hour GPU
```

## API Reference

### ComfyUIClient

Main client class for interacting with the API.

**Constructor:**
```python
ComfyUIClient(base_url: str, api_key: Optional[str] = None, timeout: int = 30)
```

**Methods:**

- `generate(**params) -> Job` - Submit image generation job
- `get_job(job_id: str) -> Dict` - Get job status
- `health() -> Dict` - Check API health
- `estimate_cost(...) -> Dict` - Estimate generation cost
- `get_stats() -> Dict` - Get usage statistics
- `project_monthly_cost(...) -> Dict` - Project monthly costs
- `configure_gpu(gpu_type: str) -> Dict` - Configure GPU type

### Job

Represents an image generation job.

**Methods:**

- `status() -> Dict` - Get current status
- `wait_for_completion(...) -> GenerationResult` - Wait for job to complete
- `cancel() -> Dict` - Cancel the job

### GenerationResult

Result of a completed generation.

**Attributes:**

- `job_id: str` - Job identifier
- `status: str` - Job status
- `artifacts: List[Dict]` - Generated images info
- `error: Optional[str]` - Error message if failed

**Methods:**

- `download_image(index: int = 0, save_path: str = "image.png") -> str` - Download image

## Exception Types

- `ComfyUIClientError` - Base exception
- `APIError` - API returned an error
- `JobNotFoundError` - Job ID not found
- `JobFailedError` - Job failed to complete
- `TimeoutError` - Job timed out
- `ConnectionError` - Connection failed
- `AuthenticationError` - Invalid API key
- `RateLimitError` - Rate limit exceeded

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Type Checking

```python
pip install mypy
mypy comfyui_client
```

### Code Formatting

```bash
pip install black
black comfyui_client
```

## License

MIT License - see [LICENSE](../../LICENSE) file

## Support

- **Documentation:** See main project README
- **Issues:** https://github.com/ApeNIG/comfy-api-service/issues
- **API Docs:** http://localhost:8000/docs (when API is running)
