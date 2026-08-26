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

# Wait for database to be ready and check/create tables in one go
echo "Waiting for database and ensuring tables exist..."
python -c "
import time
import sys
import os
try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.exc import OperationalError

    # Convert async URL to sync for connection
    db_url = os.getenv('DATABASE_URL', '').replace('aiomysql', 'pymysql')

    # Wait for database
    for i in range(30):
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            print('Database is ready!')
            break
        except OperationalError as e:
            if i < 29:
                time.sleep(2)
            else:
                raise

    # Check if tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    required_tables = ['users', 'campaigns', 'leads']

    missing_tables = [t for t in required_tables if t not in existing_tables]

    if missing_tables:
        print(f'Missing tables: {missing_tables}')
        print('Creating database tables...')
        import app.db.init_db
        app.db.init_db.create_tables()
        print('Database tables created successfully!')
    else:
        print('All required tables exist.')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"

echo "=========================================="
echo "Starting Service"
echo "=========================================="

# Execute the command passed to the container
exec "$@"
