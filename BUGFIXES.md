# Bug Fixes and Technical Improvements

This document tracks critical bugs discovered and fixed during development.

---

## Critical Bug: Worker Uploading 0 Bytes Instead of Actual Images

**Status:** ✅ Fixed (commit b954fe3)
**Date:** 2025-11-08
**Severity:** Critical - Prevented any actual image generation

### Problem

The worker was uploading 0-byte files to MinIO instead of downloading actual image data from ComfyUI. This resulted in:
- Jobs showing `"status": "succeeded"`
- Presigned URLs pointing to 0-byte files
- No actual image data being stored or retrievable

### Root Cause Analysis

**Location:** [apps/worker/main.py:132-185](apps/worker/main.py#L132-L185)

The worker had a TODO comment and placeholder code:
```python
# TODO: Download actual image from ComfyUI
image_data = b""  # Placeholder
```

This was uploading empty bytes instead of fetching the actual image from ComfyUI's URL.

### Technical Details

**Why This Bug Was Subtle:**

1. **ComfyUI generated the image successfully** - The image existed in ComfyUI's `/opt/ComfyUI/output/` directory (verified at 672KB PNG)
2. **Worker received the correct URL** - ComfyUI returned valid response with image metadata
3. **Storage upload succeeded** - MinIO accepted the 0-byte upload without error
4. **Job status showed success** - All components reported successful completion
5. **Presigned URL was valid** - The URL worked, but pointed to an empty file

**Expert Feedback Received:**

An expert identified two key implementation requirements:
1. **Use absolute URLs** with full base URL instead of relative paths
2. **Implement URL encoding** for query parameters (filename, subfolder, type)

Example from expert:
```python
from urllib.parse import quote

url = f"{self.base_url}/view?filename={quote(filename)}&type={quote(image_type)}"
if subfolder:
    url += f"&subfolder={quote(subfolder)}"
```

### The Fix

**Files Modified:**

1. **[apps/worker/main.py:132-185](apps/worker/main.py#L132-L185)** - Implemented robust image download
2. **[apps/api/services/comfyui_client.py:416-453](apps/api/services/comfyui_client.py#L416-L453)** - Updated URL construction

**Implementation:**

```python
# Download image from ComfyUI using absolute URL
logger.info(f"[{job_id}] Downloading image from: {result.image_url}")

import httpx
async with httpx.AsyncClient(timeout=60.0) as http_client:
    response = await http_client.get(result.image_url)
    response.raise_for_status()
    image_bytes = response.content

if not image_bytes:
    raise RuntimeError(f"Downloaded 0 bytes from {result.image_url}")

logger.info(f"[{job_id}] Downloaded {len(image_bytes)} bytes")

# Upload to storage
storage_client.upload_bytes(
    object_name,
    image_bytes,
    content_type="image/png"
)

logger.info(f"[{job_id}] Uploaded {len(image_bytes)} bytes to MinIO: {object_name}")
```

**Key Improvements:**
- ✅ Created dedicated `httpx.AsyncClient` instance for download
- ✅ Used absolute URLs with proper base URL
- ✅ Added URL encoding via `urllib.parse.quote()`
- ✅ Validated non-empty byte content before upload
- ✅ Added detailed byte count logging for debugging
- ✅ Proper error handling with informative messages

### Verification

**Test Case:** Generated 512x512 sunset image

**Before Fix:**
```
[j_xxx] Uploaded 0 bytes to MinIO
```

**After Fix:**
```
[j_997a726a1664] Downloading image from: http://comfyui:8188/view?filename=...
[j_997a726a1664] Downloaded 404202 bytes
[j_997a726a1664] Uploaded 404202 bytes to MinIO: jobs/j_997a726a1664/image_0.png
```

**Result:** Successfully downloaded and stored 512x512 PNG image (404,202 bytes / 395 KB)

---

## Bug: API Parameter Validation Failures

**Status:** ✅ Fixed (commit b954fe3)
**Date:** 2025-11-08
**Severity:** High - Prevented any job submission

### Problem

API requests were failing with HTTP 400 Bad Request:
```json
{
  "error": {
    "type": "prompt_outputs_failed_validation",
    "message": "Workflow validation failed",
    "details": "Invalid node outputs"
  }
}
```

### Root Cause

**Mismatch between API defaults and ComfyUI availability:**

1. **Model Default:** API requested `sd_xl_base_1.0.ckpt` but only `v1-5-pruned-emaonly.ckpt` was available
2. **Sampler Name:** API sent `euler_a` but ComfyUI expected `euler_ancestral`

### The Fix

**Files Modified:**

1. **[apps/api/models/requests.py:11](apps/api/models/requests.py#L11)** - Fixed sampler enum
2. **[apps/api/models/requests.py:88-92](apps/api/models/requests.py#L88-L92)** - Fixed model default
3. **[workflows/t2i_basic.json:7](workflows/t2i_basic.json#L7)** - Updated workflow template

**Changes:**

```python
# Before:
class SamplerType(str, Enum):
    EULER_A = "euler_a"

# After:
class SamplerType(str, Enum):
    EULER_A = "euler_ancestral"
```

```python
# Before:
model: str = Field(
    default="sd_xl_base_1.0.ckpt",
    ...
)

# After:
model: str = Field(
    default="v1-5-pruned-emaonly.ckpt",
    description="Model checkpoint to use",
    examples=["v1-5-pruned-emaonly.ckpt", "sd_xl_base_1.0.ckpt"]
)
```

### Verification

Successfully submitted job with default parameters - no validation errors.

---

## Bug: Timeout Too Short for CPU Mode

**Status:** ✅ Fixed (commit b954fe3)
**Date:** 2025-11-08
**Severity:** Medium - Jobs timing out on slower hardware

### Problem

Jobs were timing out exactly at the 300-second timeout limit:
```
Job j_xxx did not complete within 300.0s
```

However, the image **did** exist in ComfyUI's output directory (539KB), indicating generation completed but after the timeout.

**Actual generation time:** 301.3 seconds (just over the limit)

### Root Cause

**CPU Mode Performance:**
- ComfyUI configured with `--cpu` flag due to GPU compute capability mismatch (Quadro P2000 6.1 vs PyTorch requirement 7.0+)
- CPU generation is significantly slower than GPU (10-20x)
- Default timeout of 300s was insufficient for even basic 512x512 images

### The Fix

**File Modified:** [apps/api/config.py:38](apps/api/config.py#L38)

```python
# Before:
comfyui_timeout: float = 300.0  # 5 minutes

# After:
comfyui_timeout: float = 600.0  # 10 minutes
```

### Verification

**Test:** Generated 512x512 image with 10 steps in CPU mode

**Results:**
- Generation time: 534 seconds (~9 minutes)
- Job status: succeeded
- Image downloaded: 404,202 bytes

---

## Bug: Health Check Failing with RuntimeError

**Status:** ✅ Fixed (commit b954fe3)
**Date:** 2025-11-08
**Severity:** Medium - Blocked synchronous API endpoints

### Problem

API's `/generate` endpoint was returning HTTP 503 "ComfyUI service is not available" even though:
- ComfyUI was accessible: `curl http://comfyui:8188/queue` returned valid JSON
- DNS resolution worked: `172.19.0.4 comfyui`
- Container networking was functional

### Root Cause

**Location:** [apps/api/services/comfyui_client.py:114-143](apps/api/services/comfyui_client.py#L114-L143)

The `health_check()` method was using `self.client.get()` which required the context manager to be entered first. However, health checks were being called BEFORE entering the context manager, causing:
```
RuntimeError: Client not initialized. Use 'async with ComfyUIClient()' context manager.
```

### Expert Feedback

Expert recommended:
1. Implement health check with **retry logic** (5 attempts)
2. Try **multiple endpoints** (`/queue`, `/system_stats`, `/`)
3. Use **exponential backoff** between retries
4. Create a **dedicated httpx client** to avoid context manager dependency

### The Fix

**File Modified:** [apps/api/services/comfyui_client.py:114-143](apps/api/services/comfyui_client.py#L114-L143)

**Implementation:**

```python
async def health_check(self) -> bool:
    """
    Check if ComfyUI service is available.

    Uses retry logic with multiple endpoints to ensure robust connectivity.
    Creates its own HTTP client to avoid dependency on context manager.

    Returns:
        True if service is healthy, False otherwise
    """
    endpoints = ["/queue", "/system_stats", "/"]

    async with httpx.AsyncClient(base_url=self.base_url, timeout=5.0) as health_client:
        for attempt in range(5):
            for endpoint in endpoints:
                try:
                    response = await health_client.get(endpoint)
                    if response.status_code == 200:
                        logger.debug(f"Health check succeeded on {endpoint} (attempt {attempt + 1})")
                        return True
                except Exception as e:
                    logger.debug(f"Health check failed for {endpoint} (attempt {attempt + 1}): {e}")
                    pass

            # Exponential backoff
            if attempt < 4:  # Don't sleep on last attempt
                await asyncio.sleep(0.6 * (attempt + 1))

    logger.error("Health check failed after all retry attempts")
    return False
```

**Key Features:**
- ✅ Creates independent httpx client with 5s timeout
- ✅ Tries 3 different endpoints for redundancy
- ✅ 5 retry attempts with exponential backoff
- ✅ Detailed debug logging
- ✅ No dependency on context manager state

### Verification

Health checks now succeed reliably even during ComfyUI startup.

---

## Bug: Docker Cache Not Picking Up Code Changes

**Status:** ✅ Fixed
**Date:** 2025-11-08
**Severity:** Medium - Deployment issue

### Problem

After modifying code and rebuilding containers, the old code was still running:
```bash
docker compose build worker
docker compose restart worker
# Still running old code!
```

### Root Cause

**Two Issues:**
1. `docker compose build` cached layers even with code changes
2. `docker compose restart` restarted the OLD container instead of creating a new one from the new image

### The Fix

**Correct deployment sequence:**

```bash
# Build with no cache
docker compose build worker --no-cache

# Force recreate container from new image
docker compose up -d --force-recreate worker
```

**Verification Command:**
```bash
docker exec comfyui-worker cat /app/apps/worker/main.py | grep "Downloaded.*bytes"
```

---

## Summary of Fixes

| Bug | Severity | Impact | Files Changed |
|-----|----------|--------|---------------|
| 0-byte image uploads | Critical | No actual images stored | worker/main.py, comfyui_client.py |
| API parameter mismatch | High | All jobs rejected | models/requests.py, workflows/t2i_basic.json |
| Timeout too short | Medium | CPU jobs failing | config.py |
| Health check failing | Medium | Sync endpoints blocked | comfyui_client.py |
| Docker cache issues | Medium | Deployment problems | N/A (workflow fix) |

---

## Testing Recommendations

When deploying these fixes:

1. **Test image download:** Verify byte count in logs matches file size
2. **Test CPU mode:** Allow at least 10 minutes for 512x512 generation
3. **Test health checks:** Should succeed within 5 seconds
4. **Rebuild properly:** Always use `--no-cache` and `--force-recreate`
5. **Verify in container:** Use `docker exec` to check actual deployed code

---

## Performance Metrics (After Fixes)

**Test Configuration:**
- Hardware: CPU mode (Quadro P2000 unsupported)
- Image: 512x512 pixels
- Steps: 10 (reduced for testing)
- Model: v1-5-pruned-emaonly.ckpt

**Results:**
- Generation time: 534 seconds (~9 minutes)
- Image size: 404,202 bytes (395 KB)
- Status: succeeded
- Storage: MinIO with presigned URL
- Quality: Full PNG with actual pixel data

---

## Lessons Learned

1. **Always verify bytes downloaded** - Log byte counts to catch 0-byte bugs early
2. **Use absolute URLs** - Avoid base_url conflicts in nested async clients
3. **Implement proper retries** - Health checks should be resilient with exponential backoff
4. **Account for hardware variations** - CPU mode needs much longer timeouts
5. **Verify deployed code** - Docker cache can mask deployment issues
6. **Test end-to-end** - Successful API response doesn't mean the image was actually saved

---

**All fixes verified working as of commit b954fe3**
