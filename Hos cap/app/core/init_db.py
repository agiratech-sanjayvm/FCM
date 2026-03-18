"""
Database initialization script.
Creates all tables using the async engine.

Usage:
    python -m app.core.init_db          # Create tables (skip existing)
    python -m app.core.init_db --reset  # Drop all + recreate
"""

import sys
import asyncio
from app.core.database import engine, Base
from app.core.logging import logger

# Import all models so Base.metadata knows about them
from app.models.user import User  # noqa: F401
from app.models.appointment import Appointment  # noqa: F401
from app.models.device_token import DeviceToken  # noqa: F401
from app.models.notification import Notification  # noqa: F401


async def init_db(reset: bool = False):
    """Create all database tables. If reset=True, drop everything first."""
    async with engine.begin() as conn:
        if reset:
            logger.info("Dropping all existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("All tables dropped")

        logger.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def drop_db():
    """Drop all database tables (use with caution)."""
    logger.info("Dropping database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    if reset:
        logger.info("Reset flag detected — will drop and recreate all tables")
    asyncio.run(init_db(reset=reset))

