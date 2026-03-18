
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.device_token import DeviceToken
from app.models.user import User

async def check_tokens():
    async with AsyncSessionLocal() as db:
        stmt = select(DeviceToken, User.email).join(User, DeviceToken.user_id == User.id)
        result = await db.execute(stmt)
        tokens = result.fetchall()
        print(f"Total tokens found: {len(tokens)}")
        for dt, email in tokens:
            print(f"User: {email} | Token Prefix: {dt.token[:20]}... | Added: {dt.created_at}")

if __name__ == "__main__":
    asyncio.run(check_tokens())
