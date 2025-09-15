# 🚀 Deployment Guide - Rapid Minutes Export

This document provides comprehensive deployment instructions for the Rapid Minutes Export application using Docker and Kubernetes.

## 📋 Prerequisites

### Required Software
- Docker 20.10+
- Docker Compose 2.0+
- Kubernetes 1.24+ (for production)
- kubectl configured with cluster access
- Git

### System Requirements
- **Development**: 2 CPU cores, 4GB RAM
- **Production**: 4+ CPU cores, 8GB+ RAM, 20GB+ storage

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │      Nginx      │    │   FastAPI App   │
│    (Ingress)    │───▶│   (Reverse      │───▶│  (3 replicas)   │
│                 │    │     Proxy)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┐            │
                       │   Persistent    │◀───────────┘
                       │    Storage      │
                       │   (Uploads)     │
                       └─────────────────┘
```

## 🐳 Docker Deployment

### Local Development

1. **Clone and Setup**:
```bash
git clone <repository-url>
cd rapid-minutes-export
```

2. **Development with Hot Reload**:
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Access application
open http://localhost:8000
```

3. **Production-like Local Environment**:
```bash
# Build and start production containers
docker-compose up -d

# View logs
docker-compose logs -f rapid-minutes

# Access application
open http://localhost
```

### Building Custom Images

Use the provided build script:
```bash
# Build and test locally
./scripts/build-and-test.sh --tag v1.0.0

# Build and push to registry
./scripts/build-and-test.sh --tag v1.0.0 --push
```

## ☸️ Kubernetes Deployment

### Prerequisites Setup

1. **Create Namespace**:
```bash
kubectl create namespace rapid-minutes
```

2. **Configure Secrets** (if needed):
```bash
# Example: Docker registry credentials
kubectl create secret docker-registry regcred \
  --docker-server=ghcr.io \
  --docker-username=<username> \
  --docker-password=<token> \
  --namespace=rapid-minutes
```

### Production Deployment

1. **Deploy Application**:
```bash
# Using deployment script
./scripts/deploy.sh production v1.0.0

# Or manual deployment
kubectl apply -f k8s/production/ -n rapid-minutes
```

2. **Verify Deployment**:
```bash
# Check pods
kubectl get pods -n rapid-minutes

# Check services
kubectl get svc -n rapid-minutes

# Check ingress
kubectl get ingress -n rapid-minutes

# View logs
kubectl logs -l app=rapid-minutes-export -n rapid-minutes --follow
```

3. **Scaling**:
```bash
# Manual scaling
kubectl scale deployment rapid-minutes-export --replicas=5 -n rapid-minutes

# Auto-scaling is configured via HPA (3-10 replicas based on CPU/Memory)
kubectl get hpa -n rapid-minutes
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Runtime environment | `production` | Yes |
| `MAX_FILE_SIZE` | Maximum upload size (bytes) | `10485760` | No |
| `MAX_CONCURRENT_PROCESSES` | Max concurrent AI processes | `3` | No |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | No |
| `UPLOAD_TIMEOUT` | Upload timeout (seconds) | `60` | No |
| `PROCESSING_TIMEOUT` | AI processing timeout (seconds) | `300` | No |

### Kubernetes Configuration

Update values in `k8s/production/service.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rapid-minutes-config
data:
  cors_origins: "https://yourapp.com"
  max_file_size: "10485760"
  # ... other config values
```

### Ingress Configuration

Update hostnames in `k8s/production/ingress.yaml`:
```yaml
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: rapid-minutes-tls
  rules:
  - host: your-domain.com
    # ... rest of configuration
```

## 📊 Monitoring & Observability

### Health Checks

The application provides health endpoints:
- `GET /health` - Application health status
- `GET /metrics` - Prometheus metrics (if enabled)

### Prometheus Monitoring

Metrics are automatically collected when deployed with the provided manifests:
```bash
# View available metrics
kubectl get servicemonitor -n rapid-minutes

# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open http://localhost:9090/targets
```

### Logging

View application logs:
```bash
# Real-time logs
kubectl logs -l app=rapid-minutes-export -n rapid-minutes --follow

# Logs from specific pod
kubectl logs rapid-minutes-export-<pod-id> -n rapid-minutes

# Previous container logs (if crashed)
kubectl logs rapid-minutes-export-<pod-id> -n rapid-minutes --previous
```

## 🛡️ Security Considerations

### Container Security
- Runs as non-root user (UID 1000)
- Read-only filesystem where possible
- Resource limits enforced
- Security scanning with Trivy

### Network Security
- NetworkPolicy restricts traffic
- HTTPS termination at ingress
- Rate limiting configured
- CORS properly configured

### File Security
- File type validation
- Size limits enforced
- Temporary file cleanup
- Isolated upload directory

## 🚨 Troubleshooting

### Common Issues

1. **Pod CrashLoopBackOff**:
```bash
# Check pod logs
kubectl logs <pod-name> -n rapid-minutes

# Check pod events
kubectl describe pod <pod-name> -n rapid-minutes

# Common causes:
# - Missing ConfigMap/Secret
# - Resource limits too low
# - Health check failing
```

2. **Service Unreachable**:
```bash
# Check service endpoints
kubectl get endpoints -n rapid-minutes

# Test service connectivity
kubectl run debug --image=curlimages/curl --rm -i --restart=Never -- curl -v http://rapid-minutes-export-service/health
```

3. **Ingress Issues**:
```bash
# Check ingress status
kubectl describe ingress rapid-minutes-export-ingress -n rapid-minutes

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

### Performance Issues

1. **High Memory Usage**:
   - Check resource requests/limits
   - Monitor file upload sizes
   - Review concurrent processing limits

2. **Slow Response Times**:
   - Check HPA scaling
   - Monitor AI processing times
   - Review database/storage performance

### Recovery Procedures

1. **Rolling Restart**:
```bash
kubectl rollout restart deployment/rapid-minutes-export -n rapid-minutes
```

2. **Rollback Deployment**:
```bash
# View rollout history
kubectl rollout history deployment/rapid-minutes-export -n rapid-minutes

# Rollback to previous version
kubectl rollout undo deployment/rapid-minutes-export -n rapid-minutes
```

3. **Emergency Scale Down**:
```bash
kubectl scale deployment rapid-minutes-export --replicas=0 -n rapid-minutes
# Fix issues, then scale back up
kubectl scale deployment rapid-minutes-export --replicas=3 -n rapid-minutes
```

## 📞 Support

For deployment issues:
1. Check application logs first
2. Verify configuration values
3. Test connectivity between components
4. Review resource usage and scaling
5. Contact development team with specific error messages and logs

## 🔄 CI/CD Pipeline

The GitHub Actions workflow automatically:
1. Runs tests and security scans
2. Builds and pushes Docker images
3. Deploys to staging on `develop` branch
4. Deploys to production on `main` branch
5. Sends deployment notifications

Configure the following secrets in GitHub:
- `CODECOV_TOKEN` - For coverage reporting
- Kubernetes access credentials for deployment
- Container registry credentials