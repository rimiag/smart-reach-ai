#!/bin/bash
# =============================================================================
# Docker Entrypoint Script for Backend
# =============================================================================

set -e

echo "=========================================="
echo "Starting Backend Container"
echo "=========================================="

# Display environment info
echo "Environment: ${ENVIRONMENT:-development}"

# Wait for database to be ready using Python
echo "Waiting for database to be ready..."
python -c "
import time
import sys
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
    # Convert async URL to sync for connection check
    db_url = '${DATABASE_URL}'.replace('aiomysql', 'pymysql')
    for i in range(30):
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print('Database is ready!')
            sys.exit(0)
        except OperationalError:
            time.sleep(2)
    print('Database connection timeout')
    sys.exit(1)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head || {
    echo "Alembic migration failed, trying direct table creation..."
    python -m app.db.init_db
}

echo "=========================================="
echo "Starting Service"
echo "=========================================="

# Execute the command passed to the container
exec "$@"
