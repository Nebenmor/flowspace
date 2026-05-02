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
from app.websockets.manager import manager
from app.services.notification_service import create_notification
from app.services.webhook_service import trigger_webhook_event


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

    # Broadcast real-time event to workspace
    await manager.broadcast_to_workspace(
        workspace_id=str(workspace.id),
        event="task.created",
        data={
            "task_id": str(task.id),
            "title": task.title,
            "created_by": str(current_user.id),
            "status": task.status,
            "priority": task.priority,
        },
    )

    # Trigger webhook event
    await trigger_webhook_event(
        db=db,
        org_id=workspace.org_id,
        event_type="task.created",
        payload={
            "task_id": str(task.id),
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "workspace_id": str(workspace.id),
            "created_by": str(current_user.id),
        },
    )

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

        # Notify the newly assigned user
        if data.assignee_id:
            await create_notification(
                db=db,
                user_id=data.assignee_id,
                type="task.assigned",
                title="You were assigned a task",
                body=f"You have been assigned to: {task.title}",
                meta={
                    "task_id": str(task.id),
                    "workspace_id": str(workspace.id),
                },
            )
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

        # Broadcast real-time event to workspace
        await manager.broadcast_to_workspace(
            workspace_id=str(workspace.id),
            event="task.updated",
            data={
                "task_id": str(task.id),
                "changes": changes,
                "updated_by": str(current_user.id),
            },
        )

        # Trigger webhook events
        await trigger_webhook_event(
            db=db,
            org_id=workspace.org_id,
            event_type="task.updated",
            payload={
                "task_id": str(task.id),
                "changes": {k: v["new"] for k, v in changes.items()},
                "workspace_id": str(workspace.id),
                "updated_by": str(current_user.id),
            },
        )

        # Fire task.completed specifically if status changed to done
        if "status" in changes and changes["status"]["new"] == "done":
            await trigger_webhook_event(
                db=db,
                org_id=workspace.org_id,
                event_type="task.completed",
                payload={
                    "task_id": str(task.id),
                    "title": task.title,
                    "completed_by": str(current_user.id),
                    "workspace_id": str(workspace.id),
                },
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

    # Broadcast real-time event
    await manager.broadcast_to_workspace(
        workspace_id=str(workspace.id),
        event="task.deleted",
        data={
            "task_id": str(task_id),
            "deleted_by": str(current_user.id),
        },
    )

    # Trigger webhook event
    await trigger_webhook_event(
        db=db,
        org_id=workspace.org_id,
        event_type="task.deleted",
        payload={
            "task_id": str(task_id),
            "deleted_by": str(current_user.id),
            "workspace_id": str(workspace.id),
        },
    )


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


async def create_subtask(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    parent_task_id: uuid.UUID,
    data: TaskCreateRequest,
    current_user: User,
) -> Task:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    # Verify parent task exists in this workspace
    result = await db.execute(
        select(Task).where(
            Task.id == parent_task_id,
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
        )
    )
    parent_task = result.scalar_one_or_none()
    if not parent_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent task not found",
        )

    # Prevent more than one level of nesting —
    # subtasks cannot have subtasks of their own
    if parent_task.parent_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a subtask of a subtask. Only one level of nesting is allowed.",
        )

    # Validate assignee
    if data.assignee_id:
        await _require_workspace_member(db, workspace.id, data.assignee_id)

    # Calculate position within siblings
    result = await db.execute(
        select(func.max(Task.position)).where(
            Task.workspace_id == workspace.id,
            Task.parent_id == parent_task_id,
        )
    )
    max_position = result.scalar() or 0.0
    position = max_position + 1000.0

    subtask = Task(
        workspace_id=workspace.id,
        parent_id=parent_task_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        assignee_id=data.assignee_id,
        created_by=current_user.id,
        due_date=data.due_date,
        position=position,
    )
    db.add(subtask)
    await db.flush()

    await _record_activity(db, subtask.id, current_user.id, "created", None, {
        "title": subtask.title,
        "parent_id": str(parent_task_id),
    })

    return subtask


async def list_subtasks(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    parent_task_id: uuid.UUID,
    current_user: User,
) -> list[Task]:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(Task).where(
            Task.parent_id == parent_task_id,
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
        ).order_by(Task.position)
    )
    return list(result.scalars().all())


async def add_dependency(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    data: "TaskDependencyCreateRequest",
    current_user: User,
) -> "TaskDependency":
    from app.db.models.task import TaskDependency
    from app.schemas.task import TaskDependencyCreateRequest

    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    # Verify task exists
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

    # Verify dependency target exists in same workspace
    result = await db.execute(
        select(Task).where(
            Task.id == data.depends_on_id,
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target task not found in this workspace",
        )

    # Prevent self-dependency
    if task_id == data.depends_on_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot depend on itself",
        )

    # Prevent circular dependency
    if await _would_create_cycle(db, task_id, data.depends_on_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dependency would create a circular relationship",
        )

    # Check not already exists
    result = await db.execute(
        select(TaskDependency).where(
            TaskDependency.task_id == task_id,
            TaskDependency.depends_on_id == data.depends_on_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This dependency already exists",
        )

    dependency = TaskDependency(
        task_id=task_id,
        depends_on_id=data.depends_on_id,
        dependency_type=data.dependency_type,
    )
    db.add(dependency)
    await db.flush()

    await _record_activity(db, task_id, current_user.id, "dependency_added", None, {
        "depends_on_id": str(data.depends_on_id),
        "dependency_type": data.dependency_type,
    })

    return dependency


async def list_dependencies(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    current_user: User,
) -> list:
    from app.db.models.task import TaskDependency

    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(TaskDependency).where(TaskDependency.task_id == task_id)
    )
    return list(result.scalars().all())


async def remove_dependency(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    dependency_id: uuid.UUID,
    current_user: User,
) -> None:
    from app.db.models.task import TaskDependency

    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(TaskDependency).where(
            TaskDependency.id == dependency_id,
            TaskDependency.task_id == task_id,
        )
    )
    dependency = result.scalar_one_or_none()
    if not dependency:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dependency not found",
        )

    await db.delete(dependency)

    await _record_activity(db, task_id, current_user.id, "dependency_removed", {
        "depends_on_id": str(dependency.depends_on_id),
        "dependency_type": dependency.dependency_type,
    }, None)


# ── Cycle detection ───────────────────────────────────────────────────────────

async def _would_create_cycle(
    db: AsyncSession,
    task_id: uuid.UUID,
    depends_on_id: uuid.UUID,
) -> bool:
    """
    Check if adding task_id -> depends_on_id would create a cycle.
    We do a breadth-first traversal starting from depends_on_id,
    following existing dependencies. If we reach task_id, it's a cycle.
    """
    from app.db.models.task import TaskDependency

    visited = set()
    queue = [depends_on_id]

    while queue:
        current = queue.pop(0)
        if current == task_id:
            return True
        if current in visited:
            continue
        visited.add(current)

        result = await db.execute(
            select(TaskDependency.depends_on_id).where(
                TaskDependency.task_id == current
            )
        )
        neighbors = result.scalars().all()
        queue.extend(neighbors)

    return False