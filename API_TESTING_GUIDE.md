# ComfyUI API Service - Testing Guide

**Version:** 1.0
**Last Updated:** 2025-11-06

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Testing Individual Endpoints](#testing-individual-endpoints)
3. [Example Requests](#example-requests)
4. [Testing Scenarios](#testing-scenarios)
5. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

1. **Both services must be running:**
   - ComfyUI: `http://localhost:8188`
   - FastAPI: `http://localhost:8000`

2. **ComfyUI must have at least one model installed**

### Start the Services

```bash
# Start ComfyUI (in terminal 1)
cd /workspaces/ComfyUI
python3 main.py --cpu --listen 0.0.0.0 --port 8188

# Start FastAPI (in terminal 2)
cd /workspaces/comfy-api-service
poetry run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verify Services are Running

```bash
# Check FastAPI
curl http://localhost:8000/

# Check health endpoint
curl http://localhost:8000/health

# Expected response when both services are healthy:
{
  "status": "healthy",
  "api_version": "1.0.0",
  "comfyui_status": "connected",
  "comfyui_url": "http://localhost:8188",
  "timestamp": "2025-11-06T12:00:00Z"
}
```

---

## Testing Individual Endpoints

### 1. Root Endpoint

**Test basic connectivity:**

```bash
curl -X GET http://localhost:8000/
```

**Expected Response:**
```json
{
  "service": "ComfyUI API Service",
  "status": "online",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

**What this tests:** API service is running

---

### 2. Health Check

**Test service health:**

```bash
curl -X GET http://localhost:8000/health | jq .
```

**Expected Response (Healthy):**
```json
{
  "status": "healthy",
  "api_version": "1.0.0",
  "comfyui_status": "connected",
  "comfyui_url": "http://localhost:8188",
  "timestamp": "2025-11-06T12:00:00.000000"
}
```

**Expected Response (Degraded):**
```json
{
  "status": "degraded",
  "api_version": "1.0.0",
  "comfyui_status": "disconnected",
  "comfyui_url": "http://localhost:8188",
  "timestamp": "2025-11-06T12:00:00.000000"
}
```

**What this tests:**
- API service health
- ComfyUI connectivity
- Service integration

---

### 3. List Available Models

**Get list of models:**

```bash
curl -X GET http://localhost:8000/models | jq .
```

**Expected Response:**
```json
{
  "models": [
    {
      "name": "sd_xl_base_1.0.safetensors",
      "path": "sd_xl_base_1.0.safetensors",
      "size": null,
      "type": "checkpoint"
    },
    {
      "name": "v1-5-pruned-emaonly.safetensors",
      "path": "v1-5-pruned-emaonly.safetensors",
      "size": null,
      "type": "checkpoint"
    }
  ],
  "total": 2
}
```

**What this tests:**
- ComfyUI communication
- Model discovery
- API can read ComfyUI's object_info endpoint

---

### 4. Generate Single Image (Simple)

**Generate with minimal parameters:**

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains"
  }' | jq .
```

**Expected Response:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "completed",
  "image_url": "/view?filename=api_generated_abc12345_00001_.png&type=output",
  "image_data": null,
  "error": null,
  "metadata": {
    "prompt": "A beautiful sunset over mountains",
    "negative_prompt": null,
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg_scale": 7.0,
    "sampler": "euler_a",
    "seed": 1234567890,
    "model": "sd_xl_base_1.0.safetensors",
    "generation_time": 15.234
  },
  "created_at": "2025-11-06T12:00:00.000000",
  "started_at": "2025-11-06T12:00:01.000000",
  "completed_at": "2025-11-06T12:00:16.234000"
}
```

**What this tests:**
- Full workflow integration
- Prompt submission
- Image generation
- Status tracking
- Response formatting

---

### 5. Generate Image (Advanced)

**Generate with all parameters:**

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A majestic lion in the savanna, golden hour lighting, photorealistic, 4k, detailed fur",
    "negative_prompt": "blurry, low quality, cartoon, anime, distorted, ugly",
    "width": 1024,
    "height": 1024,
    "steps": 30,
    "cfg_scale": 7.5,
    "sampler": "dpm_plus_plus_2m",
    "seed": 42,
    "model": "sd_xl_base_1.0.safetensors",
    "batch_size": 1
  }' | jq .
```

**What this tests:**
- All parameter validation
- Complex prompt handling
- Custom seed (reproducibility)
- Advanced sampler selection

---

### 6. Batch Generation

**Generate multiple images:**

```bash
curl -X POST http://localhost:8000/api/v1/generate/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {
        "prompt": "A cat sitting on a windowsill",
        "width": 512,
        "height": 512
      },
      {
        "prompt": "A dog playing in a park",
        "width": 512,
        "height": 512
      },
      {
        "prompt": "A bird flying in the sky",
        "width": 512,
        "height": 512
      }
    ]
  }' | jq .
