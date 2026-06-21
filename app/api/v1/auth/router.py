from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.logging import logger
from app.core.refresh_tokens import refresh_token_store
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_token_payload,
    get_password_hash,
    verify_password,
)
from app.db.database import get_db
from app.db.models import User
from app.schemas.schemas import RefreshRequest, Token, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def issue_token_pair(user_id: int) -> Token:
    payload = {"sub": str(user_id)}
    refresh_jti = str(uuid4())
    refresh_token = create_refresh_token(payload, jti=refresh_jti)

    try:
        await refresh_token_store.store(refresh_jti, user_id)
    except RedisError:
        logger.exception(f"Unable to store refresh token for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to issue refresh token",
        )

    return Token(
        access_token=create_access_token(payload),
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    result = await db.execute(select(User).where(User.email == user.email))
    if result.scalar_one_or_none():
        logger.warning(f"Registration attempt for existing email: {user.email[:3]}***")
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

    logger.info(f"New user registered: {new_user.id}")
    return new_user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(
    request: Request,
    user: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    result = await db.execute(select(User).where(User.email == user.email))
    db_user = result.scalar_one_or_none()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        logger.warning(f"Failed login attempt for email: {user.email[:3]}***")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    logger.info(f"User {db_user.id} logged in successfully")
    return await issue_token_pair(db_user.id)


@router.post("/refresh", response_model=Token)
@limiter.limit("20/minute")
async def refresh_token(request: Request, body: RefreshRequest) -> Token:
    """
    Accept a valid refresh token and return a new access/refresh token pair.
    The old refresh token is invalidated in Redis, so replaying it after a
    successful refresh is rejected.
    """
    payload = decode_token_payload(body.refresh_token, token_type="refresh")
    if not payload or not payload.get("jti"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = decode_token(body.refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    try:
        token_is_active = await refresh_token_store.consume(payload["jti"], user_id)
    except RedisError:
        logger.exception(f"Unable to verify refresh token for user {user_id}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify refresh token",
        )

    if not token_is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    logger.info(f"Token rotated for user {user_id}")
    return await issue_token_pair(user_id)
