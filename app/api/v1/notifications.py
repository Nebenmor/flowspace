import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.notification import NotificationResponse, NotificationListResponse
from app.services.notification_service import (
    list_notifications,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_notifications(
        db, current_user, page, page_size, unread_only
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def read_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await mark_as_read(db, notification_id, current_user)


@router.patch("/read-all", response_model=dict)
async def read_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await mark_all_as_read(db, current_user)


@router.delete("/{notification_id}", status_code=204)
async def remove_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_notification(db, notification_id, current_user)