```

**Expected Response:**
```json
{
  "batch_id": "batch-xyz-789",
  "jobs": [
    {
      "job_id": "job-1",
      "status": "completed",
      "image_url": "/view?filename=...",
      ...
    },
    {
      "job_id": "job-2",
      "status": "completed",
      "image_url": "/view?filename=...",
      ...
    },
    {
      "job_id": "job-3",
      "status": "completed",
      "image_url": "/view?filename=...",
      ...
    }
  ],
  "total": 3,
  "completed": 3,
  "failed": 0
}
```

**What this tests:**
- Batch processing
- Multiple sequential requests
- Aggregate status tracking
- Error handling per item

---

## Example Requests

### Using Python

```python
import requests
import json

# Generate an image
response = requests.post(
    "http://localhost:8000/api/v1/generate",
    json={
        "prompt": "A beautiful landscape with mountains and a lake",
        "width": 1024,
        "height": 1024,
        "steps": 30
    }
)

result = response.json()
print(f"Job ID: {result['job_id']}")
print(f"Status: {result['status']}")
print(f"Image URL: {result['image_url']}")
print(f"Generation time: {result['metadata']['generation_time']}s")
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

async function generateImage() {
  try {
    const response = await axios.post(
      'http://localhost:8000/api/v1/generate',
      {
        prompt: 'A beautiful landscape with mountains and a lake',
        width: 1024,
        height: 1024,
        steps: 30
      }
    );

    console.log('Job ID:', response.data.job_id);
    console.log('Status:', response.data.status);
    console.log('Image URL:', response.data.image_url);
    console.log('Generation time:', response.data.metadata.generation_time, 's');
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
  }
}

generateImage();
```

### Using cURL (Save to file)

```bash
# Generate and save response
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset",
    "width": 1024,
    "height": 1024
  }' > response.json

# Extract image URL
IMAGE_URL=$(jq -r '.image_url' response.json)

# Download the image
curl "http://localhost:8188${IMAGE_URL}" -o generated_image.png
```

---

## Testing Scenarios

### Scenario 1: Validation Errors

**Test invalid width (not divisible by 8):**

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A test image",
    "width": 513
  }'
```

**Expected Response (422 Validation Error):**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "width"],
      "msg": "Dimension must be divisible by 8, got 513",
      "input": 513
    }
  ]
}
```

---

### Scenario 2: ComfyUI Unavailable

**Condition:** ComfyUI is not running

```bash
# Stop ComfyUI first, then:
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A test image"
  }'
```

**Expected Response (503 Service Unavailable):**
```json
{
  "detail": "ComfyUI service is not available"
}
```

---

### Scenario 3: Timeout

**Test with very high steps (may timeout):**

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A complex scene",
    "steps": 150,
    "width": 2048,
    "height": 2048
  }'
```

**If timeout occurs:**
```json
{
  "detail": "Image generation timed out: Job abc-123 did not complete within 300.0s"
}
```

---

### Scenario 4: Invalid Model

**Test with non-existent model:**

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A test image",
    "model": "nonexistent_model.safetensors"
  }'
