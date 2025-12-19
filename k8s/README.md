# Kubernetes Deployment Guide

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Docker registry access (or use local images)
- Optional: Helm for Grafana/Prometheus

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f k8s/ingress.yaml  # Creates namespace
```

### 2. Deploy PostgreSQL

```bash
# Update password in k8s/postgres.yaml first!
kubectl apply -f k8s/postgres.yaml
```

### 3. Configure Secrets

Edit `k8s/deployment.yaml` and update:
- `github-token`: Your GitHub Personal Access Token
- `database-url`: PostgreSQL connection string
- `slack-webhook`: (Optional) Slack webhook URL

```bash
# Apply secrets
kubectl create secret generic validator-secrets \
  --from-literal=github-token=YOUR_TOKEN \
  --from-literal=database-url=postgresql+asyncpg://validator_user:validator_pass@postgres:5432/validator_db \
  -n validator
```

### 4. Deploy Application

```bash
# Build and push Docker image
docker build -t your-registry/cloud-service-validator:latest .
docker push your-registry/cloud-service-validator:latest

# Update image in k8s/deployment.yaml

# Deploy
kubectl apply -f k8s/deployment.yaml
```

### 5. Deploy Ingress (Optional)

```bash
# Update host in k8s/ingress.yaml
kubectl apply -f k8s/ingress.yaml
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods -n validator

# Check services
kubectl get svc -n validator

# Check logs
kubectl logs -f deployment/cloud-service-validator -n validator
```

## Access the Application

### Port Forward (Development)

```bash
kubectl port-forward svc/validator-service 8000:80 -n validator
```

Access at: http://localhost:8000

### Via Ingress (Production)

Access at: https://validator.example.com

## Monitoring

### Deploy Prometheus

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/prometheus -n validator
```

### Deploy Grafana

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm install grafana grafana/grafana -n validator

# Get admin password
kubectl get secret --namespace validator grafana -o jsonpath="{.data.admin-password}" | base64 --decode
```

## Scaling

```bash
# Scale replicas
kubectl scale deployment cloud-service-validator --replicas=5 -n validator

# Enable HPA
kubectl autoscale deployment cloud-service-validator \
  --cpu-percent=70 \
  --min=2 \
  --max=10 \
  -n validator
```

## Troubleshooting

### Check Logs

```bash
# Application logs
kubectl logs -f deployment/cloud-service-validator -n validator

# PostgreSQL logs
kubectl logs -f statefulset/postgres -n validator
```

### Debug Pod

```bash
kubectl exec -it deployment/cloud-service-validator -n validator -- /bin/bash
```

### Check Events

```bash
kubectl get events -n validator --sort-by='.lastTimestamp'
```

## Backup & Restore

### Backup PostgreSQL

```bash
kubectl exec -it postgres-0 -n validator -- pg_dump -U validator_user validator_db > backup.sql
```

### Restore PostgreSQL

```bash
kubectl exec -i postgres-0 -n validator -- psql -U validator_user validator_db < backup.sql
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace validator
```
