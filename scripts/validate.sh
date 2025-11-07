#!/bin/bash
set -e

# Post-Deployment Validation Script
# Validates that all services are working correctly after deployment
# Usage: ./scripts/validate.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
SKIPPED=0

echo "=================================================="
echo "ComfyUI API Service - Post-Deployment Validation"
echo "=================================================="
echo ""

# Logging functions
log_pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    ((FAILED++))
}

log_skip() {
    echo -e "${YELLOW}⊘ SKIP${NC} $1"
    ((SKIPPED++))
}

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

# Load API key if exists
API_KEY=""
if [ -f "$PROJECT_ROOT/.api_key_test" ]; then
    API_KEY=$(cat "$PROJECT_ROOT/.api_key_test")
fi

# ==================================================
# Infrastructure Tests
# ==================================================

echo "=== Infrastructure Tests ==="
echo ""

# Test 1: Docker containers running
log_test "1.1: Docker containers are running"
RUNNING_CONTAINERS=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)
if [ "$RUNNING_CONTAINERS" -ge 3 ]; then
    log_pass "Found $RUNNING_CONTAINERS running containers"
else
    log_fail "Only $RUNNING_CONTAINERS containers running (expected ≥3)"
fi

# Test 2: Redis connectivity
log_test "1.2: Redis connectivity"
if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    log_pass "Redis responding to ping"
else
    log_fail "Redis not responding"
fi

# Test 3: MinIO connectivity
log_test "1.3: MinIO connectivity"
if docker-compose exec -T minio mc alias set myminio http://localhost:9000 minioadmin minioadmin 2>/dev/null; then
    log_pass "MinIO accessible"
else
    log_fail "MinIO not accessible"
fi

# Test 4: MinIO bucket exists
log_test "1.4: MinIO bucket exists"
if docker-compose exec -T minio mc ls myminio/comfyui-artifacts 2>/dev/null >/dev/null; then
    log_pass "Bucket comfyui-artifacts exists"
else
    log_fail "Bucket comfyui-artifacts not found"
fi

echo ""

# ==================================================
# API Health Tests
# ==================================================

echo "=== API Health Tests ==="
echo ""

# Test 5: API health endpoint
log_test "2.1: API /health endpoint"
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health 2>/dev/null || echo "{}")
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    log_pass "API health check passed"
else
    log_fail "API health check failed: $HEALTH_RESPONSE"
fi

