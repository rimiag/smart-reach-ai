# Environment Configuration Guide
# AI Lead Generation Platform - Production Ready Setup

## 🎯 Overview

This platform uses a **layered environment configuration** that works seamlessly for:
- ✅ **Local Development** - Your local database and services
- ✅ **Docker Development** - Containerized services with internal networking
- ✅ **Production** - External services and secure configurations

## 📁 Environment Files Structure

```
smart-reach-ai/
├── backend/
│   ├── .env                    # Local development (gitignored)
│   ├── .env.example           # Template for developers
│   └── .env.local.example     # Reference copy of .env
├── .env.production            # Production overrides (gitignored)
└── docker-compose.yml         # Docker environment variables
```

## 🔧 Environment Priority (Highest to Lowest)

1. **Docker Compose Environment Variables** - When running in Docker
2. **System Environment Variables** - Set via `export` or `.env` file
3. **Default Values** - From `app/core/config.py`

## 🚀 Quick Setup Guide

### 1. Local Development Setup

```bash
# Copy the example file
cp backend/.env.example backend/.env

# Edit with your local database credentials
nano backend/.env

# Update DATABASE_URL for your local database
DATABASE_URL=mariadb+aiomysql://root:yourpassword@localhost:3306/leadgen_db
```

**Local .env file should use:**
- `localhost` for database host
- `localhost` for Redis host
- Your local database credentials

### 2. Docker Development Setup

```bash
# Docker uses docker-compose.yml environment variables
# No need to configure DATABASE_URL - it's already set in docker-compose.yml

# Just start the services
docker-compose up -d --build
```

**Docker environment automatically uses:**
- `db` for database host (internal Docker network)
- `redis` for Redis host (internal Docker network)
- Docker database credentials (`leadgen_user:leadgen_pass`)

### 3. Production Setup

```bash
# Copy production template
cp .env.production .env.production.local

# Edit with your production values
nano .env.production.local

# Deploy with production overrides
docker-compose --env-file .env.production.local up -d
```

## 🔑 Key Environment Variables

### Database Configuration

| Environment | DATABASE_URL Format |
|-------------|---------------------|
| Local Dev | `mariadb+aiomysql://root:pass@localhost:3306/leadgen_db` |
| Docker | `mariadb+aiomysql://leadgen_user:leadgen_pass@db:3306/leadgen_db` |
| Production | `mariadb+aiomysql://user:pass@prod-db-host:3306/leadgen_db` |

### Redis Configuration

| Environment | REDIS_URL Format |
|-------------|-----------------|
| Local Dev | `redis://localhost:6379/0` |
| Docker | `redis://redis:6379/0` |
| Production | `redis://prod-redis-host:6379/0` |

### CORS Configuration

| Environment | CORS_ORIGINS |
|-------------|-------------|
| Local Dev | `http://localhost:3000,http://localhost:8000` |
| Docker | `http://frontend:3000,http://localhost:3000,http://backend:8000` |
| Production | `https://yourdomain.com,https://www.yourdomain.com` |

## 🔐 Security Best Practices

### 1. Never Commit Sensitive Data

```bash
# .gitignore should include:
.env
.env.local
.env.*.local
.env.production
```

### 2. Use Different Keys per Environment

```bash
# Generate secure keys
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
```

### 3. Production Security Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Change database passwords in docker-compose.yml
- [ ] Update `CORS_ORIGINS` to your domain only
- [ ] Set `ENVIRONMENT=production`
- [ ] Add your API keys (OpenAI, Anthropic, etc.)
- [ ] Configure HTTPS/reverse proxy
- [ ] Set up monitoring and logging
- [ ] Configure backups

## 🧪 Testing Environment Configuration

### Test Local Development
```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -c "from app.core.config import settings; print(f'DB Host: {settings.database_url.split(\"@\")[1] if \"@\" in settings.database_url else \"unknown\"}')"
```

### Test Docker Environment
```bash
docker-compose config | grep DATABASE_URL
docker-compose up -d backend
docker-compose logs backend | grep "Database Host"
```

### Test Production Environment
```bash
docker-compose --env-file .env.production config | grep DATABASE_URL
```

## 📋 Environment Variable Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | See formats above |
| `REDIS_URL` | Redis connection string | See formats above |
| `SECRET_KEY` | JWT signing key | Random 32+ character string |
| `CORS_ORIGINS` | Allowed CORS origins | Comma-separated URLs |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Application mode | `development` |
| `OPENAI_API_KEY` | OpenAI API key | (Required for AI features) |
| `ANTHROPIC_API_KEY` | Anthropic API key | (Alternative to OpenAI) |
| `BING_SEARCH_API_KEY` | Bing Search API key | (Required for search) |
| `SMTP_HOST` | SMTP server host | (Required for email) |
| `SMTP_USER` | SMTP username | (Required for email) |
| `SMTP_PASSWORD` | SMTP password | (Required for email) |

## 🔍 Troubleshooting

### Issue: Database Connection Failed

**Symptoms:** `Database is unavailable - sleeping`

**Solutions:**
1. **Local Dev:** Check your local database is running
2. **Docker:** Check `db` container is healthy: `docker-compose ps db`
3. **Production:** Verify external database is accessible

### Issue: Wrong Database Being Used

**Symptoms:** Connected to `localhost` instead of `db`, or vice versa

**Solutions:**
1. Check which environment variables are being used
2. Verify `.env` file vs `docker-compose.yml` settings
3. Remember: Docker environment variables override `.env` file

### Issue: CORS Errors

**Symptoms:** `No 'Access-Control-Allow-Origin' header is present`

**Solutions:**
1. Update `CORS_ORIGINS` to include your frontend URL
2. For local Docker dev, include both `localhost:3000` and `frontend:3000`
3. Restart backend after changing CORS settings

## 📁 File Management

### Files to Keep in Git
- ✅ `.env.example` - Template for developers
- ✅ `.env.local.example` - Reference copy
- ✅ `.env.production` - Template (no secrets)
- ✅ `docker-compose.yml` - Development configuration

### Files to Gitignore
- ❌ `.env` - Local development secrets
- ❌ `.env.local` - Any local overrides
- ❌ `.env.*.local` - Environment-specific local files
- ❌ `.env.production.local` - Production secrets

## 🚀 Deployment Commands

### Local Development
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### Docker Development
```bash
docker-compose up -d --build
```

### Production
```bash
docker-compose --env-file .env.production.local up -d --build
```

## 📚 Additional Resources

- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

---

**Version:** Iteration 1.3 - Production Ready Environment Configuration
**Last Updated:** 2026-08-21
