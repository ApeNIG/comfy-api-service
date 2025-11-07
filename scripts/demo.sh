#!/bin/bash
set -e

# Demo Mode - Run ComfyUI API Service without external dependencies
# This script demonstrates the API in "mock mode" for local testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=================================================="
echo "ComfyUI API Service - Demo Mode"
echo "=================================================="
echo ""
echo -e "${YELLOW}Note: Running in demo mode without Redis/MinIO/ComfyUI${NC}"
echo "The API will work but jobs won't actually generate images."
echo ""

cd "$PROJECT_ROOT"

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}Poetry not found. Installing dependencies with pip...${NC}"
    pip install -e .
else
    echo -e "${GREEN}Installing dependencies with poetry...${NC}"
    poetry install --no-interaction --no-ansi
fi

echo ""
echo -e "${GREEN}Starting API server on http://localhost:8000${NC}"
echo ""
echo "Available endpoints:"
echo "  - Health:      http://localhost:8000/health"
echo "  - API Docs:    http://localhost:8000/docs"
echo "  - Metrics:     http://localhost:8000/metrics"
echo "  - Ping:        http://localhost:8000/ping"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "=================================================="
echo ""

# Set demo environment variables
export AUTH_ENABLED=false
export RATE_LIMIT_ENABLED=false
export JOBS_ENABLED=false
export REDIS_URL=redis://localhost:6379
export MINIO_ENDPOINT=localhost:9000
export COMFYUI_URL=http://localhost:8188

# Start the API server
if command -v poetry &> /dev/null; then
    poetry run uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
else
    python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
fi
