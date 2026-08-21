# SmartReach AI - Deployment Guide

**Project:** AI-Powered B2B Lead Generation & Outreach Platform  
**Version:** 0.1.0  
**Last Updated:** 2026-08-10

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Database Setup](#database-setup)
4. [Running the Application](#running-the-application)
5. [Verification & Testing](#verification--testing)
6. [Local Development Setup](#local-development-setup)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)
9. [Security Checklist](#security-checklist)

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| **Docker** | 20.10+ | Containerization |
| **Docker Compose** | 2.0+ | Multi-container orchestration |
| **Git** | Latest | Cloning repository |
| **Python** | 3.11+ | Local backend development |
| **Node.js** | 20+ | Local frontend development |
| **MySQL** | 8.0+ | (Optional if using Docker) |
| **Redis** | 7+ | (Optional if using Docker) |

### System Requirements

- **RAM:** 4GB minimum (8GB recommended)
- **Disk Space:** 10GB free space
- **OS:** Windows 10/11, macOS 10.15+, or Linux

### Optional (For Local Development)

```bash
# Verify installations
docker --version
docker-compose --version
python --version
node --version
npm --version
```

---

## Quick Start (Docker)

### Step 1: Clone & Navigate

```bash
# Navigate to project directory
cd "c:\Users\Rizwan\Desktop\Office Work\Devops-work\ai agent\smart-reach-ai"
```

### Step 2: Environment Configuration

```bash
# Copy environment template
copy .env.example .env

# Edit .env with your settings (notepad, nano, etc.)
notepad .env
```

**Critical Environment Variables (Required for Deployment):**

```env
# -----------------------------------------------------------------------------
# MUST CHANGE IN PRODUCTION
# -----------------------------------------------------------------------------
SECRET_KEY=generate-a-secure-random-string-here
ENCRYPTION_KEY=generate-a-32-byte-base64-key-here

# -----------------------------------------------------------------------------
# Database (Docker handles this automatically)
# -----------------------------------------------------------------------------
DATABASE_URL=mysql+aiomysql://leadgen_user:leadgen_pass@db:3306/leadgen_db

# -----------------------------------------------------------------------------
# Redis (Docker handles this automatically)
# -----------------------------------------------------------------------------
REDIS_URL=redis://redis:6379/0

# -----------------------------------------------------------------------------
# Application Settings
# -----------------------------------------------------------------------------
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000,http://frontend:3000
```

**Optional (For Future Features):**

```env
# AI Providers (Phase 2)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Search Providers (Iteration 1.4)
BING_SEARCH_API_KEY=your_key_here

# Email Providers (Phase 3)
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Step 3: Database Migration Setup

**IMPORTANT:** The Alembic migrations need to be initialized first.

#### Option A: Initialize Fresh (Recommended)

```bash
cd backend

# Initialize Alembic
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# Initialize Alembic
alembic init alembic
```

Then edit `alembic/env.py` to include your models:

```python
# Add this at the top of alembic/env.py
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import your models
from app.db.base import Base
from app.models.user import User
from app.models.campaign import Campaign

# Add this to target_metadata
target_metadata = Base.metadata
```

Create initial migration:

```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

#### Option B: Run in Docker After Init

```bash
# After initializing Alembic locally, run in Docker
cd ..  # Back to project root

# Build and start containers
docker-compose build
docker-compose up -d

# Run migrations in container
docker-compose exec backend alembic upgrade head
```

### Step 4: Build & Start Containers

```bash
# From project root
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

Expected output:
```
NAME                STATUS              PORTS
frontend            Up                 0.0.0.0:3000->3000/tcp
backend             Up                 0.0.0.0:8000->8000/tcp
db                  Up (healthy)       0.0.0.0:3306->3306/tcp
redis               Up (healthy)       0.0.0.0:6379->6379/tcp
worker              Up
scheduler           Up
```

### Step 5: Verify Services

```bash
# Check backend health
curl http://localhost:8000/health

# Check API docs (in browser)
# http://localhost:8000/docs

# Check frontend (in browser)
# http://localhost:3000
```

---

## Database Setup

### Manual Database Creation (Without Docker)

If you're not using Docker for the database:

```bash
# Connect to MySQL
mysql -u root -p

# Create database and user
CREATE DATABASE leadgen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'leadgen_user'@'localhost' IDENTIFIED BY 'leadgen_pass';
GRANT ALL PRIVILEGES ON leadgen_db.* TO 'leadgen_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### Running Migrations

```bash
# In Docker
docker-compose exec backend alembic upgrade head

# Locally
cd backend
alembic upgrade head
```

### Creating Admin User (Optional)

```bash
# In Docker
docker-compose exec backend python -m app.cli.create_admin

# Provide: email, password, full name
```

---

## Running the Application

### Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (deletes data!)
docker-compose down -v

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart specific service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build backend
```

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | Main application UI |
| **Backend API** | http://localhost:8000 | REST API |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **ReDoc** | http://localhost:8000/redoc | Alternative API docs |
| **Flower** | http://localhost:5555 | Celery task monitoring (if enabled) |

---

## Verification & Testing

### 1. Health Check

```bash
# Backend health endpoint
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "AI Lead Generation Platform",
  "environment": "development",
  "version": "0.1.0"
}
```

### 2. Database Connection

```bash
# In backend container
docker-compose exec backend python -c "
from app.db.base import engine
import asyncio
async def test():
    async with engine.begin() as conn:
        await conn.execute('SELECT 1')
    print('Database connection OK!')
asyncio.run(test())
"
```

### 3. Frontend Access

Open browser and navigate to:
- http://localhost:3000

You should see:
- Login/Register page
- Clean UI with Tailwind styling
- No console errors

### 4. User Registration Flow

1. Navigate to http://localhost:3000/register
2. Fill in:
   - Email: `test@example.com`
   - Password: `TestPass123!`
   - Full Name: `Test User`
3. Submit
4. Should redirect to login page
5. Login with credentials
6. Should redirect to Campaigns page

### 5. Create Campaign Test

1. After login, click "New Campaign"
2. Fill form:
   - Campaign Name: `Test Campaign`
   - Description: `Testing the platform`
   - Add 5 keywords:
     - `REDCap consultant`
     - `REDCap hosting`
     - `REDCap support`
     - `REDCap development`
     - `Clinical research software`
3. Submit
4. Should see campaign in list

### 6. API Testing

Using the API docs at http://localhost:8000/docs:

1. Login to get token:
   - POST `/api/v1/auth/login`
   - Use credentials from registration
   - Copy `access_token`

2. Use token for authenticated requests:
   - Click "Authorize" button
   - Enter: `Bearer YOUR_TOKEN_HERE`
   - Now you can test protected endpoints

3. Test Campaign endpoints:
   - GET `/api/v1/campaigns` - List campaigns
   - POST `/api/v1/campaigns` - Create campaign
   - GET `/api/v1/campaigns/{id}` - Get specific campaign

---

## Local Development Setup

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables (use .env file)
set-env.cmd  # Or manually set

# Run development server
uvicorn app.main:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Run Celery beat (separate terminal)
celery -A app.tasks.celery_app beat --loglevel=info
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

# Run development server
npm run dev
```

### Database for Local Development

```bash
# Option 1: Use Docker database only
docker-compose up -d db redis

# Option 2: Install MySQL and Redis locally
# Then update .env with local connection strings
```

---

## Production Deployment

### Prerequisites for Production

- [ ] SSL certificates (Let's Encrypt or custom)
- [ ] Domain name configured
- [ ] Server with Docker installed
- [ ] Environment variables secured
- [ ] Database backup strategy
- [ ] Log aggregation

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=https://api.yourdomain.com
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.frontend.tls=true"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=mysql+aiomysql://user:pass@db:3306/dbname
    env_file:
      - .env.production
    secrets:
      - db_password
      - secret_key

  db:
    image: mysql:8.0
    volumes:
      - mysql_prod:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD_FILE=/run/secrets/db_root_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
  secret_key:
    file: ./secrets/secret_key.txt

volumes:
  mysql_prod:
```

### Deployment Steps

```bash
# On production server

# 1. Clone repository
git clone <your-repo-url> /var/www/smart-reach-ai
cd /var/www/smart-reach-ai

# 2. Create secrets
mkdir secrets
echo "your-secure-password" > secrets/db_password.txt
echo "your-secret-key" > secrets/secret_key.txt
chmod 600 secrets/*

# 3. Create production environment
cp .env.example .env.production
nano .env.production  # Edit with production values

# 4. Build and start
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 5. Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# 6. Create admin user
docker-compose -f docker-compose.prod.yml exec backend python -m app.cli.create_admin
```

### SSL/TLS Setup with Traefik

```yaml
# docker-compose.traefik.yml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik.yml:/etc/traefik/traefik.yml
      - ./acme.json:/acme.json
    command:
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

**Symptom:** `Backend logs show "Database connection failed"`

**Solutions:**
```bash
# Check MySQL is running
docker-compose ps db

# Check MySQL logs
docker-compose logs db

# Restart database
docker-compose restart db

# Verify connection string in .env
echo $DATABASE_URL
```

#### 2. Frontend Can't Reach Backend

**Symptom:** `Network errors in browser console`

**Solutions:**
```bash
# Check both are running
docker-compose ps

# Verify CORS settings
# In .env: CORS_ORIGINS=http://localhost:3000,http://frontend:3000

# Check backend is accessible
curl http://localhost:8000/health
```

#### 3. Alembic Migration Errors

**Symptom:** `Target database is not up to date`

**Solutions:**
```bash
# Check current version
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history

# Reset (WARNING: Deletes data!)
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

#### 4. Container Won't Start

**Symptom:** `Container exits immediately`

**Solutions:**
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Port already in use: Change port in docker-compose.yml
# - Missing .env: Create from .env.example
# - Volume permission issues: Restart Docker Desktop

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

#### 5. "Module Not Found" Errors

**Symptom:** `ModuleNotFoundError: No module named 'app'`

**Solutions:**
```bash
# Rebuild container
docker-compose build backend

# Or reinstall dependencies locally
cd backend
pip install -r requirements.txt
```

### Debug Mode

```bash
# Enable detailed logging
# In .env:
LOG_LEVEL=DEBUG

# Restart with debug output
docker-compose up

# Shell into container
docker-compose exec backend bash
docker-compose exec frontend sh
```

### Health Check Script

Create `health-check.sh`:

```bash
#!/bin/bash

echo "Checking SmartReach AI services..."

# Check containers
docker-compose ps | grep "Up" || exit 1

# Check backend
curl -f http://localhost:8000/health || exit 1

# Check frontend
curl -f http://localhost:3000 > /dev/null || exit 1

# Check database
docker-compose exec -T backend python -c "
from app.db.base import engine
import asyncio
asyncio.run(engine.connect())
" || exit 1

echo "All services healthy!"
```

---

## Security Checklist

### Before Production Deployment

- [ ] Change all default passwords in `.env`
- [ ] Generate secure `SECRET_KEY` (32+ random bytes)
- [ ] Generate secure `ENCRYPTION_KEY`
- [ ] Set `ENVIRONMENT=production`
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Configure rate limiting
- [ ] Set up log aggregation
- [ ] Enable database backups
- [ ] Review API key permissions
- [ ] Set up monitoring/alerts
- [ ] Configure email authentication
- [ ] Test GDPR compliance features
- [ ] Set up error tracking (Sentry)
- [ ] Document disaster recovery plan

### Password Generation

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"

# Generate DB password
openssl rand -base64 24
```

### File Permissions

```bash
# Secure sensitive files
chmod 600 .env
chmod 600 .env.production
chmod 700 secrets/
chmod 600 secrets/*
```

---

## Monitoring

### Application Logs

```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend

# Worker logs
docker-compose logs -f worker

# All logs
docker-compose logs -f
```

### Database Monitoring

```bash
# Connect to MySQL
docker-compose exec db mysql -u root -p

# Check database size
SELECT table_schema, 
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS "Size (MB)"
FROM information_schema.tables
GROUP BY table_schema;

# Check connections
SHOW PROCESSLIST;
```

### Celery Monitoring (Flower)

Add to `docker-compose.yml`:

```yaml
flower:
  build: ./backend
  command: celery -A app.tasks.celery_app flower --port=5555
  ports:
    - "5555:5555"
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/0
```

Access at: http://localhost:5555

---

## Backup & Restore

### Database Backup

```bash
# Backup
docker-compose exec db mysqldump -u root -p leadgen_db > backup.sql

# Restore
docker-compose exec -T db mysql -u root -p leadgen_db < backup.sql
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * cd /path/to/project && docker-compose exec db mysqldump -u root -pPASSWORD leadgen_db > /backups/leadgen_$(date +\%Y\%m\%d).sql
```

---

## Support

For issues and questions:
- Check this guide first
- Review logs: `docker-compose logs`
- Check API docs: http://localhost:8000/docs
- Check development plan: [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)

---

**End of Deployment Guide**

Next: After successful deployment, proceed with [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) for feature implementation.
