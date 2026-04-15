import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.db.models.task import Task
from app.db.models.workspace import Workspace
from app.db.models.user import User
from app.schemas.task import TaskCreateRequest, TaskUpdateRequest, TaskFilterParams
from app.services.workspace_service import _get_org_or_404, _get_workspace_or_404, _require_workspace_member


async def create_task(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    data: TaskCreateRequest,
    current_user: User,
) -> Task:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    # Validate parent task belongs to same workspace
    if data.parent_id:
        result = await db.execute(
            select(Task).where(
                Task.id == data.parent_id,
                Task.workspace_id == workspace.id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent task not found in this workspace",
            )

    # Validate assignee is a workspace member
    if data.assignee_id:
        await _require_workspace_member(db, workspace.id, data.assignee_id)

    # Calculate position — place at end of list
    result = await db.execute(
        select(func.max(Task.position)).where(
            Task.workspace_id == workspace.id,
            Task.parent_id == data.parent_id,
        )
    )
    max_position = result.scalar() or 0.0
    position = max_position + 1000.0

    task = Task(
        workspace_id=workspace.id,
        parent_id=data.parent_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        assignee_id=data.assignee_id,
        created_by=current_user.id,
        due_date=data.due_date,
        position=position,
    )
    db.add(task)
    await db.flush()

    # Record audit trail
    await _record_activity(db, task.id, current_user.id, "created", None, {
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
    })

    return task


async def list_tasks(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    filters: TaskFilterParams,
    current_user: User,
) -> dict:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    query = select(Task).where(
        Task.workspace_id == workspace.id,
        Task.is_archived == False,
    )

    # Apply filters
    if filters.status:
        query = query.where(Task.status == filters.status)
    if filters.priority:
        query = query.where(Task.priority == filters.priority)
    if filters.assignee_id:
        query = query.where(Task.assignee_id == filters.assignee_id)
    if filters.parent_id is not None:
        query = query.where(Task.parent_id == filters.parent_id)
    else:
        # Default: only return root tasks (no parent)
        query = query.where(Task.parent_id.is_(None))
    if filters.is_overdue:
        query = query.where(
            Task.due_date < datetime.now(timezone.utc),
            Task.status.notin_(["done", "cancelled"]),
        )
    if filters.search:
        query = query.where(
            or_(
                Task.title.ilike(f"%{filters.search}%"),
                Task.description.ilike(f"%{filters.search}%"),
            )
        )

    # Count total for pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (filters.page - 1) * filters.page_size
    query = query.order_by(Task.position).offset(offset).limit(filters.page_size)

    result = await db.execute(query)
    tasks = list(result.scalars().all())

    return {
        "items": tasks,
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "has_next": (offset + filters.page_size) < total,
    }


async def get_task(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    current_user: User,
) -> Task:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    return task


async def update_task(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    data: TaskUpdateRequest,
    current_user: User,
) -> Task:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Validate assignee if being changed
    if data.assignee_id:
        await _require_workspace_member(db, workspace.id, data.assignee_id)

    # Track changes for audit trail
    changes = {}
    if data.title is not None and data.title != task.title:
        changes["title"] = {"old": task.title, "new": data.title}
        task.title = data.title
    if data.description is not None and data.description != task.description:
        changes["description"] = {"old": task.description, "new": data.description}
        task.description = data.description
    if data.status is not None and data.status != task.status:
        changes["status"] = {"old": task.status, "new": data.status}
        task.status = data.status
        if data.status == "done":
            task.completed_at = datetime.now(timezone.utc)
        elif task.completed_at:
            task.completed_at = None
    if data.priority is not None and data.priority != task.priority:
        changes["priority"] = {"old": task.priority, "new": data.priority}
        task.priority = data.priority
    if data.assignee_id != task.assignee_id:
        changes["assignee_id"] = {
            "old": str(task.assignee_id),
            "new": str(data.assignee_id),
        }
        task.assignee_id = data.assignee_id
    if data.due_date is not None and data.due_date != task.due_date:
        changes["due_date"] = {
            "old": task.due_date.isoformat() if task.due_date else None,
            "new": data.due_date.isoformat(),
        }
        task.due_date = data.due_date

    # Record audit trail only if something changed
    if changes:
        await _record_activity(
            db, task.id, current_user.id, "updated",
            {k: v["old"] for k, v in changes.items()},
            {k: v["new"] for k, v in changes.items()},
        )

    return task


async def delete_task(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    current_user: User,
) -> None:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.workspace_id == workspace.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Soft delete
    task.is_archived = True
    await _record_activity(db, task.id, current_user.id, "archived", None, None)


# ── Audit trail helper ────────────────────────────────────────────────────────

async def _record_activity(
    db: AsyncSession,
    task_id: uuid.UUID,
    actor_id: uuid.UUID,
    action: str,
    old_value: dict | None,
    new_value: dict | None,
) -> None:
    from app.db.models.collaboration import TaskActivity
    db.add(TaskActivity(
        task_id=task_id,
        actor_id=actor_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
    ))