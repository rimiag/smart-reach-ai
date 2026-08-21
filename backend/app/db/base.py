"""
Database Base Configuration

Sets up SQLAlchemy base, engine, and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# -----------------------------------------------------------------------------
# Async Engine
# -----------------------------------------------------------------------------
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_pre_ping=True,
    echo=settings.environment == "development",
)


# -----------------------------------------------------------------------------
# Session Factory
# -----------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# -----------------------------------------------------------------------------
# Base Class for Models
# -----------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# -----------------------------------------------------------------------------
# Dependency for FastAPI
# -----------------------------------------------------------------------------
async def get_db() -> AsyncSession:
    """
    Get database session for use in FastAPI endpoints.

    Yields:
        AsyncSession: Database session

    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
