#!/bin/bash
set -euo pipefail

# Deployment script for Rapid Minutes Export
# Usage: ./scripts/deploy.sh [environment] [version]

ENVIRONMENT=${1:-production}
VERSION=${2:-latest}
NAMESPACE="rapid-minutes"

echo "🚀 Starting deployment of Rapid Minutes Export"
echo "Environment: $ENVIRONMENT"
echo "Version: $VERSION"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

# Create namespace if it doesn't exist
print_status "Creating namespace '$NAMESPACE' if it doesn't exist..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes manifests based on environment
case $ENVIRONMENT in
    production)
        print_status "Deploying to production environment..."

        # Apply ConfigMap and PVC first
        kubectl apply -f k8s/production/service.yaml -n "$NAMESPACE"

        # Wait for PVC to be bound
        print_status "Waiting for PVC to be bound..."
        kubectl wait --for=condition=Bound pvc/rapid-minutes-upload-pvc -n "$NAMESPACE" --timeout=60s

        # Update image tag in deployment
        sed "s|ghcr.io/yippine/rapid-minutes-export:latest|ghcr.io/yippine/rapid-minutes-export:$VERSION|g" k8s/production/deployment.yaml | kubectl apply -f - -n "$NAMESPACE"

        # Apply other resources
        kubectl apply -f k8s/production/ingress.yaml -n "$NAMESPACE"
        kubectl apply -f k8s/production/hpa.yaml -n "$NAMESPACE"
        kubectl apply -f k8s/production/monitoring.yaml -n "$NAMESPACE"
        ;;
    staging)
        print_status "Deploying to staging environment..."
        kubectl apply -f k8s/staging/ -n "$NAMESPACE"
        ;;
    *)
        print_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Wait for deployment to be ready
print_status "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=600s deployment/rapid-minutes-export -n "$NAMESPACE"

# Get deployment status
print_status "Deployment status:"
kubectl get deployment rapid-minutes-export -n "$NAMESPACE"
kubectl get pods -l app=rapid-minutes-export -n "$NAMESPACE"

# Check service endpoints
print_status "Service endpoints:"
kubectl get endpoints rapid-minutes-export-service -n "$NAMESPACE"

# Get ingress information
if kubectl get ingress rapid-minutes-export-ingress -n "$NAMESPACE" &> /dev/null; then
    print_status "Ingress information:"
    kubectl get ingress rapid-minutes-export-ingress -n "$NAMESPACE"
fi

# Run health check
print_status "Running health check..."
if kubectl run health-check --image=curlimages/curl --rm -i --restart=Never -- curl -f http://rapid-minutes-export-service/health -n "$NAMESPACE"; then
    print_status "✅ Health check passed!"
else
    print_error "❌ Health check failed!"
    exit 1
fi

print_status "🎉 Deployment completed successfully!"
print_status "You can check the logs with: kubectl logs -l app=rapid-minutes-export -n $NAMESPACE --follow"