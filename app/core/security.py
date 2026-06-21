from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict, jti: Optional[str] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti or str(uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token_payload(token: str, token_type: str = "access") -> Optional[dict]:
    """
    Decode and validate a JWT. Returns the payload on success, None on any failure.
    Expiry is always enforced.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != token_type:
            return None
        if payload.get("sub") is None:
            return None
        return payload
    except JWTError:
        return None


def decode_token(token: str, token_type: str = "access") -> Optional[int]:
    """
    Decode and validate a JWT. Returns the user_id (int) on success, None on any failure.
    Expiry is always enforced -- use create_refresh_token for long-lived tokens.
    """
    try:
        payload = decode_token_payload(token, token_type=token_type)
        if payload is None:
            return None
        return int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
