from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserResponse,
    RegisterResponse,
)
from app.services.auth_service import register_user, login_user, refresh_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(data: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    user, access_token, refresh_token = await register_user(db, data)
    return RegisterResponse(
        message="Account created successfully",
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post("/login", response_model=RegisterResponse)
async def login(data: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    user, access_token, refresh_token = await login_user(db, data)
    return RegisterResponse(
        message="Login successful",
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    access_token, refresh_token = await refresh_access_token(db, data.refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return UserResponse.model_validate(current_user)