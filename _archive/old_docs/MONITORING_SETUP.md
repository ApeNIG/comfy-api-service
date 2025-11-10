# Monitoring and Cost Tracking Setup

**Goal:** Track costs, performance metrics, and usage patterns for your ComfyUI API Service

---

## Overview

The monitoring system tracks:
- **Cost estimates** for RunPod GPU usage
- **Generation metrics** (time, success rate, throughput)
- **Monthly projections** based on usage patterns
- **Real-time stats** for all jobs

---

## Quick Start

### 1. Configure GPU Type

Tell the system what GPU you're using for accurate cost estimation:

```bash
curl -X POST "http://localhost:8000/api/v1/monitoring/configure-gpu?gpu_type=rtx_4000_ada"
```

**Available GPU types:**
- `cpu` - Local CPU (free, slow)
- `local_gpu` - Local GPU (free, fast)
- `rtx_3060` - RunPod Spot ($0.10/hour)
- `rtx_4000_ada` - RunPod Spot ($0.15/hour) **← Recommended**
- `rtx_4090` - RunPod On-Demand ($0.40/hour)
- `a40` - RunPod On-Demand ($0.50/hour)

### 2. Check Current Stats

```bash
curl http://localhost:8000/api/v1/monitoring/stats
```

**Example response:**
```json
{
  "total_jobs": 25,
  "successful_jobs": 24,
  "failed_jobs": 1,
  "success_rate_percent": 96.0,
  "total_images_generated": 48,
  "total_cost_usd": 0.0624,
  "total_runtime_hours": 0.42,
  "avg_time_per_image_seconds": 3.2,
  "avg_cost_per_image_usd": 0.0013
}
```

### 3. Estimate Cost Before Generating

```bash
curl "http://localhost:8000/api/v1/monitoring/estimate-cost?width=512&height=512&steps=20&num_images=1"
```

**Example response:**
```json
{
  "gpu_type": "rtx_4000_ada",
  "hourly_rate": 0.15,
  "estimated_time_seconds": 3.0,
  "total_time_seconds": 3.0,
  "estimated_cost_usd": 0.000125,
  "cost_per_image": 0.000125,
  "num_images": 1
}
```

### 4. Project Monthly Costs

```bash
curl "http://localhost:8000/api/v1/monitoring/project-monthly-cost?images_per_day=100&avg_time_seconds=3"
```

**Example response:**
```json
{
  "gpu_type": "rtx_4000_ada",
  "hourly_rate": 0.15,
  "images_per_day": 100,
  "daily_runtime_hours": 0.08,
  "daily_cost_usd": 0.0125,
  "monthly_images": 3000,
  "monthly_runtime_hours": 2.5,
  "monthly_cost_usd": 0.38,
  "cost_per_image": 0.0001
}
```

---

## API Endpoints

### GET `/api/v1/monitoring/stats`
Get overall statistics for all jobs.

**Response:**
- `total_jobs`: Total number of jobs submitted
- `successful_jobs`: Number of successfully completed jobs
- `failed_jobs`: Number of failed jobs
- `success_rate_percent`: Success rate (0-100%)
- `total_images_generated`: Total images created
- `total_cost_usd`: Total estimated cost in USD
- `total_runtime_hours`: Total GPU runtime in hours
- `avg_time_per_image_seconds`: Average generation time
- `avg_cost_per_image_usd`: Average cost per image

### GET `/api/v1/monitoring/recent-jobs?limit=10`
Get recent job history with metrics.

**Parameters:**
- `limit` (optional): Number of jobs to return (1-100, default: 10)

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "j_abc123",
      "timestamp": "2025-11-08T12:34:56.789Z",
      "status": "succeeded",
      "duration_seconds": 3.2,
      "num_images": 1,
      "cost_usd": 0.00013,
      "width": 512,
      "height": 512,
      "steps": 20
    }
  ],
  "total_tracked": 100
}
```

### POST `/api/v1/monitoring/estimate-cost`
Estimate cost for a planned image generation.

**Parameters:**
- `width`: Image width (64-2048, default: 512)
- `height`: Image height (64-2048, default: 512)
- `steps`: Diffusion steps (1-150, default: 20)
- `num_images`: Number of images (1-10, default: 1)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/monitoring/estimate-cost?width=1024&height=1024&steps=30&num_images=4"
```

### GET `/api/v1/monitoring/project-monthly-cost`
Project monthly costs based on expected usage.

