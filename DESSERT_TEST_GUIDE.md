# Dessert Prompt A/B Testing Guide

Since you're running in a Codespace/WSL2 environment where Docker networking requires special handling, here are **two ways** to run your dessert prompt test:

## Method 1: Browser-Based A/B Testing (Recommended - Works Now!)

You confirmed the dashboards are working, so use this:

### Steps:

1. **Open A/B Testing Dashboard**
   - Go to: http://localhost:8080/abtest_dashboard.html

2. **Configure the Test**

   **Base Prompt:**
   ```
   Hyperrealistic still life of a stainless steel dessert cup filled with scoops of salted caramel ice cream. A melting caramel-coated chocolate bar leans diagonally against the scoops, dripping thick golden caramel that runs down the cup and pools below. Studio lighting with soft warm reflections on a brown background, detailed textures, rich highlights, cinematic composition, modern food photography, ultra sharp focus.
   ```

   **Variant 1 (Fast):**
   - Steps: `10`
   - Width: `512`
   - Height: `512`
   - CFG Scale: `7.0`
   - Sampler: `euler_ancestral`

   **Variant 2 (Quality):**
   - Steps: `30`
   - Width: `512`
   - Height: `512`
   - CFG Scale: `7.0`
   - Sampler: `euler_ancestral`

3. **Run the Test**
   - Click "Run A/B Test"
   - Images should appear inline
   - Compare generation times and costs

4. **View Results**
   - Images displayed side-by-side
   - Generation time for each variant
   - Cost comparison
   - Download images if needed

---

## Method 2: Python SDK from Within Docker Container

Since the API isn't accessible from the host due to WSL2 networking, run Python from inside the container:

### Create the test script:

```bash
cat > /tmp/dessert_test.py << 'EOF'
import requests
import time
import json

API_URL = "http://localhost:8000"

DESSERT_PROMPT = """Hyperrealistic still life of a stainless steel dessert cup filled with scoops of salted caramel ice cream. A melting caramel-coated chocolate bar leans diagonally against the scoops, dripping thick golden caramel that runs down the cup and pools below. Studio lighting with soft warm reflections on a brown background, detailed textures, rich highlights, cinematic composition, modern food photography, ultra sharp focus."""

def test_variant(name, steps):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")

    # Submit job
    payload = {
        "prompt": DESSERT_PROMPT,
        "width": 512,
        "height": 512,
        "steps": steps,
        "cfg_scale": 7.0,
        "sampler_name": "euler_ancestral",
        "num_images": 1
    }

    start = time.time()
    resp = requests.post(f"{API_URL}/api/v1/generate", json=payload)
    job_id = resp.json()['job_id']
    print(f"Job ID: {job_id}")

    # Poll for completion
    while True:
        status_resp = requests.get(f"{API_URL}/api/v1/jobs/{job_id}")
        status = status_resp.json()

        if status['status'] == 'completed':
            elapsed = time.time() - start
            image_url = status['outputs'][0]['url']
            print(f"✓ Completed in {elapsed:.1f}s")
            print(f"  Image: {image_url}")
            return {'name': name, 'time': elapsed, 'url': image_url}
        elif status['status'] == 'failed':
            print(f"✗ Failed: {status.get('error')}")
            return None

        time.sleep(1)

print("Dessert Prompt A/B Test")
print("="*60)

results = []
results.append(test_variant("Fast (10 steps)", 10))
time.sleep(2)
results.append(test_variant("Quality (30 steps)", 30))

print(f"\n{'='*60}")
print("RESULTS")
print(f"{'='*60}")
for r in results:
    if r:
        print(f"{r['name']:20} {r['time']:.1f}s")
        print(f"  {r['url']}")
EOF
```

### Run it:

```bash
docker cp /tmp/dessert_test.py comfyui-api:/tmp/
docker exec comfyui-api python3 /tmp/dessert_test.py
```

---

## Method 3: Check Existing Test Results

If you've already run tests through the dashboard, check the generated images:

```bash
# View in MinIO browser
open http://localhost:9001
# Login: minioadmin / minioadmin
# Browse bucket: comfyui-artifacts

# Or check API stats
docker exec comfyui-api curl -s http://localhost:8000/api/v1/monitoring/stats | jq
```

---

## Expected Results

### Fast Variant (10 steps):
- Generation time: ~3-5 seconds
- Cost: ~$0.000010-0.000020
- Quality: Good for previews, may lack fine details

### Quality Variant (30 steps):
- Generation time: ~8-12 seconds
- Cost: ~$0.000030-0.000060
- Quality: Better details, smoother caramel drips, sharper focus

### What to Compare:
1. **Detail Quality**: Caramel texture, ice cream scoops, reflections
2. **Generation Speed**: Is 3x faster worth the quality tradeoff?
3. **Cost**: Is 3x more expensive justified for final images?

---

## Troubleshooting

### Dashboard not loading?
```bash
# Check web server
curl http://localhost:8080/

# Restart if needed
docker restart intelligent_yalow
```

### API not responding?
```bash
# Check API health
docker exec comfyui-api curl -s http://localhost:8000/healthz

# Check logs
docker logs comfyui-api --tail=50
```

### Images not appearing?
- Check MinIO: http://localhost:9001
- Verify bucket exists: `comfyui-artifacts`
- Check browser console (F12) for errors

---

## Next Steps

After comparing results:

1. **Choose your default settings** based on the quality/cost/speed tradeoff
2. **Test other parameters**:
   - Different resolutions (768x768, 1024x1024)
   - Different samplers (euler, dpm_2, etc.)
   - Different CFG scales (5.0, 7.0, 9.0)
3. **Document your findings** for your production workload
4. **Set up automation** with your preferred settings

Enjoy your dessert images! 🍨
