import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException, status
from app.db.models.collaboration import TaskActivity
from app.db.models.task import Task
from app.db.models.user import User
from app.services.workspace_service import (
    _get_org_or_404,
    _get_workspace_or_404,
    _require_workspace_member,
)


async def get_task_activity(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    # Verify task exists and belongs to workspace
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Base query
    query = select(TaskActivity).where(TaskActivity.task_id == task_id)

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination — most recent first
    offset = (page - 1) * page_size
    query = (
        query.order_by(TaskActivity.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    activities = list(result.scalars().all())

    return {
        "items": activities,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": (offset + page_size) < total,
    }


async def get_workspace_activity(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """
    Returns a feed of all activity across all tasks in a workspace.
    Useful for a workspace-level activity timeline.
    """
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    # Join through tasks to scope to workspace
    query = (
        select(TaskActivity)
        .join(Task, Task.id == TaskActivity.task_id)
        .where(Task.workspace_id == workspace.id)
    )

    # Count total
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    # Apply pagination — most recent first
    offset = (page - 1) * page_size
    query = (
        query.order_by(TaskActivity.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    activities = list(result.scalars().all())

    return {
        "items": activities,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": (offset + page_size) < total,
    }


async def get_user_activity(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    target_user_id: uuid.UUID,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Returns all activity performed by a specific user in a workspace.
    Useful for team productivity views.
    """
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    # Verify target user is a workspace member
    await _require_workspace_member(db, workspace.id, target_user_id)

    query = (
        select(TaskActivity)
        .join(Task, Task.id == TaskActivity.task_id)
        .where(
            Task.workspace_id == workspace.id,
            TaskActivity.actor_id == target_user_id,
        )
    )

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar()

    offset = (page - 1) * page_size
    query = (
        query.order_by(TaskActivity.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    activities = list(result.scalars().all())

    return {
        "items": activities,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_next": (offset + page_size) < total,
    }