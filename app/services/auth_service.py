import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.db.models.user import User, RefreshToken
from app.schemas.auth import UserRegisterRequest, UserLoginRequest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
    decode_token,
)
from jose import JWTError


async def register_user(db: AsyncSession, data: UserRegisterRequest):
    # Check email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Check username already exists
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken",
        )

    # Create user
    user = User(
        email=data.email,
        username=data.username,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.flush()  # flush to get the user.id without committing yet

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Store hashed refresh token
    from app.core.config import settings
    from datetime import timedelta
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    ))

    return user, access_token, refresh_token


async def login_user(db: AsyncSession, data: UserLoginRequest):
    # Find user by email
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    # Deliberately vague error — never confirm whether email exists
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )

    # Generate new tokens
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(subject=str(user.id))

    # Store hashed refresh token
    from app.core.config import settings
    from datetime import timedelta
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    ))

    return user, access_token, refresh_token


async def refresh_access_token(db: AsyncSession, refresh_token: str):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verify token exists in DB and is not revoked
    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    stored_token = result.scalar_one_or_none()
    if not stored_token:
        raise credentials_exception

    # Rotate — revoke old token, issue new ones
    stored_token.revoked_at = datetime.now(timezone.utc)

    new_access_token = create_access_token(subject=user_id)
    new_refresh_token = create_refresh_token(subject=user_id)

    from app.core.config import settings
    from datetime import timedelta
    db.add(RefreshToken(
        user_id=uuid.UUID(user_id),
        token_hash=hash_token(new_refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        ),
    ))

    return new_access_token, new_refresh_token