#!/bin/bash
set -euo pipefail

# Build and test script for Rapid Minutes Export
# Usage: ./scripts/build-and-test.sh [--push] [--tag TAG]

PUSH=false
TAG="latest"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --push)
            PUSH=true
            shift
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--push] [--tag TAG]"
            exit 1
            ;;
    esac
done

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "🔨 Building and testing Rapid Minutes Export"
print_status "Tag: $TAG"
print_status "Push to registry: $PUSH"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Set image name
IMAGE_NAME="ghcr.io/yippine/rapid-minutes-export"

# Build the Docker image
print_status "Building Docker image..."
docker build -t "$IMAGE_NAME:$TAG" .

# Tag as latest if this is not latest
if [[ "$TAG" != "latest" ]]; then
    docker tag "$IMAGE_NAME:$TAG" "$IMAGE_NAME:latest"
fi

# Run tests in Docker container
print_status "Running tests in Docker container..."
docker run --rm \
    -v "$(pwd):/app" \
    -w /app \
    --entrypoint="" \
    "$IMAGE_NAME:$TAG" \
    bash -c "
        pip install pytest pytest-cov pytest-asyncio && \
        pytest --cov=. --cov-report=term-missing --cov-report=html
    "

# Security scan with Trivy
if command -v trivy &> /dev/null; then
    print_status "Running security scan with Trivy..."
    trivy image "$IMAGE_NAME:$TAG"
else
    print_warning "Trivy not found, skipping security scan"
fi

# Test the built image
print_status "Testing Docker image functionality..."
CONTAINER_ID=$(docker run -d -p 8001:8000 "$IMAGE_NAME:$TAG")

# Wait for container to start
sleep 10

# Health check
if curl -f http://localhost:8001/health; then
    print_status "✅ Health check passed!"
else
    print_error "❌ Health check failed!"
    docker logs "$CONTAINER_ID"
    docker stop "$CONTAINER_ID"
    exit 1
fi

# Clean up test container
docker stop "$CONTAINER_ID"

# Push to registry if requested
if [[ "$PUSH" == true ]]; then
    print_status "Pushing image to registry..."
    docker push "$IMAGE_NAME:$TAG"
    if [[ "$TAG" != "latest" ]]; then
        docker push "$IMAGE_NAME:latest"
    fi
    print_status "✅ Image pushed to registry!"
fi

# Show image information
print_status "Image information:"
docker images "$IMAGE_NAME:$TAG"

print_status "🎉 Build and test completed successfully!"
print_status "Image: $IMAGE_NAME:$TAG"
print_status "Size: $(docker images --format 'table {{.Repository}}:{{.Tag}}\t{{.Size}}' | grep "$IMAGE_NAME:$TAG" | awk '{print $2}')"