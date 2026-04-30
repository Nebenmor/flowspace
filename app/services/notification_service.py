import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from fastapi import HTTPException, status
from app.db.models.system import Notification
from app.db.models.user import User


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str | None = None,
    meta: dict | None = None,
) -> Notification:
    """
    Internal helper — called from other services when events happen.
    e.g. task assigned, invitation received, comment added.
    """
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        meta=meta,
    )
    db.add(notification)
    return notification


async def list_notifications(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
) -> dict:
    query = select(Notification).where(
        Notification.user_id == current_user.id
    )

    if unread_only:
        query = query.where(Notification.is_read == False)

    # Count total and unread
    total_result = await db.execute(
        select(func.count()).select_from(
            select(Notification).where(
                Notification.user_id == current_user.id
            ).subquery()
        )
    )
    total = total_result.scalar()

    unread_result = await db.execute(
        select(func.count()).select_from(
            select(Notification).where(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            ).subquery()
        )
    )
    unread_count = unread_result.scalar()

    # Apply pagination — most recent first
    offset = (page - 1) * page_size
    query = (
        query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    notifications = list(result.scalars().all())

    return {
        "items": notifications,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
        "has_next": (offset + page_size) < total,
    }


async def mark_as_read(
    db: AsyncSession,
    notification_id: uuid.UUID,
    current_user: User,
) -> Notification:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    notification.is_read = True
    return notification


async def mark_all_as_read(
    db: AsyncSession,
    current_user: User,
) -> dict:
    result = await db.execute(
        select(func.count()).select_from(
            select(Notification).where(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
            ).subquery()
        )
    )
    unread_count = result.scalar()

    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )

    return {"marked_read": unread_count}


async def delete_notification(
    db: AsyncSession,
    notification_id: uuid.UUID,
    current_user: User,
) -> None:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    await db.delete(notification)