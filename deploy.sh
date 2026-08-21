#!/bin/bash
# =============================================================================
# Docker Deployment Script - AI Lead Generation Platform
# =============================================================================
# Quick deployment script for docker-compose setup

set -e

echo "=========================================="
echo "AI Lead Generation Platform - Deployment"
echo "Iteration 1.3 - Lead Management"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose first: https://docs.docker.com/compose/install/"
    exit 1
fi

# Determine which docker compose command to use
if docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo -e "${GREEN}✓ Docker and Docker Compose found${NC}"

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}Creating .env file from .env.example...${NC}"
    cp backend/.env.example backend/.env
    echo -e "${YELLOW}⚠️  Please update backend/.env with your configuration${NC}"
    echo -e "${YELLOW}⚠️  Especially change SECRET_KEY and passwords!${NC}"
    read -p "Press Enter after updating .env file..."
fi

# Stop existing containers if running
echo "Stopping any existing containers..."
$DOCKER_COMPOSE down 2>/dev/null || true

# Build and start services
echo "Building and starting services..."
$DOCKER_COMPOSE up -d --build

# Wait for services to be healthy
echo "Waiting for services to be ready..."
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if $DOCKER_COMPOSE ps | grep -q "healthy\|Up"; then
        echo -e "${GREEN}✓ Services are running${NC}"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

# Show service status
echo ""
echo "=========================================="
echo "Service Status:"
echo "=========================================="
$DOCKER_COMPOSE ps

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo -e "${GREEN}✓ Frontend:${NC}     http://localhost:3000"
echo -e "${GREEN}✓ Backend API:${NC}  http://localhost:8000"
echo -e "${GREEN}✓ API Docs:${NC}     http://localhost:8000/docs"
echo -e "${GREEN}✓ Flower (Celery):${NC} http://localhost:5555"
echo ""
echo "=========================================="
echo "Next Steps:"
echo "=========================================="
echo "1. Create your first admin user:"
echo "   docker-compose exec backend python -c 'from app.db.base import AsyncSessionLocal; from app.models.user import User; from app.core.security import get_password_hash; import asyncio; async def create_admin(): async with AsyncSessionLocal() as db: user = User(email=\"admin@example.com\", password_hash=get_password_hash(\"admin123\"), name=\"Admin User\", role=\"admin\"); db.add(user); await db.commit(); print(\"Admin user created: admin@example.com / admin123\"); asyncio.run(create_admin())'"
echo ""
echo "2. Login at: http://localhost:3000/login"
echo "3. View logs: docker-compose logs -f"
echo ""
echo -e "${YELLOW}⚠️  Don't forget to update passwords in backend/.env!${NC}"
echo "=========================================="

# Show recent logs
echo ""
echo "Recent logs (press Ctrl+C to exit):"
$DOCKER_COMPOSE logs --tail=20
