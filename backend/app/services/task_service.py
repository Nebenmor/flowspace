import uuid
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, text
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
from app.services.cache_service import get_cached, set_cached, invalidate_workspace_cache


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

    # Commit before invalidating cache / broadcasting — otherwise a client
    # refetching in response to the WS event below can race ahead of this
    # transaction and re-populate the cache with pre-update data.
    await db.commit()

    # Invalidate workspace task cache
    await invalidate_workspace_cache(str(workspace.id))

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

    # Build a deterministic cache key from the workspace + filters
    filter_str = json.dumps(filters.__dict__, default=str, sort_keys=True)
    filter_hash = hashlib.md5(filter_str.encode()).hexdigest()[:12]
    cache_key = f"tasks:{workspace.id}:{filter_hash}"

    # Return cached result if available
    cached = await get_cached(cache_key)
    if cached:
        return cached

    query = select(Task).where(
        Task.workspace_id == workspace.id,
        Task.is_archived == False,
    )

    # Full-text search using PostgreSQL tsvector
    if filters.search:
        query = query.where(
            Task.search_vector.op("@@")(
                func.plainto_tsquery("english", filters.search)
            )
        )

    # Apply remaining filters
    if filters.status:
        query = query.where(Task.status == filters.status)
    if filters.priority:
        query = query.where(Task.priority == filters.priority)
    if filters.assignee_id:
        query = query.where(Task.assignee_id == filters.assignee_id)
    if filters.parent_id is not None:
        query = query.where(Task.parent_id == filters.parent_id)
    else:
        query = query.where(Task.parent_id.is_(None))
    if filters.is_overdue:
        query = query.where(
            Task.due_date < datetime.now(timezone.utc),
            Task.status.notin_(["done", "cancelled"]),
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

    response = {
        "items": [
            {
                "id": str(t.id),
                "workspace_id": str(t.workspace_id),
                "parent_id": str(t.parent_id) if t.parent_id else None,
                "title": t.title,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "assignee_id": str(t.assignee_id) if t.assignee_id else None,
                "created_by": str(t.created_by),
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "position": t.position,
                "is_archived": t.is_archived,
                "created_at": t.created_at.isoformat(),
                "updated_at": t.updated_at.isoformat(),
            }
            for t in tasks
        ],
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
        "has_next": (offset + filters.page_size) < total,
    }

    # Cache the result for 60 seconds
    await set_cached(cache_key, response)

    return response


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

            # Send email notification to newly assigned user
            result = await db.execute(select(User).where(User.id == data.assignee_id))
            assignee = result.scalar_one_or_none()
            if assignee:
                from app.workers.email_tasks import send_task_assigned_email
                send_task_assigned_email.delay(
                    to_email=assignee.email,
                    assignee_name=assignee.full_name or assignee.username,
                    task_title=task.title,
                    task_id=str(task.id),
                    workspace_name=workspace.slug,
                )

    if data.due_date is not None and data.due_date != task.due_date:
        changes["due_date"] = {
            "old": task.due_date.isoformat() if task.due_date else None,
            "new": data.due_date.isoformat(),
        }
        task.due_date = data.due_date

    if changes:
        await _record_activity(
            db, task.id, current_user.id, "updated",
            {k: v["old"] for k, v in changes.items()},
            {k: v["new"] for k, v in changes.items()},
        )

        # Commit before invalidating cache / broadcasting — otherwise a client
        # refetching in response to the WS event below can race ahead of this
        # transaction and re-populate the cache with pre-update data.
        await db.commit()

        # Invalidate workspace task cache
        await invalidate_workspace_cache(str(workspace.id))

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

    # Commit before invalidating cache / broadcasting — otherwise a client
    # refetching in response to the WS event below can race ahead of this
    # transaction and re-populate the cache with pre-delete data.
    await db.commit()

    # Invalidate workspace task cache
    await invalidate_workspace_cache(str(workspace.id))

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

    if parent_task.parent_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a subtask of a subtask. Only one level of nesting is allowed.",
        )

    if data.assignee_id:
        await _require_workspace_member(db, workspace.id, data.assignee_id)

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

    if task_id == data.depends_on_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A task cannot depend on itself",
        )

    if await _would_create_cycle(db, task_id, data.depends_on_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dependency would create a circular relationship",
        )

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