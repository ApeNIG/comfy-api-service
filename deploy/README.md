# Production Deployment Scripts

Automated deployment scripts for ComfyUI API Service on a VPS.

## Quick Deploy (30 Minutes)

### Prerequisites
- DigitalOcean account (or any VPS provider)
- Domain name (optional, for SSL)
- SSH access to your server

### Step 1: Create VPS

**DigitalOcean:**
1. Create Droplet: Ubuntu 22.04 LTS
2. Size: $12/month (2GB RAM, 1 vCPU)
3. Add your SSH key
4. Note the IP address

**Other providers:** Any Ubuntu 22.04 server with 2GB RAM works

### Step 2: Push Code to GitHub

```bash
# From your local machine
git add .
git commit -m "Production deployment ready"
git push origin main
```

### Step 3: Deploy to Server

SSH into your server and run:

```bash
# SSH to your server
ssh root@YOUR_SERVER_IP

# Clone repository
git clone https://github.com/YOUR_USERNAME/comfy-api-service.git
cd comfy-api-service

# Make scripts executable
chmod +x deploy/*.sh

# Run setup
./deploy/setup-vps.sh

# Deploy API
./deploy/deploy-api.sh

# Setup SSL (optional, requires domain)
./deploy/setup-ssl.sh api.yourdomain.com

# Generate API key
./deploy/create-api-key.sh
```

## What Gets Deployed

- **ComfyUI API** - REST API server
- **Worker** - Background job processor
- **Redis** - Caching and rate limiting
- **MinIO** - Image storage
- **ComfyUI Backend** - Image generation engine
- **Nginx** - Reverse proxy (optional, for SSL)

## Scripts Reference

### `setup-vps.sh`
Initial server setup - run once

**What it does:**
- Updates system packages
- Installs Docker & Docker Compose
- Installs Nginx & Certbot
- Configures firewall

**Usage:**
```bash
./deploy/setup-vps.sh
```

### `deploy-api.sh`
Deploys the API service

**What it does:**
- Creates .env file with production settings
- Starts all Docker containers
- Runs health checks
- Shows next steps

**Usage:**
```bash
./deploy/deploy-api.sh
```

### `setup-ssl.sh`
Sets up HTTPS with Let's Encrypt

**What it does:**
- Configures Nginx reverse proxy
- Obtains SSL certificate
- Sets up auto-renewal

**Usage:**
```bash
./deploy/setup-ssl.sh your-domain.com
```

**Requirements:**
- Domain pointing to your server IP
- Ports 80 and 443 open

### `create-api-key.sh`
Generates API keys for users

**What it does:**
- Creates secure API key
- Displays key (save it!)

**Usage:**
```bash
# Default: PRO tier
./deploy/create-api-key.sh

# Custom user and tier
./deploy/create-api-key.sh username FREE
./deploy/create-api-key.sh username PRO
./deploy/create-api-key.sh username ENTERPRISE
```

## Post-Deployment

### Test the API

```bash
# Health check
curl https://your-domain.com/health

# Get stats
curl https://your-domain.com/api/v1/monitoring/stats

# With API key
curl -H "X-API-Key: YOUR_API_KEY" \
  https://your-domain.com/api/v1/monitoring/stats
```

### Use from Local Machine

```bash
# Install SDK
cd sdk/python && pip install -e .

# Generate images
python demo/image_generator.py \
  --url https://your-domain.com \
  --api-key YOUR_API_KEY \
  --prompt "A beautiful landscape"
```

### Monitor Logs

```bash
# All services
docker compose logs -f

# Just API
docker compose logs -f api

# Just worker
docker compose logs -f worker
```

## Configuration

### Environment Variables

Edit `.env` file on your server:

```bash
# Security (IMPORTANT!)
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true

# Change this!
MINIO_SECRET_KEY=your-secure-secret-here

# GPU type for cost tracking
GPU_TYPE=cpu  # or rtx_4000_ada, rtx_4090, etc.

# CORS (if needed)
CORS_ORIGINS=["https://your-frontend.com"]
```

After changing `.env`:
```bash
docker compose restart api worker
```

### Rate Limits

Default limits per tier (per minute):

- **FREE**: 10 requests
- **PRO**: 100 requests
- **ENTERPRISE**: 1000 requests

To change: Edit `apps/api/middleware/rate_limit.py`

## Adding GPU Backend (Optional)

For 100x faster generation, add RunPod GPU:

1. Create RunPod account
2. Launch RTX 4000 Ada pod ($0.15/hour)
3. Install ComfyUI on pod
4. Update `.env`:
   ```bash
   COMFYUI_API_BASE_URL=https://your-pod-id-8188.proxy.runpod.net
   GPU_TYPE=rtx_4000_ada
   ```
5. Restart: `docker compose restart api worker`

**Result:** 9 minutes → 3 seconds per image!

See [RUNPOD_DEPLOYMENT_GUIDE.md](../RUNPOD_DEPLOYMENT_GUIDE.md) for details.

## Troubleshooting

### API won't start

```bash
# Check logs
docker compose logs api

# Restart services
docker compose down
docker compose up -d
```

### Can't access from outside

```bash
# Check firewall
ufw status

# Allow ports
ufw allow 80/tcp
ufw allow 443/tcp

# Check Nginx
nginx -t
systemctl status nginx
```

### SSL certificate fails

```bash
# Verify domain points to server
dig your-domain.com

# Check DNS propagation (may take time)
# Try again after DNS updates
```

### Out of memory

Upgrade to larger droplet:
- $18/month (4GB RAM) recommended for production
- $24/month (8GB RAM) for high traffic

## Security Checklist

Before going live:

- [ ] `AUTH_ENABLED=true`
- [ ] `RATE_LIMIT_ENABLED=true`
- [ ] Changed `MINIO_SECRET_KEY`
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Strong API keys generated
- [ ] Backups configured
- [ ] Monitoring set up

## Cost Summary

### Minimal (CPU only)
- **VPS**: $12/month
- **Total**: $12/month
- **Speed**: Slow (9 min/image)

### Production (with GPU)
- **VPS**: $12/month
- **RunPod GPU**: $0.38/month (100 images/day)
- **Total**: $12.38/month
- **Speed**: Fast (3 sec/image)

## Support

- **Documentation**: [PRODUCTION_DEPLOYMENT.md](../PRODUCTION_DEPLOYMENT.md)
- **API Reference**: [MONITORING_SETUP.md](../MONITORING_SETUP.md)
- **SDK Guide**: [sdk/python/README.md](../sdk/python/README.md)
- **GPU Setup**: [RUNPOD_DEPLOYMENT_GUIDE.md](../RUNPOD_DEPLOYMENT_GUIDE.md)

## Next Steps

1. ✅ Deploy to VPS
2. ✅ Set up SSL
3. ✅ Generate API keys
4. 📊 Monitor usage
5. 🚀 Add GPU backend (optional)
6. 🔧 Customize for your needs