```

**Expected:** May succeed (validation happens in ComfyUI) or return error from ComfyUI

---

### Scenario 5: Reproducibility (Same Seed)

**Generate same image twice:**

```bash
# First generation
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A red apple on a table",
    "seed": 12345,
    "steps": 20
  }' > result1.json

# Second generation (same parameters)
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A red apple on a table",
    "seed": 12345,
    "steps": 20
  }' > result2.json

# Compare (should be very similar or identical)
```

**Expected:** Both images should be identical or very similar

---

## Testing Scenarios (Continued)

### Scenario 6: Stress Test (Multiple Requests)

**Test handling of concurrent/sequential requests:**

```bash
#!/bin/bash
# Generate 5 images sequentially
for i in {1..5}; do
  echo "Request $i..."
  curl -X POST http://localhost:8000/api/v1/generate \
    -H "Content-Type: application/json" \
    -d "{
      \"prompt\": \"Test image $i\",
      \"width\": 512,
      \"height\": 512,
      \"steps\": 10
    }" | jq -r '.job_id'
done
```

**What to observe:**
- All requests complete successfully
- No crashes or timeouts
- Response times are consistent
- Memory usage doesn't grow unbounded

---

## Interactive Testing with Swagger UI

### Access Swagger Documentation

1. Start the API service
2. Open browser: `http://localhost:8000/docs`
3. Interactive API documentation available

### Features:
- **Try it out:** Execute requests directly from browser
- **Request samples:** See example payloads
- **Response schemas:** View expected responses
- **Validation:** Real-time validation of parameters

### Using Swagger UI:

1. **Click on an endpoint** (e.g., POST /api/v1/generate)
2. **Click "Try it out"**
3. **Modify the request body** with your parameters
4. **Click "Execute"**
5. **View the response** below

---

## Automated Testing Script

### Complete Test Suite

Create a file `test_api.sh`:

```bash
#!/bin/bash

API_URL="http://localhost:8000"
PASSED=0
FAILED=0

function test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    local expected_status=$5

    echo "Testing: $name"

    if [ -z "$data" ]; then
        response=$(curl -s -w "\\n%{http_code}" -X $method "$API_URL$endpoint")
    else
        response=$(curl -s -w "\\n%{http_code}" -X $method "$API_URL$endpoint" \\
            -H "Content-Type: application/json" \\
            -d "$data")
    fi

    status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$status" -eq "$expected_status" ]; then
        echo "✓ PASSED (Status: $status)"
        ((PASSED++))
    else
        echo "✗ FAILED (Expected: $expected_status, Got: $status)"
        echo "Response: $body"
        ((FAILED++))
    fi
    echo ""
}

echo "======================================"
echo "ComfyUI API Service Test Suite"
echo "======================================"
echo ""

# Test 1: Root endpoint
test_endpoint "Root endpoint" "GET" "/" "" 200

# Test 2: Health check
test_endpoint "Health check" "GET" "/health" "" 200

# Test 3: List models
test_endpoint "List models" "GET" "/models" "" 200

# Test 4: Ping endpoint
test_endpoint "Ping endpoint" "GET" "/ping" "" 200

# Test 5: Generate image (valid)
test_endpoint "Generate image (valid)" "POST" "/api/v1/generate" \\
    '{"prompt": "A test image", "width": 512, "height": 512, "steps": 10}' 201

# Test 6: Generate image (invalid width)
test_endpoint "Generate image (invalid width)" "POST" "/api/v1/generate" \\
    '{"prompt": "A test image", "width": 513}' 422

# Test 7: Generate image (missing prompt)
test_endpoint "Generate image (missing prompt)" "POST" "/api/v1/generate" \\
    '{"width": 512}' 422

echo "======================================"
echo "Test Results"
echo "======================================"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✓ All tests passed!"
    exit 0
else
    echo "✗ Some tests failed"
    exit 1
fi
```

**Run the test suite:**

```bash
chmod +x test_api.sh
./test_api.sh
```