# Test 6: API ping endpoint
log_test "2.2: API /ping endpoint"
PING_RESPONSE=$(curl -s http://localhost:8000/ping 2>/dev/null || echo "{}")
if echo "$PING_RESPONSE" | grep -q '"ok":true'; then
    log_pass "API ping passed"
else
    log_fail "API ping failed: $PING_RESPONSE"
fi

# Test 7: Metrics endpoint
log_test "2.3: Prometheus metrics endpoint"
METRICS_RESPONSE=$(curl -s http://localhost:8000/metrics 2>/dev/null || echo "")
if echo "$METRICS_RESPONSE" | grep -q "comfyui_"; then
    METRIC_COUNT=$(echo "$METRICS_RESPONSE" | grep -c "^comfyui_")
    log_pass "Metrics endpoint working ($METRIC_COUNT metrics found)"
else
    log_fail "Metrics endpoint not working"
fi

# Test 8: API docs accessible
log_test "2.4: API documentation (/docs)"
DOCS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null || echo "000")
if [ "$DOCS_RESPONSE" = "200" ]; then
    log_pass "API docs accessible"
else
    log_fail "API docs returned HTTP $DOCS_RESPONSE"
fi

echo ""

# ==================================================
# Authentication Tests (if enabled)
# ==================================================

echo "=== Authentication Tests ==="
echo ""

if [ -n "$API_KEY" ]; then
    # Test 9: API key validation
    log_test "3.1: API key authentication"
    AUTH_RESPONSE=$(curl -s -H "Authorization: Bearer $API_KEY" http://localhost:8000/health 2>/dev/null || echo "{}")
    if echo "$AUTH_RESPONSE" | grep -q '"status":"healthy"'; then
        log_pass "API key authentication working"
    else
        log_fail "API key authentication failed"
    fi

    # Test 10: Rate limit headers
    log_test "3.2: Rate limit headers present"
    HEADERS=$(curl -s -I -H "Authorization: Bearer $API_KEY" http://localhost:8000/health 2>/dev/null || echo "")
    if echo "$HEADERS" | grep -qi "x-ratelimit-limit"; then
        LIMIT=$(echo "$HEADERS" | grep -i "x-ratelimit-limit" | cut -d' ' -f2 | tr -d '\r')
        REMAINING=$(echo "$HEADERS" | grep -i "x-ratelimit-remaining" | cut -d' ' -f2 | tr -d '\r')
        log_pass "Rate limit headers present (limit=$LIMIT, remaining=$REMAINING)"
    else
        log_skip "Rate limit headers not present (may be disabled)"
    fi

    # Test 11: Invalid API key rejected
    log_test "3.3: Invalid API key rejected"
    INVALID_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer invalid_key_12345" http://localhost:8000/api/v1/jobs 2>/dev/null || echo "000")
    if [ "$INVALID_RESPONSE" = "401" ]; then
        log_pass "Invalid API key correctly rejected (401)"
    else
        log_fail "Invalid API key returned HTTP $INVALID_RESPONSE (expected 401)"
    fi
else
    log_skip "3.1-3.3: Authentication tests (no API key available, auth may be disabled)"
    ((SKIPPED+=3))
fi

echo ""

# ==================================================
# Job Submission Tests
# ==================================================

echo "=== Job Submission Tests ==="
echo ""

# Test 12: Job submission (without auth)
log_test "4.1: Job submission endpoint"
JOB_PAYLOAD='{"prompt":"Test deployment","model":"dreamshaper_8.safetensors","width":512,"height":512}'
if [ -n "$API_KEY" ]; then
    JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -d "$JOB_PAYLOAD" 2>/dev/null || echo "{}")
else
    JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
        -H "Content-Type: application/json" \
        -d "$JOB_PAYLOAD" 2>/dev/null || echo "{}")
fi

if echo "$JOB_RESPONSE" | grep -q '"job_id"'; then
    JOB_ID=$(echo "$JOB_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
    log_pass "Job submitted successfully: $JOB_ID"

    # Test 13: Job status polling
    log_test "4.2: Job status endpoint"
    sleep 1
    if [ -n "$API_KEY" ]; then
        STATUS_RESPONSE=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID \
            -H "Authorization: Bearer $API_KEY" 2>/dev/null || echo "{}")
    else
        STATUS_RESPONSE=$(curl -s http://localhost:8000/api/v1/jobs/$JOB_ID 2>/dev/null || echo "{}")
    fi

    if echo "$STATUS_RESPONSE" | grep -q '"job_id"'; then
        JOB_STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        log_pass "Job status retrieved: $JOB_STATUS"

        # Test 14: Job cancellation
        log_test "4.3: Job cancellation"
        if [ "$JOB_STATUS" = "queued" ] || [ "$JOB_STATUS" = "running" ]; then
            if [ -n "$API_KEY" ]; then
                CANCEL_RESPONSE=$(curl -s -X DELETE http://localhost:8000/api/v1/jobs/$JOB_ID \
                    -H "Authorization: Bearer $API_KEY" 2>/dev/null || echo "{}")
            else
                CANCEL_RESPONSE=$(curl -s -X DELETE http://localhost:8000/api/v1/jobs/$JOB_ID 2>/dev/null || echo "{}")
            fi

            if echo "$CANCEL_RESPONSE" | grep -q '"status"'; then
                log_pass "Job cancellation requested"
            else
                log_fail "Job cancellation failed: $CANCEL_RESPONSE"
            fi
        else
            log_skip "Job already completed, cannot test cancellation"
        fi
    else
        log_fail "Job status retrieval failed: $STATUS_RESPONSE"
        log_skip "Job cancellation test (dependent on status)"
        ((SKIPPED++))
    fi
else
    log_fail "Job submission failed: $JOB_RESPONSE"
    log_skip "Job status test (dependent on submission)"
    log_skip "Job cancellation test (dependent on submission)"
    ((SKIPPED+=2))
fi

echo ""

# ==================================================
# Idempotency Tests
# ==================================================

echo "=== Idempotency Tests ==="
echo ""

# Test 15: Idempotency key
log_test "5.1: Idempotency prevents duplicate execution"
IDEMPOTENCY_KEY="validation-test-$(date +%s)"
IDEMPOTENT_PAYLOAD='{"prompt":"Idempotency test","model":"dreamshaper_8.safetensors","width":512,"height":512}'

if [ -n "$API_KEY" ]; then
    IDEMPOTENT_RESPONSE_1=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
        -H "Authorization: Bearer $API_KEY" \
        -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
        -H "Content-Type: application/json" \
        -d "$IDEMPOTENT_PAYLOAD" 2>/dev/null || echo "{}")
else
    IDEMPOTENT_RESPONSE_1=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
        -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
        -H "Content-Type: application/json" \
        -d "$IDEMPOTENT_PAYLOAD" 2>/dev/null || echo "{}")
fi

if echo "$IDEMPOTENT_RESPONSE_1" | grep -q '"job_id"'; then
    JOB_ID_1=$(echo "$IDEMPOTENT_RESPONSE_1" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

    # Submit same request again
    sleep 0.5
    if [ -n "$API_KEY" ]; then
        IDEMPOTENT_RESPONSE_2=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
            -H "Authorization: Bearer $API_KEY" \
            -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
            -H "Content-Type: application/json" \
            -d "$IDEMPOTENT_PAYLOAD" 2>/dev/null || echo "{}")
    else
        IDEMPOTENT_RESPONSE_2=$(curl -s -X POST http://localhost:8000/api/v1/jobs \
            -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
            -H "Content-Type: application/json" \
            -d "$IDEMPOTENT_PAYLOAD" 2>/dev/null || echo "{}")
    fi

    JOB_ID_2=$(echo "$IDEMPOTENT_RESPONSE_2" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)

    if [ "$JOB_ID_1" = "$JOB_ID_2" ]; then
        log_pass "Idempotency working: same job_id returned ($JOB_ID_1)"
    else
        log_fail "Idempotency failed: different job_ids ($JOB_ID_1 vs $JOB_ID_2)"
    fi
else
    log_fail "Idempotency test failed: could not submit job"
fi

echo ""

# ==================================================
# Worker Tests
# ==================================================

echo "=== Worker Tests ==="
echo ""

# Test 16: Worker logs
log_test "6.1: Worker is running"
WORKER_LOGS=$(docker-compose logs --tail=20 worker 2>/dev/null || echo "")
if echo "$WORKER_LOGS" | grep -q "Started ARQ worker"; then
    log_pass "Worker started successfully"
elif echo "$WORKER_LOGS" | grep -q "worker"; then
    log_pass "Worker container running"
else
    log_fail "Worker not detected in logs"
fi

# Test 17: Worker crash recovery
log_test "6.2: Crash recovery ran on startup"
if echo "$WORKER_LOGS" | grep -q "Crash recovery:"; then
    RECOVERED=$(echo "$WORKER_LOGS" | grep "Crash recovery:" | tail -1)
    log_pass "Crash recovery executed: $RECOVERED"
else
    log_skip "Crash recovery not found in logs (may not have crashed jobs)"
fi

echo ""

# ==================================================
# ComfyUI Backend Tests (if available)
# ==================================================

echo "=== ComfyUI Backend Tests ==="
echo ""

# Test 18: ComfyUI connectivity
log_test "7.1: ComfyUI backend connectivity"
COMFYUI_RESPONSE=$(curl -s http://localhost:8188/system_stats 2>/dev/null || echo "")
if [ -n "$COMFYUI_RESPONSE" ]; then
    log_pass "ComfyUI backend accessible"

    # Test 19: ComfyUI queue endpoint
    log_test "7.2: ComfyUI queue endpoint"
    QUEUE_RESPONSE=$(curl -s http://localhost:8188/queue 2>/dev/null || echo "")
    if [ -n "$QUEUE_RESPONSE" ]; then
        log_pass "ComfyUI queue endpoint working"
    else
        log_fail "ComfyUI queue endpoint not responding"
    fi
else
    log_skip "7.1-7.2: ComfyUI not available (expected in dev environment)"
    ((SKIPPED+=2))
fi

echo ""

# ==================================================
# Summary
# ==================================================

echo "=================================================="
echo "Validation Summary"
echo "=================================================="
echo ""
echo -e "${GREEN}Passed:${NC}  $PASSED"
echo -e "${RED}Failed:${NC}  $FAILED"
echo -e "${YELLOW}Skipped:${NC} $SKIPPED"
echo ""

TOTAL=$((PASSED + FAILED))
if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$((PASSED * 100 / TOTAL))
    echo "Success Rate: $SUCCESS_RATE% ($PASSED/$TOTAL)"
    echo ""
fi

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Your deployment is ready for production use."
    echo ""
    echo "Next steps:"
    echo "  1. Run integration tests: poetry run pytest tests/integration/ -v"
    echo "  2. Monitor metrics: http://localhost:8000/metrics"
    echo "  3. Review logs: docker-compose logs -f api worker"
    echo "  4. See DEPLOYMENT_CHECKLIST.md for post-deployment tasks"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Please review the failures above and check:"
    echo "  - docker-compose ps"
    echo "  - docker-compose logs api"
    echo "  - docker-compose logs worker"
    echo ""
    exit 1
fi
