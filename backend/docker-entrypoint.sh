#!/bin/bash
# =============================================================================
# Docker Entrypoint Script - Backend Container
# =============================================================================
# This script handles database migrations and server startup
# Works with both docker-compose environment variables and .env files

set -e

echo "=========================================="
echo "Starting Backend Container"
echo "=========================================="

# Display database configuration
if [ -n "$DATABASE_URL" ]; then
    # Extract host from DATABASE_URL for display
    DB_HOST=$(echo $DATABASE_URL | grep -oP '@\K[^:]+' || echo "unknown")
    echo "Database Host: $DB_HOST"
    echo "Environment: ${ENVIRONMENT:-development}"
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head || echo "⚠️  Migration failed - will retry on API calls"

# Create necessary directories
echo "Creating required directories..."
mkdir -p /app/logs /app/exports /app/uploads /app/celerybeat

echo "=========================================="
echo "Starting Backend Server"
echo "=========================================="

# Execute the main container command
exec "$@"