**Parameters:**
- `images_per_day`: Average images per day (1-10000, default: 10)
- `avg_time_seconds`: Average generation time (0.1-3600, default: 3.0)

**Example:**
```bash
curl "http://localhost:8000/api/v1/monitoring/project-monthly-cost?images_per_day=500&avg_time_seconds=2.5"
```

### GET `/api/v1/monitoring/gpu-pricing`
Get pricing information for all GPU types.

**Response:**
```json
{
  "pricing": {
    "cpu": 0.0,
    "rtx_3060": 0.10,
    "rtx_4000_ada": 0.15,
    "rtx_4090": 0.40,
    "a40": 0.50,
    "local_gpu": 0.0
  },
  "current_gpu": "rtx_4000_ada",
  "current_hourly_rate": 0.15,
  "generation_times": {
    "512x512_10steps": 1.5,
    "512x512_20steps": 3,
    "1024x1024_20steps": 10
  }
}
```

### POST `/api/v1/monitoring/configure-gpu`
Configure GPU type for cost tracking.

**Parameters:**
- `gpu_type`: GPU type (required)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/monitoring/configure-gpu?gpu_type=rtx_4090"
```

---

## Cost Estimation Examples

### Example 1: Simple Image (512x512, 20 steps)
```bash
# Estimate cost
curl "http://localhost:8000/api/v1/monitoring/estimate-cost?width=512&height=512&steps=20&num_images=1"

# Result (RTX 4000 Ada):
# - Time: ~3 seconds
# - Cost: ~$0.00013 per image
# - Monthly (100 images/day): ~$3.90/month
```

### Example 2: High-Resolution (1024x1024, 30 steps)
```bash
# Estimate cost
curl "http://localhost:8000/api/v1/monitoring/estimate-cost?width=1024&height=1024&steps=30&num_images=1"

# Result (RTX 4000 Ada):
# - Time: ~15 seconds
# - Cost: ~$0.00063 per image
# - Monthly (50 images/day): ~$0.94/month
```

### Example 3: Batch Generation (4 images at 512x512)
```bash
# Estimate cost
curl "http://localhost:8000/api/v1/monitoring/estimate-cost?width=512&height=512&steps=20&num_images=4"

# Result (RTX 4000 Ada):
# - Time: ~12 seconds total
# - Cost: ~$0.0005 total ($0.000125 per image)
# - Monthly (25 batches/day): ~$3.75/month
```

---

## Monthly Cost Projections

### Low Volume (10 images/day)
```bash
curl "http://localhost:8000/api/v1/monitoring/project-monthly-cost?images_per_day=10&avg_time_seconds=3"

# Result (RTX 4000 Ada):
# - Daily runtime: 0.08 hours (~5 minutes)
# - Daily cost: $0.01
# - Monthly cost: $0.38
```

### Medium Volume (100 images/day)
```bash
curl "http://localhost:8000/api/v1/monitoring/project-monthly-cost?images_per_day=100&avg_time_seconds=3"

# Result (RTX 4000 Ada):
# - Daily runtime: 0.83 hours (~50 minutes)
# - Daily cost: $0.13
# - Monthly cost: $3.75
```

### High Volume (1000 images/day)
```bash
curl "http://localhost:8000/api/v1/monitoring/project-monthly-cost?images_per_day=1000&avg_time_seconds=3"

# Result (RTX 4000 Ada):
# - Daily runtime: 8.33 hours
# - Daily cost: $1.25
# - Monthly cost: $37.50
```

---

## Cost Tracking Best Practices

### 1. Set Budget Alerts

Add to your monitoring script:
```bash
#!/bin/bash
# check-budget.sh

MONTHLY_BUDGET=50.00  # $50/month limit

