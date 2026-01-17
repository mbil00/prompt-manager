#!/bin/bash
# Test script for Prompt Manager container
# Usage: ./scripts/test-container.sh [API_KEY]

set -e

API_KEY="${1:-test-key-12345}"
BASE_URL="http://localhost:8000"
CONTAINER_NAME="pm-test"
IMAGE_NAME="prompt-manager:test"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cleanup() {
    log_info "Cleaning up..."
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
}

# Cleanup on exit
trap cleanup EXIT

log_info "Building container image..."
docker build -t "$IMAGE_NAME" .

log_info "Starting container..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -p 8000:8000 \
    -e PM_API_KEY="$API_KEY" \
    -e PM_ALLOW_LOCALHOST_BYPASS=false \
    "$IMAGE_NAME"

log_info "Waiting for container to be ready..."
for i in {1..30}; do
    if curl -s "$BASE_URL/health" > /dev/null 2>&1; then
        break
    fi
    if [ $i -eq 30 ]; then
        log_error "Container failed to start"
        docker logs "$CONTAINER_NAME"
        exit 1
    fi
    sleep 1
done

log_info "Running tests..."

# Test 1: Health endpoint
log_info "Test 1: Health endpoint..."
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    log_info "  PASS: Health endpoint returns healthy"
else
    log_error "  FAIL: Health endpoint returned: $HEALTH"
    exit 1
fi

# Test 2: Root endpoint
log_info "Test 2: Root endpoint..."
ROOT=$(curl -s "$BASE_URL/")
if echo "$ROOT" | grep -q '"name":"Prompt Manager API"'; then
    log_info "  PASS: Root endpoint returns API info"
else
    log_error "  FAIL: Root endpoint returned: $ROOT"
    exit 1
fi

# Test 3: Auth required for API endpoints
log_info "Test 3: Authentication required..."
AUTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/prompts")
if [ "$AUTH_RESPONSE" = "401" ]; then
    log_info "  PASS: API returns 401 without auth"
else
    log_error "  FAIL: Expected 401, got $AUTH_RESPONSE"
    exit 1
fi

# Test 4: Auth works with correct key
log_info "Test 4: Authentication with API key..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/prompts")
if [ "$API_RESPONSE" = "200" ]; then
    log_info "  PASS: API returns 200 with valid key"
else
    log_error "  FAIL: Expected 200, got $API_RESPONSE"
    exit 1
fi

# Test 5: Wrong key rejected
log_info "Test 5: Invalid key rejected..."
WRONG_KEY_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: wrong-key" "$BASE_URL/api/v1/prompts")
if [ "$WRONG_KEY_RESPONSE" = "401" ]; then
    log_info "  PASS: API rejects invalid key"
else
    log_error "  FAIL: Expected 401, got $WRONG_KEY_RESPONSE"
    exit 1
fi

# Test 6: Create a prompt
log_info "Test 6: Create prompt..."
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/prompts" \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"slug": "test-prompt", "title": "Test Prompt", "content": "Hello {{name}}"}')
if echo "$CREATE_RESPONSE" | grep -q '"slug":"test-prompt"'; then
    log_info "  PASS: Created prompt successfully"
else
    log_error "  FAIL: Create returned: $CREATE_RESPONSE"
    exit 1
fi

# Test 7: Get prompt
log_info "Test 7: Get prompt..."
GET_RESPONSE=$(curl -s -H "X-API-Key: $API_KEY" "$BASE_URL/api/v1/prompts/test-prompt")
if echo "$GET_RESPONSE" | grep -q '"title":"Test Prompt"'; then
    log_info "  PASS: Retrieved prompt successfully"
else
    log_error "  FAIL: Get returned: $GET_RESPONSE"
    exit 1
fi

# Test 8: Delete prompt
log_info "Test 8: Delete prompt..."
DELETE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    -H "X-API-Key: $API_KEY" \
    "$BASE_URL/api/v1/prompts/test-prompt")
if [ "$DELETE_RESPONSE" = "204" ]; then
    log_info "  PASS: Deleted prompt successfully"
else
    log_error "  FAIL: Delete returned: $DELETE_RESPONSE"
    exit 1
fi

echo ""
log_info "All tests passed!"
echo ""
log_info "Container logs:"
docker logs "$CONTAINER_NAME" 2>&1 | tail -20