---

## Performance Testing

### Load Testing with Apache Bench

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test health endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 http://localhost:8000/health

# Test root endpoint
ab -n 100 -c 10 http://localhost:8000/
```

### Load Testing with wrk

```bash
# Install wrk
sudo apt-get install wrk

# Test for 30 seconds with 10 connections
wrk -t10 -c10 -d30s http://localhost:8000/health
```

---

## Troubleshooting

### Issue: "ComfyUI service is not available"

**Symptoms:**
- Health check shows "comfyui_status": "disconnected"
- Generation requests return 503 error

**Solutions:**

1. **Verify ComfyUI is running:**
   ```bash
   curl http://localhost:8188/system_stats
   ```

2. **Check ComfyUI logs:**
   ```bash
   cat /workspaces/comfy-data/comfy.log
   ```

3. **Start ComfyUI manually:**
   ```bash
   cd /workspaces/ComfyUI
   python3 main.py --cpu --listen 0.0.0.0 --port 8188
   ```

---

### Issue: "Module not found" errors

**Symptoms:**
- API fails to start
- Import errors in logs

**Solutions:**

1. **Install dependencies:**
   ```bash
   poetry install
   ```

2. **Verify virtual environment:**
   ```bash
   poetry env info
   poetry show
   ```

---

### Issue: Validation errors (422)

**Symptoms:**
- Request returns 422 status code
- Error message about field validation

**Solutions:**

1. **Check request format:**
   - Width/height must be divisible by 8
   - Prompt must not be empty
   - Steps must be between 1 and 150
   - CFG scale between 1.0 and 30.0

2. **View detailed error:**
   ```bash
   curl -X POST ... | jq .detail
   ```

---

### Issue: Timeout during generation

**Symptoms:**
- Request takes very long
- Returns 504 Gateway Timeout

**Solutions:**

1. **Reduce complexity:**
   - Lower steps (20 instead of 50)
   - Smaller dimensions (512x512 instead of 1024x1024)

2. **Increase timeout:**
   - Modify ComfyUIClient timeout parameter
   - Adjust Uvicorn timeout settings

3. **Check system resources:**
   ```bash
   htop  # Check CPU/memory usage
   ```

---

### Issue: Images not generating despite success response

**Symptoms:**
- Status shows "completed"
- image_url is null or invalid

**Solutions:**

1. **Check ComfyUI output directory:**
   ```bash
   ls -la /workspaces/ComfyUI/output/
   ```

2. **Verify workflow execution:**
   - Check ComfyUI logs for errors
   - Test workflow directly in ComfyUI UI

3. **Check model availability:**
   ```bash
   curl http://localhost:8000/models
   ```

---

### Issue: Port already in use

**Symptoms:**
- Error: "Address already in use"
- API fails to start

**Solutions:**

1. **Find process using port:**
   ```bash
   lsof -i :8000
   ```

2. **Kill existing process:**
   ```bash
   kill -9 <PID>
   ```

3. **Use different port:**
   ```bash
   uvicorn apps.api.main:app --port 8001
   ```

---

## Testing Checklist

### Before Deployment

- [ ] All endpoints respond with correct status codes
- [ ] Health check shows "healthy" status
- [ ] Models list is populated
- [ ] Simple image generation works
- [ ] Advanced image generation with all parameters works
- [ ] Batch generation works
- [ ] Validation errors are handled correctly
- [ ] ComfyUI unavailable scenario handled gracefully
- [ ] Swagger documentation is accessible
- [ ] No memory leaks during stress testing
- [ ] Response times are acceptable
- [ ] Error messages are informative

### After Deployment

- [ ] Service auto-starts on container/server restart
- [ ] Logs are being written correctly
- [ ] Both services communicate properly
- [ ] Generated images are accessible
- [ ] API documentation is reachable

---

**Last Updated:** 2025-11-06
**Tested On:** FastAPI 0.111.0, ComfyUI latest
**Status:** Ready for testing
