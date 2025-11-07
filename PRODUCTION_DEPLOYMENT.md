# Production Deployment Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-07
**Status:** Ready for Production

This guide walks you through deploying the ComfyUI API Service to production.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Quick Start (Docker Compose)](#quick-start-docker-compose)
5. [Cloud Deployment](#cloud-deployment)
6. [Post-Deployment Validation](#post-deployment-validation)
7. [Monitoring Setup](#monitoring-setup)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### Architecture

```
┌─────────────┐
│ Load        │
│ Balancer    │ (HTTPS, SSL termination)
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────────┐
│                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ API     │  │ API     │  │ API     │         │
│  │ Server  │  │ Server  │  │ Server  │         │
│  │ (x3)    │  │ (x3)    │  │ (x3)    │         │
│  └────┬────┘  └────┬────┘  └────┬────┘         │
│       │            │            │               │
│  ┌────▼────────────▼────────────▼───┐          │
│  │          Redis Cluster            │          │
│  │  (Queue, Cache, Rate Limiting)    │          │
│  └────┬──────────────────────────────┘          │
│       │                                          │
│  ┌────▼────┐  ┌─────────┐  ┌─────────┐         │
│  │ Worker  │  │ Worker  │  │ Worker  │         │
│  │ (x3)    │  │ (x3)    │  │ (x3)    │         │
│  └────┬────┘  └────┬────┘  └────┬────┘         │
│       │            │            │               │
│  ┌────▼────────────▼────────────▼───┐          │
│  │        ComfyUI Backend(s)         │          │
│  │         (GPU Instances)            │          │
│  └────────────────────────────────────┘         │
│                                                  │
└──────────────────────────────────────────────────┘
       │                    │
┌──────▼──────┐      ┌──────▼──────┐
│   S3/MinIO  │      │ Prometheus  │
│  (Artifacts)│      │  + Grafana  │
└─────────────┘      └─────────────┘
```

### Components

| Component | Purpose | Scaling Strategy |
|-----------|---------|------------------|
| **API Servers** | Handle HTTP requests | Horizontal (3+ instances) |
| **Workers** | Process jobs from queue | Horizontal (based on GPU availability) |
| **Redis** | Queue, cache, rate limiting | Managed service with replication |
| **ComfyUI** | GPU image generation | Horizontal (GPU instances) |
| **S3/MinIO** | Artifact storage | Managed service with auto-scaling |
| **Load Balancer** | Traffic distribution | Managed service |
| **Monitoring** | Metrics and alerting | Centralized (Prometheus/Grafana) |

---

## Prerequisites

### Required

- [x] Docker 20.10+ and Docker Compose 2.0+
- [x] 8GB+ RAM (16GB recommended)
- [x] 50GB+ disk space
- [x] Domain name with DNS access
- [x] SSL certificate (Let's Encrypt recommended)

### Recommended for Production

- [x] Managed Redis (AWS ElastiCache, Redis Cloud)
- [x] Managed S3 storage (AWS S3, GCS, Azure Blob)
- [x] GPU instance for ComfyUI (AWS g4dn, GCP n1-standard-4 + T4)
- [x] Monitoring (Prometheus + Grafana or Datadog)
- [x] Log aggregation (CloudWatch, Datadog, ELK)

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Testing/Staging)

**Best for:** Small deployments, staging environments, proof of concept

**Pros:**
- Simple setup (one command)
- All services bundled
- Good for testing

**Cons:**
- Single point of failure
- Manual scaling
- Not suitable for high traffic

**Timeline:** 1-2 hours

### Option 2: Kubernetes (Recommended for Production)

**Best for:** Production deployments, high availability, auto-scaling

**Pros:**
- Auto-scaling
- High availability
- Rolling updates
- Self-healing

**Cons:**
- Complex setup
- Requires K8s knowledge
- Higher operational overhead

**Timeline:** 1-2 days

### Option 3: Cloud Services (Recommended for Enterprises)

**Best for:** Enterprises, managed services, minimal ops

**Pros:**
- Fully managed
- Auto-scaling
- High SLA
- Minimal maintenance

**Cons:**
- Higher cost
- Vendor lock-in
- Less control

**Timeline:** 2-3 days (setup + integration)

---

## Quick Start (Docker Compose)

This is the fastest way to get running in production or staging.

### Step 1: Clone and Configure

```bash
# Clone repository
git clone https://github.com/ApeNIG/comfy-api-service.git
cd comfy-api-service

# Create environment file
cp .env.example .env

# Edit .env with your production values
nano .env
```

**Required changes in `.env`:**
```bash
# Set to production
ENVIRONMENT=production

# Enable security features
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true

# Configure Redis (use managed service in production)
REDIS_URL=redis://:YOUR_PASSWORD@your-redis-host:6379

# Configure MinIO/S3
MINIO_ENDPOINT=your-minio-or-s3-endpoint
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_USE_SSL=true

# Configure ComfyUI
COMFYUI_URL=http://your-comfyui-host:8188

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

### Step 2: Deploy Services

```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh production
```

The script will:
1. Build Docker images
2. Start infrastructure (Redis, MinIO)
3. Start ComfyUI backend
4. Start API and workers
5. Run smoke tests
6. Display service URLs

**Expected output:**
```
==================================================
Deployment Complete!
==================================================

Service URLs:
  - API:         http://localhost:8000
  - API Docs:    http://localhost:8000/docs
  - Health:      http://localhost:8000/health
  - Metrics:     http://localhost:8000/metrics
  - MinIO UI:    http://localhost:9001
```

### Step 3: Create Admin User and API Key

```bash
# Create admin user
curl -X POST http://localhost:8000/admin/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "role": "internal"
  }'

# Response: {"user_id": "user_abc123", ...}

# Create API key
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_abc123",
    "name": "Production Admin Key"
  }'

# Response: {"api_key": "cui_sk_...", ...}
# ⚠️ SAVE THIS KEY! It won't be shown again.
```

### Step 4: Validate Deployment

```bash
# Run validation script
./scripts/validate.sh
```

**Expected output:**
```
==================================================
Validation Summary
==================================================

Passed:  18
Failed:  0
Skipped: 2

Success Rate: 100% (18/18)

✓ All tests passed!
```

See [Post-Deployment Validation](#post-deployment-validation) for details.

---

## Cloud Deployment

### AWS Deployment

**Architecture:**
- **API:** ECS Fargate (3+ tasks)
- **Worker:** ECS Fargate (3+ tasks)
- **Redis:** ElastiCache (cluster mode)
- **Storage:** S3
- **ComfyUI:** EC2 g4dn.xlarge with GPU
- **Load Balancer:** ALB with HTTPS
- **Monitoring:** CloudWatch + Prometheus

**Step-by-step:**

#### 1. Set up VPC and Security Groups

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16

# Create security groups
# - API: Allow 8000 from ALB
# - Worker: No inbound (outbound only)
# - ComfyUI: Allow 8188 from workers
# - Redis: Allow 6379 from API/workers
```

#### 2. Set up ElastiCache

```bash
aws elasticache create-replication-group \
  --replication-group-id comfyui-redis \
  --replication-group-description "ComfyUI API Redis" \
  --engine redis \
  --cache-node-type cache.t3.medium \
  --num-cache-clusters 2 \
  --automatic-failover-enabled
```

#### 3. Set up S3 Bucket

```bash
aws s3 mb s3://comfyui-artifacts-prod
aws s3api put-bucket-versioning \
  --bucket comfyui-artifacts-prod \
  --versioning-configuration Status=Enabled

# Set lifecycle policy (7/30/90 day retention)
```

#### 4. Deploy ComfyUI on EC2

```bash
# Launch g4dn.xlarge with GPU
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type g4dn.xlarge \
  --security-group-ids sg-xxx \
  --subnet-id subnet-xxx \
  --user-data file://comfyui-setup.sh
```

**comfyui-setup.sh:**
```bash
#!/bin/bash
# Install NVIDIA drivers
# Install Docker
# Run ComfyUI container
docker run -d --gpus all -p 8188:8188 yanwk/comfyui-boot:latest
```

#### 5. Build and Push Docker Images

```bash
# Build image
docker build -t comfyui-api:latest .

# Tag and push to ECR
aws ecr create-repository --repository-name comfyui-api
docker tag comfyui-api:latest 123456789.dkr.ecr.us-west-2.amazonaws.com/comfyui-api:latest
docker push 123456789.dkr.ecr.us-west-2.amazonaws.com/comfyui-api:latest
```

#### 6. Create ECS Task Definitions

**API Task:**
```json
{
  "family": "comfyui-api",
  "containerDefinitions": [{
    "name": "api",
    "image": "123456789.dkr.ecr.us-west-2.amazonaws.com/comfyui-api:latest",
    "portMappings": [{"containerPort": 8000}],
    "environment": [
      {"name": "REDIS_URL", "value": "redis://your-elasticache:6379"},
      {"name": "AUTH_ENABLED", "value": "true"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/comfyui-api",
        "awslogs-region": "us-west-2"
      }
    }
  }]
}
```

**Worker Task:**
```json
{
  "family": "comfyui-worker",
  "containerDefinitions": [{
    "name": "worker",
    "image": "123456789.dkr.ecr.us-west-2.amazonaws.com/comfyui-api:latest",
    "command": ["poetry", "run", "arq", "apps.worker.main.WorkerSettings"],
    "environment": [
      {"name": "REDIS_URL", "value": "redis://your-elasticache:6379"},
      {"name": "COMFYUI_URL", "value": "http://10.0.1.100:8188"}
    ]
  }]
}
```

#### 7. Create ECS Services

```bash
# Create API service
aws ecs create-service \
  --cluster comfyui-cluster \
  --service-name comfyui-api \
  --task-definition comfyui-api \
  --desired-count 3 \
  --launch-type FARGATE \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...

# Create Worker service
aws ecs create-service \
  --cluster comfyui-cluster \
  --service-name comfyui-worker \
  --task-definition comfyui-worker \
  --desired-count 3 \
  --launch-type FARGATE
```

#### 8. Set up Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name comfyui-api-alb \
  --subnets subnet-xxx subnet-yyy \
  --security-groups sg-xxx

# Create target group
aws elbv2 create-target-group \
  --name comfyui-api-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxx \
  --health-check-path /health

# Add HTTPS listener with SSL certificate
aws elbv2 create-listener \
  --load-balancer-arn arn:aws:elasticloadbalancing:... \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=arn:aws:acm:... \
  --default-actions Type=forward,TargetGroupArn=arn:aws:elasticloadbalancing:...
```

#### 9. Configure DNS

```bash
# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers --names comfyui-api-alb --query 'LoadBalancers[0].DNSName')

# Create Route 53 record
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "api.yourdomain.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "'$ALB_DNS'"}]
      }
    }]
  }'
