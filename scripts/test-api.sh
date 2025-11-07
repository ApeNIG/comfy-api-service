#!/bin/bash

# Quick API Test Script
# Tests the running API endpoints

BASE_URL=${1:-http://localhost:8000}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "=================================================="
echo "Testing ComfyUI API Service"
echo "Base URL: $BASE_URL"
echo "=================================================="
echo ""

# Test 1: Health endpoint
echo -e "${BLUE}Test 1: Health Check${NC}"
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✓ PASS${NC} - Health check successful"
    echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
else
    echo -e "${RED}✗ FAIL${NC} - Health check failed"
    echo "$HEALTH"
fi
echo ""

# Test 2: Ping endpoint
echo -e "${BLUE}Test 2: Ping${NC}"
PING=$(curl -s "$BASE_URL/ping")
if echo "$PING" | grep -q '"ok":true'; then
    echo -e "${GREEN}✓ PASS${NC} - Ping successful"
    echo "$PING" | python3 -m json.tool 2>/dev/null || echo "$PING"
else
    echo -e "${RED}✗ FAIL${NC} - Ping failed"
    echo "$PING"
fi
echo ""

# Test 3: API docs
echo -e "${BLUE}Test 3: API Documentation${NC}"
DOCS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/docs")
if [ "$DOCS_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - API docs accessible at $BASE_URL/docs"
else
    echo -e "${RED}✗ FAIL${NC} - API docs returned HTTP $DOCS_STATUS"
fi
echo ""

# Test 4: Metrics endpoint
echo -e "${BLUE}Test 4: Prometheus Metrics${NC}"
METRICS=$(curl -s "$BASE_URL/metrics")
if echo "$METRICS" | grep -q "comfyui_"; then
    METRIC_COUNT=$(echo "$METRICS" | grep -c "^comfyui_")
    echo -e "${GREEN}✓ PASS${NC} - Metrics endpoint working ($METRIC_COUNT metrics)"
    echo ""
    echo "Sample metrics:"
    echo "$METRICS" | grep "^comfyui_" | head -5
else
    echo -e "${RED}✗ FAIL${NC} - Metrics endpoint not working"
fi
echo ""

# Test 5: Admin endpoints (if auth disabled)
echo -e "${BLUE}Test 5: Admin User Creation${NC}"
USER_RESPONSE=$(curl -s -X POST "$BASE_URL/admin/users" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","role":"internal"}' 2>/dev/null || echo '{"error":"failed"}')

if echo "$USER_RESPONSE" | grep -q '"user_id"'; then
    USER_ID=$(echo "$USER_RESPONSE" | grep -o '"user_id":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✓ PASS${NC} - Admin user created: $USER_ID"
    echo "$USER_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$USER_RESPONSE"

    # Test 6: API key creation
    echo ""
    echo -e "${BLUE}Test 6: API Key Creation${NC}"
    KEY_RESPONSE=$(curl -s -X POST "$BASE_URL/admin/api-keys" \
        -H "Content-Type: application/json" \
        -d "{\"user_id\":\"$USER_ID\",\"name\":\"Test Key\"}" 2>/dev/null || echo '{"error":"failed"}')

    if echo "$KEY_RESPONSE" | grep -q '"api_key"'; then
        API_KEY=$(echo "$KEY_RESPONSE" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)
        echo -e "${GREEN}✓ PASS${NC} - API key created: ${API_KEY:0:30}..."
        echo "$KEY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$KEY_RESPONSE"

        # Save API key for later use
        echo "$API_KEY" > /tmp/comfyui_test_api_key
        echo ""
        echo -e "${BLUE}API Key saved to: /tmp/comfyui_test_api_key${NC}"
    else
        echo -e "${RED}✗ FAIL${NC} - API key creation failed"
        echo "$KEY_RESPONSE"
    fi
else
    echo -e "${RED}⊘ SKIP${NC} - Admin endpoints not available (auth may be disabled)"
fi

echo ""
echo "=================================================="
echo "Testing Complete"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  - View API docs: open $BASE_URL/docs"
echo "  - View metrics: curl $BASE_URL/metrics"
echo "  - Submit a job: curl -X POST $BASE_URL/api/v1/jobs -H 'Content-Type: application/json' -d '{\"prompt\":\"test\"}'"
echo ""
