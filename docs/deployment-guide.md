# Deployment Guide

Production deployment guide for Efektywniejsi Ekosystem API.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Docker Production Setup](#docker-production-setup)
4. [Database Setup](#database-setup)
5. [Nginx Reverse Proxy](#nginx-reverse-proxy)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup Strategy](#backup-strategy)
10. [Scaling](#scaling)
11. [Security Checklist](#security-checklist)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Server Requirements

**Minimum (Single Server):**
- 2 CPU cores
- 4 GB RAM
- 50 GB SSD
- Ubuntu 22.04 LTS or similar

**Recommended (Production):**
- 4+ CPU cores
- 8+ GB RAM
- 100+ GB SSD
- Ubuntu 22.04 LTS

### Software Requirements

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Install nginx
sudo apt install nginx -y

# Install certbot (for SSL)
sudo apt install certbot python3-certbot-nginx -y
```

---

## Environment Configuration

### Create Production `.env`

```bash
# Copy template
cp .env.example .env.production

# Edit with production values
nano .env.production
```

### Production `.env` Template

```env
# ======================
# APPLICATION
# ======================
ENVIRONMENT=production
DEBUG=false
API_VERSION=v1

# ======================
# DATABASE
# ======================
# Use managed PostgreSQL (e.g., AWS RDS, DigitalOcean Managed DB)
DATABASE_URL=postgresql://username:password@db-host:5432/dbname

# Connection pool settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# ======================
# REDIS
# ======================
# Use managed Redis or dedicated server
REDIS_URL=redis://redis-host:6379/0
REDIS_PASSWORD=your_redis_password

# ======================
# JWT & SECURITY
# ======================
# Generate with: openssl rand -hex 32
SECRET_KEY=YOUR_STRONG_RANDOM_SECRET_KEY_64_CHARS_MINIMUM_PLEASE
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# ======================
# FRONTEND
# ======================
FRONTEND_URL=https://yourdomain.com
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]

# ======================
# EMAIL (SMTP)
# ======================
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your_sendgrid_api_key
SMTP_FROM_EMAIL=noreply@yourdomain.com
SMTP_FROM_NAME="Efektywniejsi"
SMTP_USE_TLS=true

# ======================
# FILE UPLOADS
# ======================
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE_MB=50

# ======================
# MUX VIDEO
# ======================
MUX_TOKEN_ID=your_production_mux_token_id
MUX_TOKEN_SECRET=your_production_mux_token_secret

# ======================
# MONITORING & LOGGING
# ======================
SENTRY_DSN=https://your_sentry_dsn@sentry.io/project_id
LOG_LEVEL=INFO

# ======================
# RATE LIMITING
# ======================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_HOUR=1000
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY (64 chars)
openssl rand -hex 32

# Generate random password
openssl rand -base64 32
```

---

## Docker Production Setup

### Dockerfile (Production-ready)

```dockerfile
FROM python:3.12-slim

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -m -u 1000 appuser && mkdir -p /app /app/uploads
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -r pyproject.toml

# Copy application
COPY --chown=appuser:appuser . .

# Create uploads directory
RUN chown -R appuser:appuser /app/uploads

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8001/health').raise_for_status()"

# Expose port
EXPOSE 8001

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

### docker-compose.production.yml

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    image: efektywniejsi-api:latest
    container_name: efektywniejsi-api
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "8001:8001"
    volumes:
      - uploads_data:/app/uploads
    depends_on:
      - redis
    networks:
      - efektywniejsi_network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    container_name: efektywniejsi-redis
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - efektywniejsi_network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  uploads_data:
  redis_data:

networks:
  efektywniejsi_network:
    driver: bridge
```

### Build and Deploy

```bash
# Build image
docker build -t efektywniejsi-api:latest .

# Or build with docker-compose
docker-compose -f docker-compose.production.yml build

# Run migrations
docker-compose -f docker-compose.production.yml run --rm api \
  uv run alembic upgrade head

# Seed data (first time only)
docker-compose -f docker-compose.production.yml run --rm api \
  uv run python app/scripts/seed_achievements.py

# Start services
docker-compose -f docker-compose.production.yml up -d

# Check logs
docker-compose -f docker-compose.production.yml logs -f api

# Check health
curl http://localhost:8001/health
```

---

## Database Setup

### Managed PostgreSQL (Recommended)

**AWS RDS:**
```bash
# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier efektywniejsi-prod \
  --db-instance-class db.t3.medium \
  --engine postgres \
  --engine-version 16.1 \
  --master-username admin \
  --master-user-password <strong-password> \
  --allocated-storage 100 \
  --storage-encrypted \
  --backup-retention-period 7 \
  --preferred-backup-window "03:00-04:00" \
  --multi-az
```

**DigitalOcean Managed Database:**
- Go to Databases → Create
- Select PostgreSQL 16
- Choose plan (Basic $15/mo or higher)
- Enable automated backups
- Copy connection string to `.env.production`

### Self-Hosted PostgreSQL

**docker-compose.production.yml addition:**
```yaml
  postgres:
    image: postgres:16-alpine
    container_name: efektywniejsi-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - efektywniejsi_network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  postgres_data:
```

### Database Migrations

```bash
# Run migrations on deployment
docker-compose -f docker-compose.production.yml exec api \
  uv run alembic upgrade head

# Rollback if needed
docker-compose -f docker-compose.production.yml exec api \
  uv run alembic downgrade -1

# Check current version
docker-compose -f docker-compose.production.yml exec api \
  uv run alembic current
```

---

## Nginx Reverse Proxy

### Install and Configure

```bash
# Install nginx
sudo apt install nginx -y

# Create configuration
sudo nano /etc/nginx/sites-available/efektywniejsi-api
```

### Nginx Configuration

```nginx
upstream api_backend {
    server localhost:8001;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL certificates (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' https:; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;

    # Logging
    access_log /var/log/nginx/efektywniejsi-api-access.log;
    error_log /var/log/nginx/efektywniejsi-api-error.log;

    # Max upload size
    client_max_body_size 50M;

    # Proxy settings
    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (no auth)
    location /health {
        proxy_pass http://api_backend/health;
        access_log off;
    }

    # Static files (if any)
    location /static/ {
        alias /var/www/efektywniejsi/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Enable Site

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/efektywniejsi-api /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal is enabled by default
# Test renewal
sudo certbot renew --dry-run

# Check renewal timer
sudo systemctl status certbot.timer
```

### Manual SSL (if using custom certificate)

```nginx
ssl_certificate /path/to/fullchain.pem;
ssl_certificate_key /path/to/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
```

---

## CI/CD Pipeline

### GitHub Actions

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run tests
        run: uv run python -m pytest tests/ -v

      - name: Run linter
        run: uv run ruff check .

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: yourusername/efektywniejsi-api:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@v0.1.10
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/efektywniejsi-api
            docker-compose -f docker-compose.production.yml pull
            docker-compose -f docker-compose.production.yml up -d
            docker-compose -f docker-compose.production.yml exec -T api uv run alembic upgrade head
```

### Secrets to Set

In GitHub repo settings → Secrets:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `SERVER_HOST`
- `SERVER_USER`
- `SSH_PRIVATE_KEY`

---

## Monitoring & Logging

### Application Monitoring (Sentry)

```bash
# Add to requirements
pip install sentry-sdk[fastapi]
```

**app/main.py:**
```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment="production",
)
```

### Logging

**Configure structured logging:**
```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(log_data)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
```

### Prometheus Metrics

```bash
# Install prometheus_fastapi_instrumentator
pip install prometheus-fastapi-instrumentator
```

**app/main.py:**
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## Backup Strategy

### Database Backups

**Automated daily backups:**

```bash
#!/bin/bash
# /opt/backups/backup-database.sh

BACKUP_DIR="/opt/backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"

# Create backup
docker-compose exec -T postgres pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp $BACKUP_FILE s3://your-backup-bucket/database/
```

**Add to crontab:**
```bash
0 3 * * * /opt/backups/backup-database.sh >> /var/log/backup.log 2>&1
```

### Upload Directory Backups

```bash
#!/bin/bash
# Backup uploads to S3
aws s3 sync /app/uploads s3://your-backup-bucket/uploads/ --delete
```

### Restore from Backup

```bash
# Restore database
gunzip < backup_20260111_030000.sql.gz | \
  docker-compose exec -T postgres psql -U $DB_USER $DB_NAME

# Restore uploads
aws s3 sync s3://your-backup-bucket/uploads/ /app/uploads/
```

---

## Scaling

### Horizontal Scaling (Multiple API Instances)

**docker-compose.production.yml:**
```yaml
services:
  api:
    # ... same config ...
    deploy:
      replicas: 4  # Run 4 instances
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

**nginx load balancing:**
```nginx
upstream api_backend {
    least_conn;  # Load balancing algorithm
    server api1:8001;
    server api2:8001;
    server api3:8001;
    server api4:8001;
}
```

### Database Connection Pooling

**.env.production:**
```env
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

### Redis Clustering (for high traffic)

Use Redis Cluster or Redis Sentinel for high availability.

---

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY (64+ chars)
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall (only ports 80, 443, 22 open)
- [ ] Disable root SSH login
- [ ] Use SSH keys (no password auth)
- [ ] Enable automated security updates
- [ ] Configure fail2ban for SSH
- [ ] Set up WAF (Cloudflare, AWS WAF)
- [ ] Enable database encryption at rest
- [ ] Use managed services for DB and Redis
- [ ] Implement rate limiting
- [ ] Configure CORS properly
- [ ] Enable Sentry error tracking
- [ ] Set up monitoring alerts
- [ ] Regular security audits
- [ ] Keep dependencies updated

---

## Troubleshooting

### API Not Responding

```bash
# Check container status
docker ps

# Check logs
docker-compose logs -f api

# Check health
curl http://localhost:8001/health

# Restart container
docker-compose restart api
```

### Database Connection Issues

```bash
# Test database connection
docker-compose exec api \
  uv run python -c "from app.db.session import engine; engine.connect()"

# Check PostgreSQL is running
docker ps | grep postgres

# Check connection string
echo $DATABASE_URL
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Reduce workers
# In Dockerfile: --workers 2 (instead of 4)

# Increase server memory
```

### SSL Certificate Issues

```bash
# Check certificate expiry
sudo certbot certificates

# Renew manually
sudo certbot renew

# Check nginx configuration
sudo nginx -t
```

---

## Post-Deployment Checklist

- [ ] DNS records pointing to server
- [ ] SSL certificate installed and auto-renewing
- [ ] Database migrations run
- [ ] Seed data loaded (achievements, demo course)
- [ ] Environment variables set
- [ ] Monitoring configured (Sentry, logs)
- [ ] Backups scheduled
- [ ] Health check endpoint responding
- [ ] API docs accessible
- [ ] Rate limiting working
- [ ] CORS configured correctly
- [ ] Test user flows (signup, login, enroll, progress)
- [ ] Performance testing completed
- [ ] Security scan passed

---

**Last Updated:** 2026-01-11
