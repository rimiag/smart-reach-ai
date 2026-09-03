"""
Database Initialization Script

Creates all database tables. Run this after starting the database.
"""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.models.research_result import ResearchResult
from app.models.user import User


async def create_tables():
    """Create all database tables."""
    engine = create_async_engine(settings.database_url, echo=True)

    # Import all models to ensure they're registered with Base
    from app.models import Campaign, Lead, ResearchResult, User  # noqa: F401

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("Database tables created successfully!")  # ASCII-only: Windows cp1252 consoles


if __name__ == "__main__":
    asyncio.run(create_tables())
