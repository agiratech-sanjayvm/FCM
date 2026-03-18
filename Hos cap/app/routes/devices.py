"""
Device token routes — register and manage FCM tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.models.device_token import DeviceToken
from app.models.user import User
from app.routes.auth import get_current_user
from app.schemas.schemas import TokenRegisterRequest, TokenRegisterResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an FCM device token",
)
async def register_device_token(
    request: Request,
    body: TokenRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register an FCM device token for the authenticated user.
    Allows multiple tokens per user (multi-browser support).
    Also stores the user's IP Address for audit tracking.
    """
    user_id = current_user.id
    client_ip = request.client.host if request.client else None
    
    # Check if this exact token already exists
    stmt = select(DeviceToken).where(DeviceToken.token == body.token)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        if existing.user_id == user_id:
            # Update their IP quietly just in case it modified
            if existing.ip_address != client_ip:
                existing.ip_address = client_ip
                await db.commit()
            
            logger.info(
                "Device token already registered | user_id=%d | token=%s... | ip=%s",
                user_id, body.token[:20], client_ip
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
            existing.ip_address = client_ip
            await db.commit()
            logger.info(
                "Device token reassigned | user_id=%d | token=%s... | ip=%s",
                user_id, body.token[:20], client_ip
            )
            return TokenRegisterResponse(
                message="Token reassigned to current user",
                user_id=user_id,
                token=body.token,
            )

    # Save new token
    device_token = DeviceToken(user_id=user_id, token=body.token, ip_address=client_ip)
    db.add(device_token)
    await db.commit()

    logger.info(
        "Device token registered | user_id=%d | token=%s... | ip=%s",
        user_id, body.token[:20], client_ip
    )
    return TokenRegisterResponse(
        message="Token registered successfully",
        user_id=user_id,
        token=body.token,
    )
