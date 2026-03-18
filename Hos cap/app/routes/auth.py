"""
Auth routes — simple login for demo purposes.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.config import settings
from app.core.security import verify_password, create_access_token, ALGORITHM, limiter
from app.models.user import User
from app.schemas.schemas import LoginRequest, LoginResponse


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency to get the currently authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    return user


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
)
@limiter.limit("1000/minute")  # Safe limit for massive hospitals where the entire staff shares 1 NAT IP
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login endpoint — validates email + hashed password.
    Returns JWT access token and user info.
    """
    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("User logged in | user_id=%d | role=%s", user.id, user.role)

    # Create access token
    access_token = create_access_token(data={"sub": user.email})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
    )