```

**Timeline:** 4-6 hours (experienced) to 1-2 days (first time)

### GCP Deployment

Similar to AWS, but using:
- **API/Worker:** Cloud Run or GKE
- **Redis:** Memorystore
- **Storage:** Cloud Storage
- **ComfyUI:** Compute Engine with GPU (n1-standard-4 + T4)
- **Load Balancer:** Cloud Load Balancing

### Azure Deployment

- **API/Worker:** Container Instances or AKS
- **Redis:** Azure Cache for Redis
- **Storage:** Azure Blob Storage
- **ComfyUI:** VM with GPU (NC-series)
- **Load Balancer:** Azure Load Balancer

---

## Post-Deployment Validation

After deployment, run comprehensive validation:

### Automated Validation

```bash
./scripts/validate.sh
```

### Manual Validation Checklist

#### Day 1 Checklist

- [ ] All containers/services healthy
- [ ] Health endpoint returns 200
- [ ] Metrics endpoint accessible
- [ ] API docs load at /docs
- [ ] Can create admin user
- [ ] Can create API key
- [ ] Can submit test job
- [ ] Job completes successfully
- [ ] Can download artifact
- [ ] Rate limit headers present
- [ ] Worker logs show startup
- [ ] Crash recovery ran
- [ ] Prometheus scraping metrics

#### Week 1 Checklist

- [ ] Monitor error rates (<0.5% target)
- [ ] Check P95 latency (<20s target)
- [ ] Check P99 latency (<40s target)
- [ ] Test crash recovery (kill worker)
- [ ] Test rate limiting (exceed quota)
- [ ] Load test with 100 jobs
- [ ] Review alert noise
- [ ] Verify backups working
- [ ] Test rollback procedure
- [ ] Security scan (OWASP)

#### Month 1 Checklist

- [ ] SLO compliance review
- [ ] Cost analysis
- [ ] User feedback collection
- [ ] Performance optimization
- [ ] Security audit
- [ ] Disaster recovery drill
- [ ] Documentation review
- [ ] On-call rotation tested

---

## Monitoring Setup

### Prometheus + Grafana

#### 1. Deploy Prometheus

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'comfyui-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'

  - job_name: 'comfyui-worker'
    static_configs:
      - targets: ['worker:8000']

rule_files:
  - 'recording_rules.yml'
  - 'alert_rules.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']
```

