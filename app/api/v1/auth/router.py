from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User
from app.schemas.schemas import UserCreate, UserLogin, UserResponse, Token, RefreshRequest
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.core.logging import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)) -> UserResponse:
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
        logger.warning(f"Registration attempt for existing email: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"New user registered: {new_user.id} - {new_user.email}")
    return new_user


@router.post("/login", response_model=Token)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)) -> Token:
    result = await db.execute(select(User).where(User.email == user.email))
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        logger.warning(f"Failed login attempt for email: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    payload = {"sub": str(db_user.id)}
    logger.info(f"User {db_user.id} logged in successfully")

    return Token(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshRequest) -> Token:
    """
    Accept a valid (non-expired) refresh token and return a new access/refresh
    token pair (token rotation). The refresh token has a 7-day TTL configured
    in REFRESH_TOKEN_EXPIRE_DAYS. Access tokens cannot be used here — the
    token type claim is validated.
    """
    user_id = decode_token(request.refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    payload = {"sub": str(user_id)}
    logger.info(f"Token rotated for user {user_id}")

    return Token(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        token_type="bearer",
    )
