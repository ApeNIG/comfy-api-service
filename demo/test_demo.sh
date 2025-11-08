#!/bin/bash
# Quick demo test script
# This runs the demo inside the Docker container to avoid networking issues

echo "============================================================"
echo "              Testing ComfyUI Image Generator Demo"
echo "============================================================"
echo ""

# Copy demo script into container
echo "1. Preparing demo environment..."
docker cp demo/image_generator.py comfyui-api:/tmp/image_generator.py

# Install SDK in container
echo "2. Installing SDK in container..."
docker exec comfyui-api pip install -q /app/sdk/python

# Test 1: Show stats
echo ""
echo "============================================================"
echo "Test 1: Viewing Usage Statistics"
echo "============================================================"
docker exec comfyui-api python3 /tmp/image_generator.py \
  --url http://localhost:8000 \
  --stats

# Test 2: Estimate cost
echo ""
echo "============================================================"
echo "Test 2: Estimating Cost"
echo "============================================================"
docker exec comfyui-api python3 -c "
from comfyui_client import ComfyUIClient

client = ComfyUIClient('http://localhost:8000')
cost = client.estimate_cost(512, 512, 20, 1)

print('GPU Type:        ', cost['gpu_type'])
print('Hourly Rate:     $', cost['hourly_rate'], '/hour', sep='')
print('Est. Time:       ', cost['estimated_time_seconds'], 's', sep='')
print('Cost per Image:  $', format(cost['cost_per_image'], '.6f'), sep='')
print('Total Cost:      $', format(cost['estimated_cost_usd'], '.6f'), sep='')
"

# Test 3: Project monthly costs
echo ""
echo "============================================================"
echo "Test 3: Monthly Cost Projection"
echo "============================================================"
docker exec comfyui-api python3 /tmp/image_generator.py \
  --url http://localhost:8000 \
  --project 100

echo ""
echo "============================================================"
echo "                    Demo Tests Complete!"
echo "============================================================"
echo ""
echo "The demo is working! Here's how to use it:"
echo ""
echo "From inside the API container:"
echo "  docker exec -it comfyui-api bash"
echo "  python /tmp/image_generator.py"
echo ""
echo "Or use the SDK directly in Python:"
echo "  docker exec comfyui-api python3 -c \"from comfyui_client import ComfyUIClient; print('SDK works!')\""
echo ""