stats=$(curl -s http://localhost:8000/api/v1/monitoring/stats)
total_cost=$(echo $stats | jq -r '.total_cost_usd')

# Extrapolate to monthly
days_in_month=30
current_day=$(date +%d)
projected_monthly=$(echo "$total_cost * $days_in_month / $current_day" | bc -l)

if (( $(echo "$projected_monthly > $MONTHLY_BUDGET" | bc -l) )); then
    echo "WARNING: Projected monthly cost ($projected_monthly) exceeds budget ($MONTHLY_BUDGET)"
    # Send alert (email, Slack, etc.)
fi
```

### 2. Monitor Cost Per Image

```bash
#!/bin/bash
# monitor-cost-per-image.sh

TARGET_COST=0.002  # $0.002 target cost per image

stats=$(curl -s http://localhost:8000/api/v1/monitoring/stats)
avg_cost=$(echo $stats | jq -r '.avg_cost_per_image_usd')

if (( $(echo "$avg_cost > $TARGET_COST" | bc -l) )); then
    echo "Cost per image ($avg_cost) is higher than target ($TARGET_COST)"
    echo "Consider: reducing steps, using smaller GPU, or optimizing prompts"
fi
```

### 3. Track Success Rate

```bash
#!/bin/bash
# check-success-rate.sh

MIN_SUCCESS_RATE=95.0  # 95% minimum success rate

stats=$(curl -s http://localhost:8000/api/v1/monitoring/stats)
success_rate=$(echo $stats | jq -r '.success_rate_percent')

if (( $(echo "$success_rate < $MIN_SUCCESS_RATE" | bc -l) )); then
    echo "WARNING: Success rate ($success_rate%) is below threshold ($MIN_SUCCESS_RATE%)"
    # Check logs for errors
fi
```

---

## Integration with Job Submission

The monitoring system automatically tracks all jobs when you submit them through the API. No additional code needed!

**Example workflow:**
```bash
# 1. Estimate cost first
curl "http://localhost:8000/api/v1/monitoring/estimate-cost?width=512&height=512&steps=20"
# Output: Will cost ~$0.00013, take ~3 seconds

# 2. Submit job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A sunset",
    "width": 512,
    "height": 512,
    "steps": 20
  }'
# Output: {"job_id": "j_abc123", ...}

# 3. Wait for completion...

# 4. Check updated stats
curl http://localhost:8000/api/v1/monitoring/stats
# Output: total_cost_usd increased by $0.00013
```

---

## Prometheus Metrics Integration

The monitoring system also exposes metrics in Prometheus format at `/metrics`:

```
# Image generation metrics
generation_total{status="succeeded"} 24
generation_total{status="failed"} 1
generation_latency_seconds_sum 76.8
generation_latency_seconds_count 24

# Cost metrics (custom)
generation_cost_usd_total 0.0624
generation_cost_usd_per_image 0.0013
```

**Set up Prometheus scraping:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'comfyui-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

---

## Dashboard Visualization

Access the monitoring dashboard at:

👉 **http://localhost:8000/dashboard** (coming soon!)

Features:
- Real-time cost tracking
- Generation time charts
- Success rate trends
- Monthly cost projections
- Recent job history

---

## Troubleshooting

### Issue: Costs seem too high

**Check current GPU configuration:**
```bash
curl http://localhost:8000/api/v1/monitoring/gpu-pricing
```

**Verify you're configured for the correct GPU:**
- If using RunPod Spot: `rtx_4000_ada` ($0.15/hour)
- If using Local GPU: `local_gpu` ($0.00/hour)
- If using CPU: `cpu` ($0.00/hour)

**Reconfigure if needed:**
```bash
curl -X POST "http://localhost:8000/api/v1/monitoring/configure-gpu?gpu_type=local_gpu"
```

### Issue: Stats showing 0 jobs

**Cause:** Monitoring system tracks jobs when they're submitted through `/api/v1/jobs`

**Solution:** Make sure you're using the async job endpoint, not the old sync endpoint

### Issue: Want to reset stats

The monitoring system tracks stats in-memory. To reset:
```bash
docker compose restart api
```

For persistent stats, consider adding Redis-backed storage (future enhancement).

---

## Next Steps

1. **Deploy RunPod GPU** - See [RUNPOD_DEPLOYMENT_GUIDE.md](RUNPOD_DEPLOYMENT_GUIDE.md)
2. **Enable Authentication** - See [SECURITY_TEST_REPORT.md](SECURITY_TEST_REPORT.md)
3. **Use Python SDK** - See SDK documentation (coming next!)
4. **Set up alerts** - Integrate with your monitoring stack

---

## Summary

The monitoring system provides:
- ✅ **Real-time cost tracking** for GPU usage
- ✅ **Performance metrics** for optimization
- ✅ **Monthly projections** for budgeting
- ✅ **API endpoints** for programmatic access
- ✅ **Prometheus integration** for dashboards

**Cost per 1000 images (512x512, 20 steps, RTX 4000 Ada):** ~$1.25

**Expected monthly cost (100 images/day):** ~$3.75/month

**Questions?** Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
