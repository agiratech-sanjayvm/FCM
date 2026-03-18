"""
Device token routes — register and manage FCM tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.device_token import DeviceToken
from app.schemas.schemas import TokenRegisterRequest, TokenRegisterResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenRegisterResponse,
    status_code=201,
    summary="Register an FCM device token",
)
async def register_device_token(
    body: TokenRegisterRequest,
    user_id: int = Query(..., description="Authenticated user's ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Register an FCM device token for the authenticated user.

    - Allows multiple tokens per user (multi-browser support).
    - Prevents duplicate tokens via unique constraint.
    - If the same token already exists for this user, returns success without duplicating.

    In production, `user_id` would come from a JWT/OAuth token.
    """
    # Check if this exact token already exists
    stmt = select(DeviceToken).where(DeviceToken.token == body.token)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        if existing.user_id == user_id:
            logger.info(
                "Device token already registered | user_id=%d | token=%s...",
                user_id, body.token[:20],
            )
            return TokenRegisterResponse(
                message="Token already registered",
                user_id=user_id,
                token=body.token,
            )
        else:
            # Token belongs to a different user — reassign it
            # (e.g., user logged out on that browser and another logged in)
            existing.user_id = user_id
            await db.commit()
            logger.info(
                "Device token reassigned | user_id=%d | token=%s...",
                user_id, body.token[:20],
            )
            return TokenRegisterResponse(
                message="Token reassigned to current user",
                user_id=user_id,
                token=body.token,
            )

    # Save new token
    device_token = DeviceToken(user_id=user_id, token=body.token)
    db.add(device_token)
    await db.commit()

    logger.info(
        "Device token registered | user_id=%d | token=%s...",
        user_id, body.token[:20],
    )
    return TokenRegisterResponse(
        message="Token registered successfully",
        user_id=user_id,
        token=body.token,
    )
