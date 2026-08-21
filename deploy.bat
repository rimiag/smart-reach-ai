@echo off
REM =============================================================================
REM Docker Deployment Script - AI Lead Generation Platform (Windows)
REM =============================================================================
REM Quick deployment script for docker-compose setup

echo ==========================================
echo AI Lead Generation Platform - Deployment
echo Iteration 1.3 - Lead Management
echo ==========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running or not installed
    echo Please start Docker Desktop first
    pause
    exit /b 1
)

echo [OK] Docker is running

REM Check if .env exists
if not exist "backend\.env" (
    echo Creating .env file from .env.example...
    copy backend\.env.example backend\.env
    echo.
    echo [WARNING] Please update backend\.env with your configuration
    echo [WARNING] Especially change SECRET_KEY and passwords!
    echo.
    pause
)

REM Stop existing containers if running
echo Stopping any existing containers...
docker compose down 2>nul

REM Build and start services
echo Building and starting services...
docker compose up -d --build

REM Wait for services
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Show service status
echo.
echo ==========================================
echo Service Status:
echo ==========================================
docker compose ps

echo.
echo ==========================================
echo Deployment Complete!
echo ==========================================
echo [OK] Frontend:     http://localhost:3000
echo [OK] Backend API:  http://localhost:8000
echo [OK] API Docs:     http://localhost:8000/docs
echo [OK] Flower:       http://localhost:5555
echo.
echo ==========================================
echo Next Steps:
echo ==========================================
echo 1. Create your first admin user (run in terminal):
echo    docker compose exec backend python -c "from app.db.base import AsyncSessionLocal; from app.models.user import User; from app.core.security import get_password_hash; import asyncio
echo    async def create_admin():
echo      async with AsyncSessionLocal() as db:
echo        user = User(email='admin@example.com', password_hash=get_password_hash('admin123'), name='Admin User', role='admin')
echo        db.add(user)
echo        await db.commit()
echo        print('Admin user created: admin@example.com / admin123')
echo    asyncio.run(create_admin())"
echo.
echo 2. Login at: http://localhost:3000/login
echo 3. View logs: docker compose logs -f
echo.
echo [WARNING] Don't forget to update passwords in backend\.env!
echo ==========================================
echo.
echo Showing recent logs (Ctrl+C to exit):
docker compose logs --tail=20

pause
