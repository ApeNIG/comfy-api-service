# Service Level Objectives (SLOs)

**Last Updated:** 2025-11-07
**Version:** 1.0.0

This document defines the reliability promises for the ComfyUI API Service.

---

## Overview

Service Level Objectives (SLOs) define what "good" looks like for this service. These are measurable targets that guide operational decisions and alert thresholds.

**Key Concepts:**
- **SLI (Service Level Indicator):** What we measure (e.g., latency, success rate)
- **SLO (Service Level Objective):** Target value for an SLI (e.g., 95% < 20s)
- **Error Budget:** Allowed failures = 100% - SLO (e.g., 1% for 99% SLO)

---

## Image Generation SLOs

### Latency (P95)

**Target:** 95% of jobs for ≤2 MP images complete in **≤ 20 seconds**

**Measurement:**
```promql
histogram_quantile(0.95,
  sum(rate(comfyui_job_duration_seconds_bucket{
    width*height <= 2000000
  }[5m])) by (le)
)
```

**Rationale:** Most requests are small images for rapid prototyping. 20s provides good UX.

**Impact if missed:**
- User frustration
- Perceived service slowness
- Potential churn for FREE tier

---

### Latency (P99)

**Target:** 99% of jobs complete in **≤ 40 seconds**

**Measurement:**
```promql
histogram_quantile(0.99,
  sum(rate(comfyui_job_duration_seconds_bucket[5m])) by (le)
)
```

**Rationale:** Tail latency matters for production use cases. 40s is acceptable for batch workflows.

**Impact if missed:**
- PRO user dissatisfaction
- SLA breach for enterprise users
- Potential for timeouts in client apps

---

## API Availability SLOs

### Control Plane Success Rate

**Target:** **99.5%** of control plane requests succeed

**Endpoints:**
- `POST /api/v1/jobs` (job submission)
- `GET /api/v1/jobs/{id}` (status polling)
- `DELETE /api/v1/jobs/{id}` (cancellation)
- `GET /health`
- `GET /metrics`

**Measurement:**
```promql
sum(rate(comfyui_http_requests_total{
  code=~"2..|3..",
  endpoint=~"/api/v1/(jobs.*|health|metrics)"
}[5m]))
/
sum(rate(comfyui_http_requests_total{
  endpoint=~"/api/v1/(jobs.*|health|metrics)"
}[5m]))
```

**Rationale:** Control plane must be highly available. Users should always be able to submit/check jobs.

**Impact if missed:**
- Users cannot submit work
- Dashboard outages
- Support escalations

---

### Data Plane Reliability

**Target:** **< 0.5%** job failure rate (excluding user errors)

**Measurement:**
```promql
sum(rate(comfyui_jobs_total{status="failed",error_type!="ValidationError"}[1h]))
/
sum(rate(comfyui_jobs_total[1h]))
```

**Rationale:** Jobs should succeed unless user provides bad input. Infrastructure failures should be rare.

**Impact if missed:**
- Wasted compute/credits
- User complaints
- Revenue impact (refunds)

---

## Real-Time SLOs

### WebSocket Progress Freshness

**Target:** First progress event within **< 2 seconds** of job start

**Measurement:**
```promql
histogram_quantile(0.95,
  sum(rate(comfyui_ws_first_event_seconds_bucket[5m])) by (le)
)
```

**Rationale:** Real-time progress is a key UX differentiator. Delays feel broken.

**Impact if missed:**
- Users think job is stuck
- Increased support queries
- Competitive disadvantage

---

### Queue Depth

**Target:** Queue depth **< 50 jobs** during normal operation

**Measurement:**
```promql
comfyui_queue_depth
```

**Rationale:** Deep queues indicate insufficient worker capacity. Leads to long wait times.

**Impact if missed:**
- Increased latency (queuing time)
- Poor UX for all users
- Need to scale workers

---

## Recording Rules

Add these to your Prometheus configuration (`prometheus.yml` or recording rules file):

```yaml
groups:
  - name: comfyui_slis
    interval: 30s
    rules:
      # API Success Rate (5min window)
      - record: job:api_success_ratio:5m
        expr: |
          sum(rate(comfyui_http_requests_total{code=~"2..|3..",endpoint=~"/api/v1/(jobs.*|health)"}[5m]))
          /
          sum(rate(comfyui_http_requests_total{endpoint=~"/api/v1/(jobs.*|health)"}[5m]))

      # Job Success Rate (1h window, excluding validation errors)
      - record: job:success_ratio:1h
        expr: |
          sum(rate(comfyui_jobs_total{status="succeeded"}[1h]))
          /
          sum(rate(comfyui_jobs_total[1h]))

      # P95 Job Latency (5min window)
      - record: job:latency_p95_seconds:5m
        expr: |
          histogram_quantile(0.95,
            sum(rate(comfyui_job_duration_seconds_bucket[5m])) by (le)
          )

      # P99 Job Latency (5min window)
      - record: job:latency_p99_seconds:5m
        expr: |
          histogram_quantile(0.99,
            sum(rate(comfyui_job_duration_seconds_bucket[5m])) by (le)
          )

      # Current Queue Depth
      - record: job:queue_depth:current
        expr: comfyui_queue_depth

      # Worker Utilization
      - record: job:worker_utilization:5m
        expr: |
          comfyui_jobs_in_progress
          /
          comfyui_active_workers
```

---

## Alert Rules

Pragmatic alerts based on SLO violations:

