# Docker Compose Deployment Guide
# AI Lead Generation Platform - Iteration 1.3

## 📋 Prerequisites

Before deploying, ensure you have:
- Docker installed (v20.10+)
- Docker Compose installed (v2.0+)
- Git installed
- At least 4GB RAM available
- Ports 3000, 8000, 3306, 6379, 5555 available

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd smart-reach-ai
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp backend/.env.example backend/.env
```

**Important:** Update these values in `backend/.env`:
```env
# Change these in production!
SECRET_KEY=your-secret-key-change-in-production
MYSQL_ROOT_PASSWORD=root_password_change_in_production

# Database (already configured for docker)
DATABASE_URL=mariadb+aiomysql://leadgen_user:leadgen_pass@db:3306/leadgen_db

# Redis (already configured for docker)
REDIS_URL=redis://redis:6379/0

# API Keys (add your own)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
BING_SEARCH_API_KEY=your-bing-key
```

### 3. Start All Services

```bash
# Start all services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Flower (Celery Monitor)**: http://localhost:5555

### 5. Create First User

```bash
# Run the user creation script
docker-compose exec backend python -c "
from app.db.base import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import asyncio

async def create_admin():
    async with AsyncSessionLocal() as db:
        user = User(
            email='admin@example.com',
            password_hash=get_password_hash('admin123'),
            name='Admin User',
            role='admin'
        )
        db.add(user)
        await db.commit()
        print('Admin user created: admin@example.com / admin123')

asyncio.run(create_admin())
"
```

## 🔄 Database Migrations

Migrations run automatically on container startup. To run them manually:

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Check migration status
docker-compose exec backend alembic current

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Rollback migrations
docker-compose exec backend alembic downgrade -1
```

## 🛠️ Common Commands

### Service Management

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data!)
docker-compose down -v

# Restart specific service
docker-compose restart backend

# Rebuild and start (after code changes)
docker-compose up -d --build

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f worker
```

### Database Operations

```bash
# Access database shell
docker-compose exec db mysql -uleadgen_user -pleadgen_pass leadgen_db

# Backup database
docker-compose exec db mysqldump -uleadgen_user -pleadgen_pass leadgen_db > backup.sql

# Restore database
docker-compose exec -T db mysql -uleadgen_user -pleadgen_pass leadgen_db < backup.sql
```

### Cache Operations

```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Flush all cache
docker-compose exec redis redis-cli FLUSHALL
```

## 📊 Monitoring

### Check Service Health

```bash
# Check all services
docker-compose ps

# Backend health check
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000
```

### View Logs

```bash
# All logs
docker-compose logs

# Specific service logs
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f scheduler
docker-compose logs -f flower
```

### Celery Task Monitoring

Visit http://localhost:5555 for:
- Task execution history
- Worker status
- Task queue monitoring

## 🔧 Troubleshooting

### Services Not Starting

```bash
# Check port conflicts
netstat -tuln | grep -E '3000|8000|3306|6379|5555'

# Clean restart
docker-compose down
docker-compose up -d --force-recreate
```

### Database Connection Issues

```bash
# Check database is running
docker-compose ps db

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Migration Issues

```bash
# Reset database (⚠️ deletes all data)
docker-compose down -v
docker-compose up -d db
# Wait for db to start, then:
docker-compose up -d backend
```

### Frontend Build Issues

```bash
# Clear Next.js cache
docker-compose exec frontend rm -rf .next

# Rebuild frontend
docker-compose up -d --build frontend
```

## 🌐 Production Deployment

### Security Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY
- [ ] Set ENVIRONMENT=production
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS
- [ ] Use separate database credentials
- [ ] Set up proper backups
- [ ] Configure rate limiting
- [ ] Enable monitoring

### Environment Variables for Production

Update these in `backend/.env`:

```env
ENVIRONMENT=production
SECRET_KEY=<generate-secure-key>
MYSQL_ROOT_PASSWORD=<strong-password>
MYSQL_PASSWORD=<strong-password>

# Update CORS origins for your domain
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Add your API keys
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
# etc...
```

### Reverse Proxy (Nginx)

Example nginx configuration for HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Flower (optional - protect with auth)
    location /flower/ {
        proxy_pass http://localhost:5555;
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
```

## 📦 Container Images

### Backend Image
- Base: Python 3.11-slim
- Includes: FastAPI, SQLAlchemy, Celery, Redis client
- Port: 8000

### Frontend Image
- Base: Node 20-alpine
- Includes: Next.js, React
- Port: 3000

### Database
- MariaDB 10.1.48
- Port: 3306
- Data persisted in Docker volume

### Redis
- Redis 7-alpine
- Port: 6379
- Data persisted in Docker volume

## 🔐 Default Credentials

⚠️ **CHANGE THESE IN PRODUCTION!**

| Service | Username | Password |
|---------|----------|----------|
| Database (root) | root | root_password_change_in_production |
| Database (app) | leadgen_user | leadgen_pass |
| First Admin User | admin@example.com | admin123 |

## 📝 Notes

- Database migrations run automatically on backend startup
- Worker processes handle background tasks
- Scheduler handles recurring tasks
- All data persists in Docker volumes
- Logs are written to `/app/logs` inside containers

## 🆘 Support

For issues or questions:
1. Check logs: `docker-compose logs -f [service]`
2. Verify configuration in `.env` files
3. Check service status: `docker-compose ps`
4. Review this guide's troubleshooting section

---

**Version**: Iteration 1.3 - Lead Management
**Last Updated**: 2026-08-21
