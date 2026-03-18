"""
Seed script — creates demo users for testing.

Usage:
    python -m app.core.seed
"""

import asyncio
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.logging import logger
from app.models.user import User, UserRole


DEMO_USERS = [
    {"name": "Alice Patient", "email": "alice@example.com", "role": UserRole.USER},
    {"name": "Bob Patient", "email": "bob@example.com", "role": UserRole.USER},
    {"name": "Dr. Smith", "email": "drsmith@example.com", "role": UserRole.DOCTOR},
    {"name": "Dr. Jones", "email": "drjones@example.com", "role": UserRole.DOCTOR},
]


async def seed():
    async with AsyncSessionLocal() as db:
        for user_data in DEMO_USERS:
            # Check existence
            stmt = select(User).where(User.email == user_data["email"])
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is None:
                db.add(User(**user_data))
                logger.info("Seeded user: %s (%s)", user_data["name"], user_data["role"])
            else:
                logger.info("User already exists: %s", user_data["email"])
        await db.commit()
    logger.info("Seeding complete")


if __name__ == "__main__":
    asyncio.run(seed())
