#!/bin/bash
# ComfyUI API Service - API Key Generator
# Usage: ./create-api-key.sh [username] [tier]

set -e

USERNAME=${1:-"user"}
TIER=${2:-"PRO"}

echo "============================================================"
echo "              Generating API Key"
echo "============================================================"
echo ""
echo "Username: $USERNAME"
echo "Tier:     $TIER"
echo ""

# Generate API key
API_KEY=$(docker exec comfyui-api python3 -c "
from apps.api.models.auth import APIKey
from apps.api.middleware.auth import hash_api_key
import secrets

# Generate key
key = f'prod_{secrets.token_urlsafe(32)}'
print(key)
" 2>/dev/null)

if [ -z "$API_KEY" ]; then
    echo "Error: Failed to generate API key"
    echo ""
    echo "Make sure the API container is running:"
    echo "  docker compose ps api"
    exit 1
fi

echo "============================================================"
echo "                  API KEY GENERATED"
echo "============================================================"
echo ""
echo "$API_KEY"
echo ""
echo "============================================================"
echo ""
echo "IMPORTANT: Save this key securely! You won't be able to see it again."
echo ""
echo "Test your API key:"
echo "  curl -H \"X-API-Key: $API_KEY\" https://your-domain.com/api/v1/monitoring/stats"
echo ""
echo "Or use the Python SDK:"
echo "  from comfyui_client import ComfyUIClient"
echo "  client = ComfyUIClient('https://your-domain.com', api_key='$API_KEY')"
echo ""
