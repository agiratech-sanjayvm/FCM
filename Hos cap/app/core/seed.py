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

from app.core.security import get_password_hash


DEMO_USERS = [
    {"name": "Alice Patient", "email": "alice@example.com", "role": UserRole.USER, "password": "password123"},
    {"name": "Bob Patient", "email": "bob@example.com", "role": UserRole.USER, "password": "password123"},
    {"name": "Bobson Patient", "email": "bobson@example.com", "role": UserRole.USER, "password": "password123"},
    {"name": "Robson Patient", "email": "robson@example.com", "role": UserRole.USER, "password": "password123"},
    {"name": "Robin Patient", "email": "robin@example.com", "role": UserRole.USER, "password": "password123"},
    {"name": "Smithie Patient", "email": "smithie@example.com", "role": UserRole.USER, "password": "password123"},
    {"name": "Annie Patient", "email": "annie@example.com", "role": UserRole.USER, "password": "password123"},
    {"name": "Dr. Smith", "email": "drsmith@example.com", "role": UserRole.DOCTOR, "password": "doctor123"},
    {"name": "Dr. Jones", "email": "drjones@example.com", "role": UserRole.DOCTOR, "password": "doctor123"},
    {"name": "Dr. Jon", "email": "drjon@example.com", "role": UserRole.DOCTOR, "password": "doctor123"},
    {"name": "Dr. Jo", "email": "drjo@example.com", "role": UserRole.DOCTOR, "password": "doctor123"},
    {"name": "Dr. Lee", "email": "drlee@example.com", "role": UserRole.DOCTOR, "password": "doctor123"},
]


async def seed():
    async with AsyncSessionLocal() as db:
        for user_data in DEMO_USERS:
            # Check existence
            stmt = select(User).where(User.email == user_data["email"])
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is None:
                # Prepare hashed password
                password = user_data.pop("password")
                user_data["password_hash"] = get_password_hash(password)
                db.add(User(**user_data))
                logger.info("Seeded user: %s (%s)", user_data["name"], user_data["role"])
            else:
                logger.info("User already exists: %s", user_data["email"])
        await db.commit()
    logger.info("Seeding complete")


if __name__ == "__main__":
    asyncio.run(seed())
