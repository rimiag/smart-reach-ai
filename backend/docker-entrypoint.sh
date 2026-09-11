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

# Wait for database to be ready and check/create tables in one go.
# Services that don't need the database (e.g. flower) may run without
# DATABASE_URL - skip the check instead of exiting.
if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL not set - skipping database check for this service."
else
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

    # Check if tables exist. Derive the expected list from the ORM metadata
    # (not a hardcoded list) so newly added models are checked automatically.
    import app.models  # noqa: F401 - these imports register all models on Base
    from app.db.base import Base

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    required_tables = sorted(Base.metadata.tables.keys())

    missing_tables = [t for t in required_tables if t not in existing_tables]

    if missing_tables:
        print(f'Missing tables: {missing_tables}')
        print('Creating database tables...')
        import asyncio
        import app.db.init_db
        asyncio.run(app.db.init_db.create_tables())
        # Verify the tables actually exist now - create_tables is async and a
        # silent no-op would otherwise boot an API that 500s on every query.
        still_missing = [t for t in required_tables if t not in inspect(engine).get_table_names()]
        if still_missing:
            print(f'ERROR: tables still missing after create_tables: {still_missing}')
            sys.exit(1)
        print('Database tables created successfully!')
    else:
        print('All required tables exist.')

except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
"
fi

echo "=========================================="
echo "Starting Service"
echo "=========================================="

# Execute the command passed to the container
exec "$@"