```yaml
groups:
  - name: comfyui_slo_alerts
    rules:
      # Critical: API unavailable
      - alert: APISuccessRateLow
        expr: job:api_success_ratio:5m < 0.98
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "API success rate below 98% for 10 minutes"
          description: "Current success rate: {{ $value | humanizePercentage }}"
          runbook: "Check API logs, Redis connectivity, worker health"

      # Warning: Latency degradation
      - alert: LatencyP95High
        expr: job:latency_p95_seconds:5m > 20
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency above 20s for 30 minutes"
          description: "Current P95: {{ $value }}s"
          runbook: "Check ComfyUI backend, consider scaling workers"

      # Warning: Queue backing up
      - alert: QueueDepthHigh
        expr: comfyui_queue_depth > 50
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Queue depth above 50 for 10 minutes"
          description: "Current depth: {{ $value }}"
          runbook: "Scale workers horizontally, check worker health"

      # Critical: Job failure rate high
      - alert: JobFailureRateHigh
        expr: |
          sum(rate(comfyui_jobs_total{status="failed",error_type!="ValidationError"}[1h]))
          /
          sum(rate(comfyui_jobs_total[1h]))
          > 0.005
        for: 15m
        labels:
          severity: critical
        annotations:
          summary: "Job failure rate > 0.5% for 15 minutes"
          description: "Failure rate: {{ $value | humanizePercentage }}"
          runbook: "Check ComfyUI logs, MinIO connectivity, worker errors"

      # Warning: Worker inflight jobs stuck
      - alert: WorkerJobsStuck
        expr: |
          comfyui_jobs_in_progress > 0
          and
          delta(comfyui_jobs_in_progress[10m]) == 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Worker has jobs stuck for 10 minutes"
          description: "Stuck jobs: {{ $value }}"
          runbook: "Check worker logs, restart worker, crash recovery will handle"

      # Info: Backend error spike
      - alert: BackendErrorSpike
        expr: |
          sum(rate(comfyui_backend_requests_total{status=~"error|timeout"}[5m]))
          >
          5 * sum(rate(comfyui_backend_requests_total{status=~"error|timeout"}[1h] offset 1h))
        for: 5m
        labels:
          severity: info
        annotations:
          summary: "Backend error rate spiked 5x"
          description: "Check ComfyUI health and logs"
```

---

## SLO Monitoring Dashboard

Suggested Grafana panels:

### Row 1: SLO Compliance

| Panel | Query | Visualization |
|-------|-------|---------------|
| **API Success Rate** | `job:api_success_ratio:5m` | Gauge (99.5% target line) |
| **P95 Latency** | `job:latency_p95_seconds:5m` | Graph (20s target line) |
| **P99 Latency** | `job:latency_p99_seconds:5m` | Graph (40s target line) |
| **Job Success Rate** | `job:success_ratio:1h` | Gauge (99.5% target line) |

### Row 2: Capacity

| Panel | Query | Visualization |
|-------|-------|---------------|
| **Queue Depth** | `comfyui_queue_depth` | Graph (50 threshold line) |
| **Active Workers** | `comfyui_active_workers` | Stat |
| **Jobs In Progress** | `comfyui_jobs_in_progress` | Graph |
| **Worker Utilization** | `job:worker_utilization:5m` | Gauge (80% warning) |

### Row 3: Error Budget

| Panel | Query | Visualization |
|-------|-------|---------------|
| **API Error Budget** | `1 - job:api_success_ratio:5m` | Gauge (0.5% threshold) |
| **Job Failure Rate** | `1 - job:success_ratio:1h` | Graph (0.5% threshold) |
| **Backend Errors** | `sum(rate(comfyui_backend_requests_total{status="error"}[5m]))` | Graph |

---

## SLO Review Process

**Frequency:** Monthly

**Participants:** Engineering, Product, Support

**Agenda:**
1. Review SLO compliance (last 30 days)
2. Analyze SLO violations (root causes)
3. Adjust targets if needed (too loose or too tight)
4. Update alerts and runbooks
5. Plan infrastructure improvements

---

## Error Budget Policy

**Monthly Error Budget:** 0.5% (99.5% SLO)

**Example:** For 100,000 requests/month:
- **Allowed failures:** 500 requests
- **Current failures:** (check dashboard)
- **Remaining budget:** 500 - current

**Policy:**
- **> 50% budget remaining:** Ship aggressively, take risks
- **25-50% remaining:** Normal velocity
- **< 25% remaining:** Freeze non-critical features, focus on reliability
- **Budget exhausted:** Incident response mode, no new features

---

## Operational Thresholds

Beyond SLOs, these operational metrics guide scaling decisions:

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Queue depth | 50 | 100 | Scale workers |
| Worker CPU | 70% | 85% | Add workers |
| Redis memory | 70% | 85% | Upgrade instance |
| MinIO disk | 70% | 85% | Add storage |
| API P99 latency | 40s | 60s | Investigate bottleneck |

---

## Appendix: Metric Reference

All metrics exposed at `/metrics`:

### Job Metrics
- `comfyui_jobs_total{status}` - Total jobs by status
- `comfyui_jobs_created_total` - Jobs submitted
- `comfyui_job_duration_seconds` - Job latency histogram
- `comfyui_queue_depth` - Current queue size
- `comfyui_jobs_in_progress` - Jobs being processed
- `comfyui_active_workers` - Worker count

### API Metrics
- `comfyui_http_requests_total{method,endpoint,status}` - HTTP requests
- `comfyui_http_request_duration_seconds{method,endpoint}` - Request latency

### Storage Metrics
- `comfyui_storage_uploads_total{status}` - Upload count
- `comfyui_storage_upload_bytes_total` - Bytes uploaded

### Backend Metrics
- `comfyui_backend_requests_total{status}` - ComfyUI requests
- `comfyui_backend_request_duration_seconds` - Backend latency

### Redis Metrics
- `comfyui_redis_operations_total{operation,status}` - Redis ops

---

**Questions or feedback?**
- Slack: #comfyui-api-reliability
- Email: sre@example.com
- On-call: PagerDuty
