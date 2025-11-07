#!/bin/bash
set -e

# Production Deployment Script for ComfyUI API Service
# Usage: ./scripts/deploy.sh [environment]
# Environments: dev, staging, production

ENVIRONMENT=${1:-staging}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=================================================="
echo "ComfyUI API Service - Deployment Script"
echo "Environment: $ENVIRONMENT"
echo "=================================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Pre-deployment checks
log_info "Step 1/8: Running pre-deployment checks..."

# Check Docker installed
if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker."
    exit 1
fi
log_info "✓ Docker installed"

# Check Docker Compose installed
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose not found. Please install Docker Compose."
    exit 1
fi
log_info "✓ Docker Compose installed"

# Check .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    log_warn ".env file not found. Creating from .env.example..."
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
        log_warn "Please edit .env with your production values before proceeding."
        exit 1
    else
        log_error "Neither .env nor .env.example found."
        exit 1
    fi
fi
log_info "✓ .env file exists"

# Step 2: Build Docker images
log_info "Step 2/8: Building Docker images..."
cd "$PROJECT_ROOT"
docker-compose build --no-cache
log_info "✓ Images built successfully"

# Step 3: Stop existing containers
log_info "Step 3/8: Stopping existing containers..."
docker-compose down || true
log_info "✓ Existing containers stopped"

# Step 4: Start infrastructure services
log_info "Step 4/8: Starting infrastructure services (Redis, MinIO)..."
docker-compose up -d redis minio

# Wait for Redis
log_info "Waiting for Redis to be ready..."
timeout 30s bash -c 'until docker-compose exec -T redis redis-cli ping 2>/dev/null; do sleep 1; done' || {
    log_error "Redis failed to start within 30 seconds"
    exit 1
}
log_info "✓ Redis is ready"

# Wait for MinIO
log_info "Waiting for MinIO to be ready..."
timeout 30s bash -c 'until docker-compose exec -T minio mc alias set myminio http://localhost:9000 minioadmin minioadmin 2>/dev/null; do sleep 1; done' || {
    log_error "MinIO failed to start within 30 seconds"
    exit 1
}
log_info "✓ MinIO is ready"

# Create MinIO bucket
log_info "Creating MinIO bucket..."
docker-compose exec -T minio mc mb myminio/comfyui-artifacts --ignore-existing || true
docker-compose exec -T minio mc anonymous set download myminio/comfyui-artifacts || true
log_info "✓ MinIO bucket configured"

# Step 5: Start ComfyUI (if available)
if grep -q "comfyui:" "$PROJECT_ROOT/docker-compose.yml"; then
    log_info "Step 5/8: Starting ComfyUI..."
    docker-compose up -d comfyui

    log_info "Waiting for ComfyUI to be ready (this may take 2-3 minutes)..."
    timeout 180s bash -c 'until curl -sf http://localhost:8188/system_stats >/dev/null 2>&1; do sleep 5; done' || {
        log_warn "ComfyUI not responding. Continuing without it (some tests will skip)."
    }
    log_info "✓ ComfyUI started (or skipped)"
else
    log_info "Step 5/8: ComfyUI not in docker-compose.yml, skipping..."
fi

# Step 6: Start API and Worker
log_info "Step 6/8: Starting API and Worker services..."
docker-compose up -d api worker
log_info "✓ API and Worker started"

# Wait for API health check
log_info "Waiting for API to be ready..."
timeout 60s bash -c 'until curl -sf http://localhost:8000/health >/dev/null 2>&1; do sleep 2; done' || {
    log_error "API failed to start within 60 seconds"
    docker-compose logs api
    exit 1
}
log_info "✓ API is ready"

# Step 7: Run smoke tests
log_info "Step 7/8: Running smoke tests..."

# Test 1: Health endpoint
log_info "Test 1: Health check..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    log_info "✓ Health check passed"
else
    log_error "Health check failed: $HEALTH_RESPONSE"
    exit 1
fi

# Test 2: Metrics endpoint
log_info "Test 2: Metrics endpoint..."
METRICS_RESPONSE=$(curl -s http://localhost:8000/metrics)
if echo "$METRICS_RESPONSE" | grep -q 'comfyui_'; then
    log_info "✓ Metrics endpoint passed"
else
    log_error "Metrics endpoint failed"
    exit 1
fi

# Test 3: Create admin user (if auth enabled)
log_info "Test 3: Admin endpoints..."
ADMIN_USER_RESPONSE=$(curl -s -X POST http://localhost:8000/admin/users \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","role":"internal"}' 2>/dev/null || echo '{"error":"auth_disabled"}')

if echo "$ADMIN_USER_RESPONSE" | grep -q '"user_id"'; then
    USER_ID=$(echo "$ADMIN_USER_RESPONSE" | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
    log_info "✓ Admin user created: $USER_ID"

    # Create API key
    API_KEY_RESPONSE=$(curl -s -X POST http://localhost:8000/admin/api-keys \
        -H "Content-Type: application/json" \
        -d "{\"user_id\":\"$USER_ID\",\"name\":\"Deployment Test Key\"}")

    if echo "$API_KEY_RESPONSE" | grep -q '"api_key"'; then
        API_KEY=$(echo "$API_KEY_RESPONSE" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
        log_info "✓ API key created: ${API_KEY:0:20}..."

        # Save API key for validation script
        echo "$API_KEY" > "$PROJECT_ROOT/.api_key_test"
        chmod 600 "$PROJECT_ROOT/.api_key_test"
    else
        log_warn "API key creation skipped (auth may be disabled)"
    fi
elif echo "$ADMIN_USER_RESPONSE" | grep -q 'auth_disabled'; then
    log_warn "Authentication disabled, skipping admin tests"
else
    log_warn "Admin user creation failed (may be expected if auth disabled)"
fi

# Step 8: Display deployment status
log_info "Step 8/8: Deployment summary..."
echo ""
echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
echo ""
docker-compose ps
echo ""
log_info "Service URLs:"
echo "  - API:         http://localhost:8000"
echo "  - API Docs:    http://localhost:8000/docs"
echo "  - Health:      http://localhost:8000/health"
echo "  - Metrics:     http://localhost:8000/metrics"
echo "  - MinIO UI:    http://localhost:9001 (admin/minioadmin)"
echo ""
log_info "Next steps:"
echo "  1. Run full validation: ./scripts/validate.sh"
echo "  2. View logs: docker-compose logs -f api worker"
echo "  3. Run integration tests: poetry run pytest tests/integration/ -v"
echo ""
log_info "To stop services: docker-compose down"
log_info "To view logs: docker-compose logs -f [service]"
echo ""
