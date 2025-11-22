# RecruitPro Production Setup Guide

**Complete guide to deploying RecruitPro for 2-user production use**

**Time to complete:** 60-90 minutes
**Skill level:** Intermediate Python/System Administration

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Google Gemini API Setup](#step-1-google-gemini-api-setup)
4. [Step 2: Database Setup (PostgreSQL)](#step-2-database-setup-postgresql)
5. [Step 3: Redis Setup](#step-3-redis-setup)
6. [Step 4: Application Configuration](#step-4-application-configuration)
7. [Step 5: Install Dependencies](#step-5-install-dependencies)
8. [Step 6: Database Migration](#step-6-database-migration)
9. [Step 7: Start Services](#step-7-start-services)
10. [Step 8: Verify Installation](#step-8-verify-installation)
11. [Step 9: Monitoring Setup (Optional)](#step-9-monitoring-setup-optional)
12. [Deployment Options](#deployment-options)
13. [Maintenance & Backups](#maintenance--backups)

---

## Overview

This guide walks you through deploying RecruitPro to production with:

- ✅ **Real AI Integration** - Google Gemini API for CV screening, document analysis, and market research
- ✅ **PostgreSQL Database** - Production-grade relational database
- ✅ **Redis + RQ Queue** - Persistent job queue for background processing
- ✅ **Automatic Retries** - Resilient error handling for API calls
- ✅ **Health Monitoring** - Built-in health checks for all services
- ✅ **Error Tracking** - Optional Sentry integration

**What you'll build:**

```
┌─────────────────────────────────────────────────┐
│  RecruitPro Production Architecture             │
├─────────────────────────────────────────────────┤
│                                                 │
│  Web Server (FastAPI/Uvicorn)                   │
│  ↓                                              │
│  PostgreSQL Database ←──────┐                   │
│  ↓                          │                   │
│  Redis Queue ←──────────────┤                   │
│  ↓                          │                   │
│  RQ Workers (Background Jobs)│                   │
│  ↓                          │                   │
│  Google Gemini API          │                   │
│  ↓                          │                   │
│  Sentry (Error Monitoring)  │                   │
└─────────────────────────────────────────────────┘
```

---

## Prerequisites

### Software Requirements

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/downloads))
- **PostgreSQL 14+** OR a cloud PostgreSQL service (Supabase, Neon, etc.)
- **Redis 6+** OR a cloud Redis service (Redis Cloud, Upstash, etc.)

### Accounts Needed

1. **Google AI Studio** (Free) - For Gemini API key
2. **PostgreSQL hosting** (Free tier available on Supabase/Neon)
3. **Redis hosting** (Free tier available on Redis Cloud/Upstash)
4. **Sentry** (Optional, free tier available)

### Knowledge Requirements

- Basic command line usage
- Basic understanding of environment variables
- Ability to copy/paste commands and edit text files

---

## Step 1: Google Gemini API Setup

**Time:** 5 minutes
**Cost:** Free (generous free tier: 15 requests/minute, 1500 requests/day)

### 1.1 Get Your Gemini API Key

1. Go to [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key)
2. Click **"Get API Key"**
3. Sign in with your Google account
4. Click **"Create API Key"**
5. Copy the API key (starts with `AIza...`)

### 1.2 Test Your API Key

```bash
# Test with curl
curl -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=YOUR_API_KEY"
```

**Expected response:** JSON with generated text

✅ **Checkpoint:** You have a working Gemini API key

---

## Step 2: Database Setup (PostgreSQL)

**Time:** 10-15 minutes
**Cost:** Free (using Supabase or Neon free tier)

### Option A: Cloud PostgreSQL (Recommended)

#### Using Supabase (Easiest)

1. Go to [Supabase](https://supabase.com)
2. Create a free account
3. Click **"New Project"**
4. Fill in:
   - **Project name:** `recruitpro`
   - **Database password:** Generate a strong password
   - **Region:** Choose closest to you
5. Wait 2-3 minutes for database to be created
6. Click **"Connect"** → **"URI"** → Copy the connection string

**Your connection string looks like:**
```
postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

#### Using Neon (Alternative)

1. Go to [Neon](https://neon.tech)
2. Create a free account
3. Click **"Create a project"**
4. Copy the connection string from the dashboard

### Option B: Local PostgreSQL

```bash
# macOS
brew install postgresql@14
brew services start postgresql@14
createdb recruitpro

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo -u postgres createdb recruitpro

# Windows
# Download installer from: https://www.postgresql.org/download/windows/
# Run installer and create database "recruitpro"
```

**Your local connection string:**
```
postgresql://postgres:password@localhost:5432/recruitpro
```

✅ **Checkpoint:** You have a PostgreSQL connection string

---

## Step 3: Redis Setup

**Time:** 10 minutes
**Cost:** Free (using Redis Cloud free tier: 30MB, perfect for 2 users)

### Option A: Cloud Redis (Recommended)

#### Using Redis Cloud

1. Go to [Redis Cloud](https://redis.com/try-free/)
2. Sign up for free account
3. Click **"New Database"**
4. Configure:
   - **Cloud Provider:** AWS
   - **Region:** Choose closest to you
   - **Database Name:** `recruitpro`
   - **Free plan:** 30MB (sufficient for 2 users)
5. Click **"Create Database"**
6. Copy the **"Public endpoint"** (e.g., `redis://default:password@host:port`)

#### Using Upstash (Alternative)

1. Go to [Upstash](https://upstash.com)
2. Create a free account
3. Create a Redis database
4. Copy the connection string

### Option B: Local Redis

```bash
# macOS
brew install redis
brew services start redis

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server

# Windows
# Download from: https://github.com/microsoftarchive/redis/releases
# Or use Docker: docker run -d -p 6379:6379 redis:7-alpine
```

**Test Redis connection:**
```bash
redis-cli ping
# Should return: PONG
```

**Your Redis connection string:**
- Local: `redis://localhost:6379/0`
- Cloud: `redis://default:password@host:port`

✅ **Checkpoint:** You have a Redis connection string

---

## Step 4: Application Configuration

**Time:** 5 minutes

### 4.1 Clone the Repository (if not already done)

```bash
git clone https://github.com/your-org/recruitpro-codex.git
cd recruitpro-codex
```

### 4.2 Create Environment Configuration

```bash
# Copy the production example
cp .env.production.example .env
```

### 4.3 Edit .env File

Open `.env` in your text editor and fill in:

```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the generated key and update your `.env`:

```bash
# REQUIRED SETTINGS
RECRUITPRO_SECRET_KEY="paste-your-generated-key-here"
RECRUITPRO_ENVIRONMENT="production"
RECRUITPRO_DATABASE_URL="postgresql://..." # From Step 2
REDIS_URL="redis://..." # From Step 3
USE_REDIS_QUEUE="true"
GEMINI_API_KEY="AIza..." # From Step 1

# CORS (add your domains)
RECRUITPRO_CORS_ALLOWED_ORIGINS="http://localhost:3000,https://yourdomain.com"

# OPTIONAL (but recommended)
SENTRY_DSN="" # Add in Step 9
LOG_LEVEL="INFO"
```

✅ **Checkpoint:** `.env` file is configured

---

## Step 5: Install Dependencies

**Time:** 5 minutes

### 5.1 Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### 5.2 Install Requirements

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected output:** All packages installed successfully

✅ **Checkpoint:** Dependencies installed

---

## Step 6: Database Migration

**Time:** 2 minutes

### 6.1 Run Migrations

```bash
alembic upgrade head
```

**Expected output:**
```
INFO  [alembic.runtime.migration] Running upgrade -> xxxx
INFO  [alembic.runtime.migration] Running upgrade xxxx -> yyyy
```

### 6.2 Verify Database

```bash
# Test database connection
python3 -c "from app.database import init_db; init_db(); print('✓ Database OK')"
```

✅ **Checkpoint:** Database schema created

---

## Step 7: Start Services

**Time:** 5 minutes

### 7.1 Terminal 1: Start Web Server

```bash
# Make sure you're in the project directory with venv activated
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     ✓ Connected to Redis at redis://...
INFO:     ✓ Using Redis + RQ for background jobs (production mode)
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 7.2 Terminal 2: Start RQ Worker

Open a new terminal, activate venv, and run:

```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
python worker.py
```

**Expected output:**
```
INFO:     ✓ Connected to Redis at redis://...
INFO:     Loading RecruitPro application and registering job handlers...
INFO:     ✓ Registered 6 job handlers:
INFO:       - cv_screening
INFO:       - file_analysis
INFO:       - linkedin_xray
INFO:       - market_research
INFO:       - ai_sourcing
INFO:       - smartrecruiters_bulk
INFO:     ✓ Starting RQ worker...
INFO:     Worker is ready to process jobs. Press Ctrl+C to stop.
```

✅ **Checkpoint:** All services running

---

## Step 8: Verify Installation

**Time:** 5 minutes

### 8.1 Check Health Endpoint

```bash
curl http://localhost:8000/api/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-21T...",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection OK"
    },
    "queue": {
      "status": "healthy",
      "message": "Queue operational (redis + rq)",
      "backend": "redis + rq",
      "queued": 0,
      "processed": 0,
      "failed": 0
    },
    "redis": {
      "status": "healthy",
      "message": "Redis connection OK"
    },
    "gemini_api": {
      "status": "healthy",
      "message": "Gemini API key configured",
      "configured": true
    }
  }
}
```

### 8.2 Access the Application

Open browser: `http://localhost:8000`

You should see the RecruitPro login page.

### 8.3 Test AI Integration

```bash
# Test via API (create user first via UI, then get token)
curl -X POST http://localhost:8000/api/ai/test \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello"}'
```

✅ **Checkpoint:** Application is fully operational!

---

## Step 9: Monitoring Setup (Optional)

**Time:** 10 minutes
**Highly Recommended for Production**

### 9.1 Set Up Sentry

1. Go to [Sentry.io](https://sentry.io)
2. Create a free account (5K events/month - plenty for 2 users)
3. Create a new project → Select **"FastAPI"**
4. Copy your **DSN** (looks like: `https://xxxxx@o123456.ingest.sentry.io/123456`)

### 9.2 Add Sentry to Configuration

Update `.env`:
```bash
SENTRY_DSN="https://xxxxx@o123456.ingest.sentry.io/123456"
```

### 9.3 Restart Application

```bash
# Stop uvicorn (Ctrl+C) and restart
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     ✓ Sentry initialized for environment: production
```

### 9.4 Test Error Reporting

```bash
# Trigger a test error
curl http://localhost:8000/api/test-error
```

Check Sentry dashboard - you should see the error!

✅ **Checkpoint:** Error monitoring enabled

---

## Deployment Options

### Option 1: Self-Hosted (Free - Your Own Hardware)

**Run on your laptop/server permanently:**

```bash
# Use tmux or screen to keep processes running
tmux new -s recruitpro

# Terminal 1: Web server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Split terminal (Ctrl+B, then ")
# Terminal 2: Worker
python worker.py

# Detach: Ctrl+B, then D
```

**Pros:** Free, full control
**Cons:** Requires computer to run 24/7

### Option 2: Cloud VM ($5-10/month)

**Deploy on DigitalOcean/AWS/Azure:**

1. Create a small VM (1GB RAM, 1 CPU)
2. Install Python, PostgreSQL, Redis
3. Follow this guide
4. Use systemd or supervisor to auto-restart services

**Cost:** $5-10/month (DigitalOcean Droplet: $6/month)

### Option 3: Platform-as-a-Service ($0-20/month)

**Deploy on Render/Railway/Fly.io:**

See `DEPLOYMENT.md` for platform-specific guides.

**Cost:** $0-20/month depending on platform

---

## Maintenance & Backups

### Daily Health Checks

```bash
# Automated health monitoring
curl http://localhost:8000/api/health
```

Set up a cron job or use a monitoring service (UptimeRobot - free).

### Database Backups

#### Automated Backup Script

Create `backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $RECRUITPRO_DATABASE_URL > "backups/recruitpro_$DATE.sql"

# Keep only last 7 days
find backups/ -name "recruitpro_*.sql" -mtime +7 -delete
```

Run daily via cron:
```bash
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

### Update Application

```bash
git pull origin main
pip install -r requirements.txt
alembic upgrade head
# Restart services
```

---

## Cost Summary (Production for 2 Users)

| Service | Provider | Cost |
|---------|----------|------|
| PostgreSQL | Supabase/Neon Free | $0 |
| Redis | Redis Cloud Free | $0 |
| Gemini API | Google | $0 (free tier) |
| Sentry | Sentry.io Free | $0 |
| Hosting | Self-hosted | $0 |
| **Total** | | **$0/month** |

**OR with cloud hosting:**

| Service | Provider | Cost |
|---------|----------|------|
| VM | DigitalOcean | $6/month |
| PostgreSQL | Supabase Free | $0 |
| Redis | Redis Cloud Free | $0 |
| Gemini API | Google | $0 |
| Sentry | Sentry.io | $0 |
| **Total** | | **$6/month** |

---

## Next Steps

- ✅ Read `DEPLOYMENT.md` for production deployment options
- ✅ Read `TROUBLESHOOTING.md` if you encounter issues
- ✅ Set up automated backups
- ✅ Configure monitoring alerts
- ✅ Test all AI features (CV screening, document analysis)

---

## Support

- **Documentation:** See `TROUBLESHOOTING.md`
- **Health Check:** `http://localhost:8000/api/health`
- **Queue Status:** `http://localhost:8000/api/queue/status`
- **Logs:** Check terminal outputs

---

## Security Checklist

- ✅ Generated strong `RECRUITPRO_SECRET_KEY`
- ✅ Using HTTPS in production (not localhost)
- ✅ Database credentials are secure
- ✅ `.env` file is NOT committed to git
- ✅ Gemini API key is kept secret
- ✅ CORS origins are restricted
- ✅ Sentry is configured for error monitoring
- ✅ Regular backups are enabled

---

**Congratulations! 🎉**

RecruitPro is now running in production mode with:
- Real AI integration
- Persistent database
- Reliable job queue
- Error monitoring
- Health checks

**Total setup time:** 60-90 minutes
**Cost:** $0-6/month for 2 users

Now you can start using RecruitPro for real recruitment workflows!