#### 2. Add Recording Rules

See [SLO.md](SLO.md) for complete recording rules:

```yaml
# recording_rules.yml
groups:
  - name: comfyui_slis
    interval: 30s
    rules:
      - record: job:api_success_ratio:5m
      - record: job:latency_p95_seconds:5m
      - record: job:latency_p99_seconds:5m
```

#### 3. Add Alert Rules

See [SLO.md](SLO.md) for complete alert rules:

```yaml
# alert_rules.yml
groups:
  - name: comfyui_slo_alerts
    rules:
      - alert: APISuccessRateLow
        expr: job:api_success_ratio:5m < 0.98
        for: 10m
        severity: critical
```

#### 4. Deploy Grafana

```bash
docker run -d \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  -v grafana-storage:/var/lib/grafana \
  grafana/grafana:latest
```

**Import dashboard:**
- Add Prometheus data source
- Create panels from SLO.md
- Set up alerting (Slack, PagerDuty)

### CloudWatch (AWS)

```bash
# Enable container insights
aws ecs update-cluster-settings \
  --cluster comfyui-cluster \
  --settings name=containerInsights,value=enabled

# Create log groups
aws logs create-log-group --log-group-name /ecs/comfyui-api
aws logs create-log-group --log-group-name /ecs/comfyui-worker

# Create alarms
aws cloudwatch put-metric-alarm \
  --alarm-name comfyui-high-error-rate \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --metric-name Errors \
  --namespace AWS/ECS \
  --period 300 \
  --statistic Sum \
  --threshold 10
```

