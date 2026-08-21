"""
Alembic Environment Configuration

This file is used to configure the Alembic migration environment.
"""
from logging.config import fileConfig
from pathlib import Path
from sys import path

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add parent directory to path so we can import our app modules
path.append(str(Path(__file__).resolve().parents[1]))

# Import our database configuration
from app.core.config import settings
from app.db.base import Base

# Import all models here so they get registered with SQLAlchemy
from app.models.user import User
from app.models.campaign import Campaign
from app.models.lead import Lead

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target_metadata to the Base's metadata for autogenerate support
target_metadata = Base.metadata

# Convert async URL to sync URL for Alembic
# Alembic doesn't support async engines directly
def get_sync_url():
    """Convert async MySQL/MariaDB URL to sync URL for migrations."""
    url = settings.database_url
    if "mysql+aiomysql" in url:
        # Replace aiomysql with pymysql (sync driver)
        sync_url = url.replace("mysql+aiomysql://", "mysql+pymysql://")
        return sync_url
    elif "mariadb+aiomysql" in url:
        # Replace mariadb+aiomysql with mariadb+pymysql (sync driver)
        sync_url = url.replace("mariadb+aiomysql://", "mariadb+pymysql://")
        return sync_url
    return url

sync_url = get_sync_url()
config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate
    a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    # Use sync URL for migrations
    configuration["sqlalchemy.url"] = get_sync_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
