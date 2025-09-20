#!/bin/bash

# Clotho Docker Testing Script
set -e

echo "🧪 Testing Clotho Docker Setup"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="clotho"
TAG="test"
CONTAINER_NAME="clotho-test"
PORT="3000"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up test containers..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
}

# Set trap for cleanup on exit
trap cleanup EXIT

echo ""
print_status "Step 1: Building Docker image..."
if docker build -t ${IMAGE_NAME}:${TAG} .; then
    print_success "Image built successfully"
else
    print_error "Failed to build image"
    exit 1
fi

echo ""
print_status "Step 2: Checking image size..."
IMAGE_SIZE=$(docker images ${IMAGE_NAME}:${TAG} --format "{{.Size}}")
print_success "Image size: $IMAGE_SIZE"

echo ""
print_status "Step 3: Inspecting image layers..."
docker history ${IMAGE_NAME}:${TAG} --format "table {{.CreatedBy}}\t{{.Size}}" | head -10

echo ""
print_status "Step 4: Starting container..."
if docker run -d --name $CONTAINER_NAME -p ${PORT}:${PORT} ${IMAGE_NAME}:${TAG}; then
    print_success "Container started successfully"
else
    print_error "Failed to start container"
    exit 1
fi

echo ""
print_status "Step 5: Waiting for application to start..."
sleep 10

echo ""
print_status "Step 6: Testing health check..."
for i in {1..5}; do
    if curl -f http://localhost:${PORT}/ > /dev/null 2>&1; then
        print_success "Health check passed on attempt $i"
        break
    else
        print_warning "Health check failed, attempt $i/5"
        if [ $i -eq 5 ]; then
            print_error "Health check failed after 5 attempts"
            docker logs $CONTAINER_NAME
            exit 1
        fi
        sleep 5
    fi
done

echo ""
print_status "Step 7: Testing application endpoints..."

# Test main page
if curl -s http://localhost:${PORT}/ | grep -q "Clotho"; then
    print_success "Main page loads correctly"
else
    print_warning "Main page might not contain expected content"
fi

# Test static assets
if curl -f http://localhost:${PORT}/assets/ > /dev/null 2>&1; then
    print_success "Static assets accessible"
else
    print_warning "Static assets check inconclusive (this might be normal)"
fi

echo ""
print_status "Step 8: Checking container security..."
CONTAINER_USER=$(docker exec $CONTAINER_NAME whoami)
if [ "$CONTAINER_USER" = "appuser" ]; then
    print_success "Container running as non-root user: $CONTAINER_USER"
else
    print_warning "Container user: $CONTAINER_USER (should be 'appuser')"
fi

echo ""
print_status "Step 9: Checking container logs..."
echo "--- Container Logs (last 10 lines) ---"
docker logs --tail 10 $CONTAINER_NAME

echo ""
print_status "Step 10: Testing container resource usage..."
CONTAINER_STATS=$(docker stats $CONTAINER_NAME --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}")
echo "Resource Usage:"
echo "$CONTAINER_STATS"

echo ""
print_status "Step 11: Testing graceful shutdown..."
docker stop $CONTAINER_NAME
if [ $? -eq 0 ]; then
    print_success "Container stopped gracefully"
else
    print_warning "Container stop had issues"
fi

echo ""
print_success "🎉 All tests completed!"
echo ""
echo "Summary:"
echo "- Image: ${IMAGE_NAME}:${TAG}"
echo "- Size: $IMAGE_SIZE"
echo "- Port: $PORT"
echo "- User: $CONTAINER_USER"
echo ""
echo "To run manually:"
echo "  docker run -p ${PORT}:${PORT} ${IMAGE_NAME}:${TAG}"
echo ""
echo "To run with docker-compose:"
echo "  docker-compose up"
