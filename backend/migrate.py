#!/usr/bin/env python
"""
=============================================================================
Post-Deployment Migration Script - AI Lead Generation Platform
=============================================================================
This script handles database setup after docker-compose deployment.

Run after deployment:
    docker-compose exec backend python migrate.py
    or
    python migrate.py (for local development)

Features:
- Checks database connectivity
- Creates alembic_version table if needed
- Stamps base version and runs migrations
- Creates optional admin user
- Verifies table creation
"""

import asyncio
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))


def print_header(message: str):
    """Print formatted header."""
    print(f"\n{'='*60}")
    print(f"  {message}")
    print(f"{'='*60}\n")


def print_success(message: str):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"❌ {message}")


def print_info(message: str):
    """Print info message."""
    print(f"ℹ️  {message}")


async def check_database_connection():
    """Check if database connection works."""
    print_header("Checking Database Connection")
    from sqlalchemy import text
    from app.db.base import engine

    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print_success("Database connection successful")
            return True
    except Exception as e:
        print_error(f"Database connection failed: {e}")
        return False


async def create_alembic_version_table():
    """Create alembic_version table if it doesn't exist."""
    print_header("Creating Alembic Version Table")
    from sqlalchemy import text
    from app.db.base import engine

    try:
        async with engine.begin() as conn:
            # Check if table exists
            result = await conn.execute(text("""
                SELECT COUNT(*) as count FROM information_schema.tables
                WHERE table_schema = DATABASE() AND table_name = 'alembic_version'
            """))
            table_exists = result.scalar() > 0

            if table_exists:
                print_info("alembic_version table already exists")
            else:
                # Create the table
                await conn.execute(text("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                """))
                print_success("Created alembic_version table")

            return True
    except Exception as e:
        print_error(f"Failed to create alembic_version table: {e}")
        return False


async def stamp_base_version():
    """Stamp database with base version."""
    print_header("Stamping Base Version")
    from alembic.config import Config
    from alembic import command

    try:
        config = Config("alembic.ini")
        command.stamp(config, "base")
        print_success("Stamped database with base version")
        return True
    except Exception as e:
        print_error(f"Failed to stamp base version: {e}")
        return False


async def run_migrations():
    """Run all pending migrations."""
    print_header("Running Database Migrations")
    from alembic.config import Config
    from alembic import command
    from alembic.runtime.environment import EnvironmentContext
    from app.core.config import settings
    from sqlalchemy import create_engine
    import asyncio

    def get_sync_url():
        """Convert async URL to sync URL for Alembic."""
        url = settings.database_url
        if "mysql+aiomysql" in url:
            return url.replace("mysql+aiomysql://", "mysql+pymysql://")
        elif "mariadb+aiomysql" in url:
            return url.replace("mariadb+aiomysql://", "mariadb+pymysql://")
        return url

    try:
        config = Config("alembic.ini")
        sync_url = get_sync_url()
        config.set_main_option("sqlalchemy.url", sync_url)

        # Create sync engine for Alembic
        sync_engine = create_engine(sync_url)

        # Check current version
        def check_version(rev, context):
            if rev:
                print_info(f"Current revision: {rev}")
            else:
                print_info("No current revision - database is new")
            return []

        with EnvironmentContext(config):
            from alembic.script import ScriptDirectory
            script = ScriptDirectory.from_config(config)

            # Run upgrade
            def upgrade(rev, context):
                print("Running migration upgrade...")
                return script._upgrade_revs("head", rev)

            with sync_engine.begin() as connection:
                config.attributes['connection'] = connection
                command.upgrade(config, "head")

        # Verify migration completed
        def get_current_rev(rev, context):
            if rev:
                print_success(f"Migrations completed. Current revision: {rev}")
            else:
                print_info("No migrations to run")
            return []

        with sync_engine.begin() as connection:
            from alembic.runtime.migration import MigrationContext
            migration_context = MigrationContext(config.configure(connection=connection))
            final_rev = migration_context.get_current_revision()

        if final_rev:
            print_success(f"Migrations completed. Current revision: {final_rev}")
        else:
            print_info("No migrations were run")

        return True

    except Exception as e:
        print_error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_tables():
    """Verify that all required tables exist."""
    print_header("Verifying Table Creation")
    from sqlalchemy import text
    from app.db.base import engine

    required_tables = ['users', 'campaigns', 'leads', 'alembic_version']

    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = DATABASE()
            """))
            existing_tables = {row[0] for row in result}

            missing_tables = set(required_tables) - existing_tables

            if missing_tables:
                print_error(f"Missing tables: {missing_tables}")
                return False
            else:
                print_success(f"All required tables exist: {required_tables}")
                return True

    except Exception as e:
        print_error(f"Failed to verify tables: {e}")
        return False


async def create_admin_user():
    """Create initial admin user if none exists."""
    print_header("Creating Admin User")

    from app.db.base import AsyncSessionLocal
    from app.models.user import User
    from app.core.security import get_password_hash
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            # Check if any users exist
            result = await db.execute(select(User).limit(1))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print_info(f"Admin user already exists: {existing_user.email}")
                return True

            # Create admin user
            admin_user = User(
                email="admin@smartreach.ai",
                password_hash=get_password_hash("admin123"),
                name="System Administrator",
                role="admin"
            )
            db.add(admin_user)
            await db.commit()

            print_success("Created admin user:")
            print("   Email: admin@smartreach.ai")
            print("   Password: admin123")
            print("   ⚠️  CHANGE THIS PASSWORD AFTER FIRST LOGIN!")

            return True

    except Exception as e:
        print_error(f"Failed to create admin user: {e}")
        return False


async def main():
    """Main migration workflow."""
    print_header("🚀 AI Lead Generation Platform - Database Setup")
    print("This script will set up your database after deployment.\n")

    # Step 1: Check database connection
    if not await check_database_connection():
        print_error("Cannot proceed without database connection")
        sys.exit(1)

    # Step 2: Create alembic_version table
    await create_alembic_version_table()

    # Step 3: Stamp base version if needed
    await stamp_base_version()

    # Step 4: Run migrations
    if not await run_migrations():
        print_error("Migration failed - cannot proceed")
        sys.exit(1)

    # Step 5: Verify tables
    if not await verify_tables():
        print_error("Table verification failed")
        sys.exit(1)

    # Step 6: Create admin user
    await create_admin_user()

    # Final success message
    print_header("✅ Database Setup Complete!")
    print("Your database is ready to use.")
    print("\nNext steps:")
    print("1. Login to the application: http://localhost:3000/login")
    print("2. Use admin@smartreach.ai / admin123 for first login")
    print("3. CHANGE THE ADMIN PASSWORD IMMEDIATELY!")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
