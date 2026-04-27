# InkosAI Deployment Guide

Complete deployment instructions for Docker, Docker Compose, and Kubernetes.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/inkosai/inkosai.git
cd inkosai
cp .env.example .env
# Edit .env with your values

# Start services
docker-compose up -d

# Verify
curl http://localhost:8000/api/health
```

## Docker Deployment

### Build Image

```bash
docker build -t inkosai/api:latest .
```

### Run Container

```bash
docker run -d \
  --name inkosai-api \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  -e JWT_SECRET_KEY="your-secret" \
  inkosai/api:latest
```

## Docker Compose Deployment

### Production

```bash
# Copy production config
cp .env.production .env

# Generate secrets
openssl rand -hex 64  # JWT_SECRET_KEY
openssl rand -base64 32  # DB_PASSWORD

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Scale API replicas (if needed)
docker-compose up -d --scale api=3
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| api | 8000 | Main FastAPI application |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache/sessions |
| prometheus | 9090 | Metrics collection |
| jaeger | 16686 | Distributed tracing UI |
| grafana | 3001 | Monitoring dashboards |

### Health Checks

```bash
# Basic health
curl http://localhost:8000/api/health

# Readiness (for k8s)
curl http://localhost:8000/api/ready

# Detailed status
curl http://localhost:8000/api/health/detailed

# Metrics
curl http://localhost:8000/api/metrics
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Ingress controller (nginx recommended)

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: inkosai
```

### Secrets

```bash
# Create secrets
kubectl create secret generic inkosai-secrets \
  --namespace=inkosai \
  --from-literal=database-url="postgresql+asyncpg://..." \
  --from-literal=jwt-secret-key="$(openssl rand -hex 64)" \
  --from-literal=redis-password="$(openssl rand -base64 32)"
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inkosai-api
  namespace: inkosai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inkosai-api
  template:
    metadata:
      labels:
        app: inkosai-api
    spec:
      containers:
      - name: api
        image: inkosai/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: inkosai-secrets
              key: database-url
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: inkosai-secrets
              key: jwt-secret-key
        livenessProbe:
          httpGet:
            path: /api/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: inkosai-api
  namespace: inkosai
spec:
  selector:
    app: inkosai-api
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: inkosai-ingress
  namespace: inkosai
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    cert-manager.io/cluster-issuer: "letsencrypt"
spec:
  rules:
  - host: api.inkos.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: inkosai-api
            port:
              number: 80
  tls:
  - hosts:
    - api.inkos.ai
    secretName: inkosai-tls
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `postgresql+asyncpg://user:pass@host/db` |
| `JWT_SECRET_KEY` | JWT signing key | 64-byte hex string |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |

### Optional

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `None` | Redis connection |
| `ENVIRONMENT` | `development` | Environment name |
| `DEBUG` | `true` | Debug mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `PLUGIN_SANDBOX_MODE` | `disabled` | Plugin execution mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4318` | Tracing endpoint |

## SSL/TLS

### Let's Encrypt (cert-manager)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@inkos.ai
    privateKeySecretRef:
      name: letsencrypt
    solvers:
    - http01:
        ingress:
          class: nginx
```

### Manual Certificates

```bash
# Generate self-signed for testing
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key -out server.crt \
  -subj "/CN=api.inkos.ai"

kubectl create secret tls inkosai-tls \
  --cert=server.crt --key=server.key \
  --namespace=inkosai
```

## Backup & Recovery

### Database

```bash
# Backup
docker exec inkosai-postgres pg_dump -U inkosai inkosai > backup.sql

# Restore
docker exec -i inkosai-postgres psql -U inkosai inkosai < backup.sql
```

### Kubernetes

```bash
# Using velero
velero backup create inkosai-backup --include-namespaces inkosai

# Restore
velero restore create --from-backup inkosai-backup
```

## Monitoring Setup

### Prometheus

```bash
# Access UI
kubectl port-forward svc/prometheus 9090:9090 -n inkosai
```

### Grafana

```bash
# Access UI (default admin/admin)
kubectl port-forward svc/grafana 3000:3000 -n inkosai
```

### Alerts (example)

```yaml
- alert: HighErrorRate
  expr: rate(inkosai_http_requests_total{status_code=~"5.."}[5m]) > 0.1
  for: 5m
  labels:
    severity: critical
  annotations:
    summary: "High error rate detected"
```

## Troubleshooting

```bash
# Check pod status
kubectl get pods -n inkosai

# View logs
kubectl logs -f deployment/inkosai-api -n inkosai

# Exec into container
kubectl exec -it deployment/inkosai-api -n inkosai -- /bin/sh

# Check events
kubectl get events -n inkosai --sort-by='.lastTimestamp'
```

## Security Checklist

- [ ] JWT_SECRET_KEY is unique and random
- [ ] Database uses strong password
- [ ] Redis password configured
- [ ] TLS enabled in production
- [ ] Security headers active
- [ ] Rate limiting enabled
- [ ] Plugin sandbox mode set to `docker`
- [ ] DEBUG=false in production
- [ ] CORS origins restricted
- [ ] Request size limited
