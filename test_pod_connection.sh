#!/bin/bash
# Quick test script for RunPod connection

echo "🔍 Testing RunPod Pod Connection..."
echo ""

# Test 1: Health check
echo "1️⃣ Checking API health..."
curl -s http://localhost:8000/health | jq '.'
echo ""

# Test 2: Submit a quick test job
echo "2️⃣ Submitting test image generation job..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful sunset",
    "width": 512,
    "height": 512,
    "steps": 10,
    "model": "v1-5-pruned-emaonly.ckpt"
  }')

echo "$RESPONSE" | jq '.'
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')

echo ""
echo "3️⃣ Job ID: $JOB_ID"
echo ""
echo "4️⃣ Monitoring job (will check every 2 seconds)..."
echo ""

# Poll job status
for i in {1..30}; do
  STATUS=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID | jq -r '.status')
  echo "   Status: $STATUS"

  if [ "$STATUS" = "succeeded" ]; then
    echo ""
    echo "✅ SUCCESS! Image generated in ~$((i*2)) seconds"
    curl -s http://localhost:8000/api/v1/jobs/$JOB_ID | jq '.result'
    break
  elif [ "$STATUS" = "failed" ]; then
    echo ""
    echo "❌ FAILED"
    curl -s http://localhost:8000/api/v1/jobs/$JOB_ID | jq '.'
    break
  fi

  sleep 2
done

echo ""
echo "✨ Done!"
