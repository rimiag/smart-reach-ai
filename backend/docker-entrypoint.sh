#!/bin/bash
# =============================================================================
# Docker Entrypoint Script - Backend Container
# =============================================================================
# This script handles database migrations and server startup
# Ensures migrations run before the application starts

set -e

echo "=========================================="
echo "Starting Backend Container"
echo "=========================================="

# Parse DATABASE_URL to get connection components
# Expected format: mariadb+aiomysql://user:password@host:port/database
if [ -n "$DATABASE_URL" ]; then
    # Extract components from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | grep -oP '@\K[^:]+(?=:)' || echo "db")
    DB_PORT=$(echo $DATABASE_URL | grep -oP ':[0-9]+/' | grep -oP '[0-9]+' || echo "3306")
    DB_USER=$(echo $DATABASE_URL | grep -oP '://\K[^:]+(?=:)' || echo "leadgen_user")
    DB_PASSWORD=$(echo $DATABASE_URL | grep -oP ':\K[^@]+(?=@)' || echo "leadgen_pass")
    DB_NAME=$(echo $DATABASE_URL | grep -oP '/\K[^?]+$' || echo "leadgen_db")

    echo "Database config: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
fi

# Wait for database to be ready
echo "Waiting for database to be ready..."
until python -c "import pymysql; pymysql.connect(host='$DB_HOST', port=$DB_PORT, user='$DB_USER', password='$DB_PASSWORD', database='$DB_NAME')" 2>/dev/null; do
    echo "Database is unavailable - sleeping"
    sleep 2
done

echo "Database is ready!"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Create necessary directories
echo "Creating required directories..."
mkdir -p /app/logs /app/exports /app/uploads /app/celerybeat

echo "=========================================="
echo "Starting Backend Server"
echo "=========================================="

# Execute the main container command
exec "$@"
