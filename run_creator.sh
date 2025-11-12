#!/bin/bash
#
# Run Creator development server
#
# This script starts the Creator FastAPI application with hot reloading
# for development.
#
# Usage:
#   ./run_creator.sh
#

set -e

# Load environment variables
if [ -f .env ]; then
    echo "Loading environment from .env..."
    set -a
    source .env
    set +a
fi

# Set defaults if not provided
export ENVIRONMENT=${ENVIRONMENT:-development}
export DATABASE_URL=${DATABASE_URL:-sqlite:///./creator.db}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
export SECRET_KEY=${SECRET_KEY:-dev-secret-key-change-in-production}
export ENCRYPTION_KEY=${ENCRYPTION_KEY:-dev-encryption-key-change-in-production}

# Google OAuth (replace with your credentials)
export GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-your-client-id.apps.googleusercontent.com}
export GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-your-client-secret}
export GOOGLE_REDIRECT_URI=${GOOGLE_REDIRECT_URI:-http://localhost:8001/auth/google/callback}

# Stripe (replace with your credentials)
export STRIPE_PUBLIC_KEY=${STRIPE_PUBLIC_KEY:-pk_test_...}
export STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY:-sk_test_...}
export STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET:-whsec_...}

# ComfyUI URL
export COMFYUI_URL=${COMFYUI_URL:-http://localhost:8188}

# Frontend URL
export FRONTEND_URL=${FRONTEND_URL:-http://localhost:8001}

echo "======================================"
echo "🚀 Starting Creator Development Server"
echo "======================================"
echo ""
echo "Environment: $ENVIRONMENT"
echo "Frontend URL: $FRONTEND_URL"
echo "Database: $DATABASE_URL"
echo "Redis: $REDIS_URL"
echo "ComfyUI: $COMFYUI_URL"
echo ""
echo "📖 API Docs: http://localhost:8001/docs"
echo "🎨 Web UI: http://localhost:8001/login"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run with uvicorn and hot reload
uvicorn apps.creator.main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --reload \
    --reload-dir apps/creator \
    --reload-dir apps/shared \
    --reload-dir apps/web \
    --reload-dir config \
    --log-level info
