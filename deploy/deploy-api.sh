#!/bin/bash
# ComfyUI API Service - Deployment Script
# Run this after setup-vps.sh

set -e

echo "============================================================"
echo "       ComfyUI API Service - Production Deployment"
echo "============================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating production .env file..."
    cat > .env << 'EOF'
# Production Configuration
AUTH_ENABLED=true
RATE_LIMIT_ENABLED=true

# API Configuration
COMFYUI_API_BASE_URL=http://comfyui:8188
REDIS_URL=redis://redis:6379
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=CHANGE_THIS_IN_PRODUCTION_$(openssl rand -hex 16)
MINIO_BUCKET=comfyui-outputs

# Monitoring
GPU_TYPE=cpu
LOG_LEVEL=INFO

# Security
CORS_ORIGINS=["*"]
EOF
    echo "✓ Created .env file"
    echo ""
    echo "IMPORTANT: Edit .env and change MINIO_SECRET_KEY!"
    echo ""
fi

# Start services
echo "Starting Docker services..."
docker compose down
docker compose up -d

# Wait for services
echo ""
echo "Waiting for services to start..."
sleep 10

# Check health
echo ""
echo "Checking API health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ API is healthy!"
else
    echo "✗ API health check failed"
    echo "Check logs: docker compose logs api"
    exit 1
fi

# Test monitoring endpoint
echo ""
echo "Testing monitoring endpoint..."
if curl -f http://localhost:8000/api/v1/monitoring/stats > /dev/null 2>&1; then
    echo "✓ Monitoring is working!"
else
    echo "✗ Monitoring check failed"
fi

echo ""
echo "============================================================"
echo "                 Deployment Complete!"
echo "============================================================"
echo ""
echo "API is running at: http://localhost:8000"
echo ""
echo "Next steps:"
echo "  1. Set up domain and SSL: ./deploy/setup-ssl.sh your-domain.com"
echo "  2. Generate API keys: ./deploy/create-api-key.sh"
echo "  3. Test the API: curl http://localhost:8000/api/v1/monitoring/stats"
echo ""
echo "View logs: docker compose logs -f api"
echo ""
