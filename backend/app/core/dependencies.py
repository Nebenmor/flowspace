from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.session import AsyncSessionLocal
from app.core.security import decode_token
from jose import JWTError
from fastapi import WebSocket, WebSocketException
from starlette import status as ws_status

bearer_scheme = HTTPBearer()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from app.db.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated",
        )
    return user

async def get_current_user_ws(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket-specific auth dependency.
    Token is passed as a query parameter since WS can't use headers.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise WebSocketException(code=ws_status.WS_1008_POLICY_VIOLATION)
        user_id: str = payload.get("sub")
        if not user_id:
            raise WebSocketException(code=ws_status.WS_1008_POLICY_VIOLATION)
    except JWTError:
        raise WebSocketException(code=ws_status.WS_1008_POLICY_VIOLATION)

    from app.db.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise WebSocketException(code=ws_status.WS_1008_POLICY_VIOLATION)

    return user