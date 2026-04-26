import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException, status
from app.db.models.task import Label, TaskLabel, Task
from app.db.models.user import User
from app.schemas.label import LabelCreateRequest
from app.services.workspace_service import (
    _get_org_or_404,
    _get_workspace_or_404,
    _require_workspace_member,
    _require_workspace_role,
)


async def create_label(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    data: LabelCreateRequest,
    current_user: User,
) -> Label:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)

    # Only workspace admins can create labels
    await _require_workspace_role(db, workspace.id, current_user.id, ["admin"])

    # Check name is unique within workspace
    result = await db.execute(
        select(Label).where(
            Label.workspace_id == workspace.id,
            Label.name == data.name,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A label named '{data.name}' already exists in this workspace",
        )

    label = Label(
        workspace_id=workspace.id,
        name=data.name,
        color=data.color,
    )
    db.add(label)
    await db.flush()
    await db.refresh(label)
    return label


async def list_labels(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> list[Label]:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(Label).where(Label.workspace_id == workspace.id)
        .order_by(Label.name)
    )
    return list(result.scalars().all())


async def delete_label(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    label_id: uuid.UUID,
    current_user: User,
) -> None:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_role(db, workspace.id, current_user.id, ["admin"])

    result = await db.execute(
        select(Label).where(
            Label.id == label_id,
            Label.workspace_id == workspace.id,
        )
    )
    label = result.scalar_one_or_none()
    if not label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found",
        )
    await db.delete(label)


async def add_label_to_task(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    current_user: User,
) -> None:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    # Verify task exists in workspace
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Verify label belongs to workspace
    result = await db.execute(
        select(Label).where(
            Label.id == label_id,
            Label.workspace_id == workspace.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not found in this workspace",
        )

    # Check not already applied
    result = await db.execute(
        select(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Label already applied to this task",
        )

    db.add(TaskLabel(task_id=task_id, label_id=label_id))

    # Record audit trail
    from app.services.task_service import _record_activity
    await _record_activity(db, task_id, current_user.id, "label_added", None, {
        "label_id": str(label_id),
    })


async def remove_label_from_task(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    current_user: User,
) -> None:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(TaskLabel).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
    )
    task_label = result.scalar_one_or_none()
    if not task_label:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Label not applied to this task",
        )

    await db.delete(task_label)

    from app.services.task_service import _record_activity
    await _record_activity(db, task_id, current_user.id, "label_removed", {
        "label_id": str(label_id),
    }, None)


async def list_task_labels(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    current_user: User,
) -> list[Label]:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(Label)
        .join(TaskLabel, TaskLabel.label_id == Label.id)
        .where(TaskLabel.task_id == task_id)
    )
    return list(result.scalars().all())