---

## Troubleshooting

### Deployment Failures

#### API Won't Start

**Symptom:** Container exits immediately

**Check:**
```bash
docker-compose logs api
# Look for: Redis connection errors, import errors, config issues
```

**Common Fixes:**
- Verify REDIS_URL is correct
- Check MinIO credentials
- Ensure .env file is loaded
- Check port conflicts (8000)

#### Worker Not Processing Jobs

**Symptom:** Jobs stuck in "queued" status

**Check:**
```bash
docker-compose logs worker
# Look for: ARQ connection errors, ComfyUI unreachable
```

**Common Fixes:**
- Ensure worker container is running
- Check ComfyUI is accessible from worker
- Verify Redis connection
- Check job queue depth

#### ComfyUI Not Starting

**Symptom:** Worker logs show "ComfyUI unreachable"

**Check:**
```bash
docker-compose logs comfyui
curl http://localhost:8188/system_stats
```

**Common Fixes:**
- Verify GPU available (nvidia-smi)
- Check CUDA drivers installed
- Increase memory limit
- Check disk space for models

### Performance Issues

#### High Latency (P95 > 20s)

**Check:**
```bash
# Queue depth
curl http://localhost:8000/metrics | grep comfyui_queue_depth

# Worker utilization
curl http://localhost:8000/metrics | grep comfyui_jobs_in_progress
```

**Fixes:**
- Scale workers horizontally
- Upgrade GPU instances
- Optimize ComfyUI settings (fewer steps)
- Add Redis replicas

#### Rate Limit Issues

**Symptom:** Users hitting 429 too often

**Check:**
```bash
grep ROLE_QUOTAS apps/api/config.py
```

**Fixes:**
- Increase rate limits for role
- Add burst allowance
- Upgrade users to PRO
- Implement caching

### Security Issues

#### Exposed Secrets

**Check:**
```bash
# Check environment variables not in .env
docker-compose config | grep -E "(PASSWORD|SECRET|KEY)"

# Check .gitignore
cat .gitignore | grep .env
```

**Fixes:**
- Move secrets to .env
- Rotate exposed credentials
- Use secrets management (AWS Secrets Manager)

#### Unauthorized Access

**Check:**
```bash
# Verify auth enabled
curl http://localhost:8000/api/v1/jobs
# Should return 401 if auth enabled
```

**Fixes:**
- Set AUTH_ENABLED=true
- Enable rate limiting
- Add IP allowlisting
- Review API key permissions

---

## Next Steps

After successful deployment:

1. **Week 1:** Monitor metrics, tune alerts, test recovery
2. **Week 2:** Load testing, performance optimization
3. **Week 3:** User onboarding, documentation
4. **Month 1:** Cost optimization, SLO review

See:
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Full checklist
- [SLO.md](SLO.md) - Monitoring and SLOs
- [LIMITS.md](LIMITS.md) - API contract
- [ROADMAP.md](ROADMAP.md) - Future plans

---

**Questions?** Open an issue: https://github.com/ApeNIG/comfy-api-service/issues

**Status:** ✅ **PRODUCTION READY**
