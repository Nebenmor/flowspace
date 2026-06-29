import hashlib
import base64
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _prepare_password(password: str) -> str:
    """Pre-hash password with SHA-256 to bypass bcrypt's 72-byte limit."""
    return base64.b64encode(
        hashlib.sha256(password.encode()).digest()
    ).decode()

def hash_password(password: str) -> str:
    return pwd_context.hash(_prepare_password(password))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_prepare_password(plain_password), hashed_password)

def create_access_token(subject: str, extra_data: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "access",
    }
    if extra_data:
        payload.update(extra_data)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": subject,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])

def hash_token(token: str) -> str:
    """Hash a refresh token for safe storage — we never store raw tokens."""
    return hashlib.sha256(token.encode()).hexdigest()