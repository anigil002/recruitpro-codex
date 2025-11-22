# RecruitPro Deployment Guide

**Platform-specific deployment guides for production**

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Self-Hosted Deployment](#self-hosted-deployment)
3. [Systemd Service Setup (Linux)](#systemd-service-setup-linux)
4. [Docker Deployment](#docker-deployment)
5. [Process Management](#process-management)
6. [Reverse Proxy Setup (Nginx)](#reverse-proxy-setup-nginx)
7. [SSL/HTTPS Setup](#sslhttps-setup)
8. [Environment-Specific Configurations](#environment-specific-configurations)

---

## Deployment Overview

RecruitPro consists of two main processes:

1. **Web Server** (FastAPI/Uvicorn) - Handles HTTP requests
2. **Worker** (RQ) - Processes background jobs

Both must run continuously in production.

**Required Services:**
- PostgreSQL database (cloud or local)
- Redis server (cloud or local)
- Web server process
- Worker process

---

## Self-Hosted Deployment

### On Your Own Server/VM (Ubuntu/Debian)

#### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip \
                    postgresql-client redis-tools nginx git

# Create application user
sudo useradd -m -s /bin/bash recruitpro
sudo su - recruitpro
```

#### 2. Clone and Setup

```bash
# Clone repository
git clone https://github.com/your-org/recruitpro-codex.git
cd recruitpro-codex

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.production.example .env
nano .env  # Edit with your settings
```

#### 3. Run Database Migrations

```bash
alembic upgrade head
```

#### 4. Test Services

```bash
# Test web server
uvicorn app.main:app --host 127.0.0.1 --port 8000

# In another terminal, test worker
source venv/bin/activate
python worker.py
```

---

## Systemd Service Setup (Linux)

**Recommended for production on Linux servers**

### 1. Create Web Server Service

Create `/etc/systemd/system/recruitpro-web.service`:

```ini
[Unit]
Description=RecruitPro Web Server
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=recruitpro
Group=recruitpro
WorkingDirectory=/home/recruitpro/recruitpro-codex
Environment="PATH=/home/recruitpro/recruitpro-codex/venv/bin"
EnvironmentFile=/home/recruitpro/recruitpro-codex/.env
ExecStart=/home/recruitpro/recruitpro-codex/venv/bin/uvicorn app.main:app \
          --host 0.0.0.0 \
          --port 8000 \
          --workers 2 \
          --log-level info

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=recruitpro-web

[Install]
WantedBy=multi-user.target
```

### 2. Create Worker Service

Create `/etc/systemd/system/recruitpro-worker.service`:

```ini
[Unit]
Description=RecruitPro Background Worker
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=recruitpro
Group=recruitpro
WorkingDirectory=/home/recruitpro/recruitpro-codex
Environment="PATH=/home/recruitpro/recruitpro-codex/venv/bin"
EnvironmentFile=/home/recruitpro/recruitpro-codex/.env
ExecStart=/home/recruitpro/recruitpro-codex/venv/bin/python worker.py

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=recruitpro-worker

[Install]
WantedBy=multi-user.target
```

### 3. Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services (start on boot)
sudo systemctl enable recruitpro-web
sudo systemctl enable recruitpro-worker

# Start services
sudo systemctl start recruitpro-web
sudo systemctl start recruitpro-worker

# Check status
sudo systemctl status recruitpro-web
sudo systemctl status recruitpro-worker

# View logs
sudo journalctl -u recruitpro-web -f
sudo journalctl -u recruitpro-worker -f
```

### 4. Manage Services

```bash
# Start services
sudo systemctl start recruitpro-web recruitpro-worker

# Stop services
sudo systemctl stop recruitpro-web recruitpro-worker

# Restart services
sudo systemctl restart recruitpro-web recruitpro-worker

# View logs
sudo journalctl -u recruitpro-web -n 100 --no-pager
sudo journalctl -u recruitpro-worker -n 100 --no-pager
```

---

## Docker Deployment

### 1. Create Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p storage data

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Create docker-compose.yml

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: recruitpro
      POSTGRES_USER: recruitpro
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U recruitpro"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  # Web Server
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      RECRUITPRO_DATABASE_URL: postgresql://recruitpro:${POSTGRES_PASSWORD}@postgres:5432/recruitpro
      REDIS_URL: redis://redis:6379/0
      USE_REDIS_QUEUE: "true"
      RECRUITPRO_SECRET_KEY: ${RECRUITPRO_SECRET_KEY}
      RECRUITPRO_ENVIRONMENT: production
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      SENTRY_DSN: ${SENTRY_DSN}
    volumes:
      - ./storage:/app/storage
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"

  # Worker
  worker:
    build: .
    environment:
      RECRUITPRO_DATABASE_URL: postgresql://recruitpro:${POSTGRES_PASSWORD}@postgres:5432/recruitpro
      REDIS_URL: redis://redis:6379/0
      USE_REDIS_QUEUE: "true"
      RECRUITPRO_SECRET_KEY: ${RECRUITPRO_SECRET_KEY}
      RECRUITPRO_ENVIRONMENT: production
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      SENTRY_DSN: ${SENTRY_DSN}
    volumes:
      - ./storage:/app/storage
      - ./data:/app/data
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: python worker.py

volumes:
  postgres_data:
  redis_data:
```

### 3. Create .env.docker

```bash
POSTGRES_PASSWORD=your-secure-password
RECRUITPRO_SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
SENTRY_DSN=your-sentry-dsn
```

### 4. Deploy with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f worker

# Check status
docker-compose ps

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

---

## Process Management

### Using tmux (Simple)

```bash
# Start new session
tmux new -s recruitpro

# Window 1: Web server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Create new window (Ctrl+B, C)
# Window 2: Worker
python worker.py

# Detach (Ctrl+B, D)
# Reattach
tmux attach -t recruitpro
```

### Using Supervisor (Alternative)

Install supervisor:
```bash
sudo apt install supervisor
```

Create `/etc/supervisor/conf.d/recruitpro.conf`:

```ini
[program:recruitpro-web]
command=/home/recruitpro/recruitpro-codex/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/home/recruitpro/recruitpro-codex
user=recruitpro
autostart=true
autorestart=true
stderr_logfile=/var/log/recruitpro/web.err.log
stdout_logfile=/var/log/recruitpro/web.out.log

[program:recruitpro-worker]
command=/home/recruitpro/recruitpro-codex/venv/bin/python worker.py
directory=/home/recruitpro/recruitpro-codex
user=recruitpro
autostart=true
autorestart=true
stderr_logfile=/var/log/recruitpro/worker.err.log
stdout_logfile=/var/log/recruitpro/worker.out.log
```

Manage services:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl status
sudo supervisorctl restart all
```

---

## Reverse Proxy Setup (Nginx)

### 1. Install Nginx

```bash
sudo apt install nginx
```

### 2. Create Nginx Configuration

Create `/etc/nginx/sites-available/recruitpro`:

```nginx
upstream recruitpro_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name recruitpro.yourdomain.com;

    client_max_body_size 50M;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name recruitpro.yourdomain.com;

    # SSL certificates (managed by certbot)
    ssl_certificate /etc/letsencrypt/live/recruitpro.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/recruitpro.yourdomain.com/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://recruitpro_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files
    location /static {
        alias /home/recruitpro/recruitpro-codex/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /storage {
        alias /home/recruitpro/recruitpro-codex/storage;
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

### 3. Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/recruitpro /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

---

## SSL/HTTPS Setup

### Using Let's Encrypt (Free)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d recruitpro.yourdomain.com

# Auto-renewal (already set up by certbot)
sudo certbot renew --dry-run
```

---

## Environment-Specific Configurations

### Development

```bash
RECRUITPRO_ENVIRONMENT=development
RECRUITPRO_DATABASE_URL=sqlite:///./data/recruitpro.db
# Redis not required - uses in-memory queue
USE_REDIS_QUEUE=false
LOG_LEVEL=DEBUG
```

### Staging

```bash
RECRUITPRO_ENVIRONMENT=staging
RECRUITPRO_DATABASE_URL=postgresql://...staging-db...
REDIS_URL=redis://...staging-redis...
USE_REDIS_QUEUE=true
SENTRY_DSN=your-staging-sentry-dsn
LOG_LEVEL=INFO
```

### Production

```bash
RECRUITPRO_ENVIRONMENT=production
RECRUITPRO_DATABASE_URL=postgresql://...prod-db...
REDIS_URL=redis://...prod-redis...
USE_REDIS_QUEUE=true
SENTRY_DSN=your-prod-sentry-dsn
LOG_LEVEL=INFO
```

---

## Post-Deployment Checklist

- ✅ All services are running (web + worker)
- ✅ Health check returns "healthy": `curl https://yourdomain.com/api/health`
- ✅ Database migrations are applied
- ✅ Redis queue is operational
- ✅ Gemini API is configured
- ✅ SSL/HTTPS is working
- ✅ Sentry is receiving errors
- ✅ Backups are configured
- ✅ Monitoring is set up
- ✅ Logs are accessible

---

## Updating Application

```bash
# Pull latest code
cd /home/recruitpro/recruitpro-codex
git pull origin main

# Activate venv
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart services (systemd)
sudo systemctl restart recruitpro-web recruitpro-worker

# OR restart services (docker)
docker-compose up -d --build

# Verify
curl http://localhost:8000/api/health
```

---

## Quick Reference Commands

```bash
# Check service status
sudo systemctl status recruitpro-web recruitpro-worker

# View logs
sudo journalctl -u recruitpro-web -f
sudo journalctl -u recruitpro-worker -f

# Restart services
sudo systemctl restart recruitpro-web recruitpro-worker

# Test health
curl http://localhost:8000/api/health

# Check queue status
curl http://localhost:8000/api/queue/status

# Database backup
pg_dump $RECRUITPRO_DATABASE_URL > backup_$(date +%Y%m%d).sql
```

---

## Need Help?

- See `TROUBLESHOOTING.md` for common issues
- Check logs: `sudo journalctl -u recruitpro-web -n 100`
- Verify health: `curl http://localhost:8000/api/health`
