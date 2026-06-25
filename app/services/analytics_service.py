from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from app.db.models.task import Task
from app.db.models.user import User
from app.db.models.workspace import WorkspaceMember
from app.services.workspace_service import (
    _get_org_or_404,
    _get_workspace_or_404,
    _require_workspace_member,
)


async def get_tasks_summary(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> dict:
    """
    Returns a high-level count breakdown of tasks in the workspace.
    """
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((Task.status == "done", Task.id))
            ).label("completed"),
            func.count(
                case((Task.status == "in_progress", Task.id))
            ).label("in_progress"),
            func.count(
                case((Task.status == "todo", Task.id))
            ).label("todo"),
            func.count(
                case((Task.status == "in_review", Task.id))
            ).label("in_review"),
            func.count(
                case((
                    (Task.due_date < now) &
                    (Task.status.notin_(["done", "cancelled"])),
                    Task.id
                ))
            ).label("overdue"),
        ).where(
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
            Task.parent_id.is_(None),  # root tasks only
        )
    )
    row = result.one()

    return {
        "total": row.total,
        "completed": row.completed,
        "in_progress": row.in_progress,
        "todo": row.todo,
        "in_review": row.in_review,
        "overdue": row.overdue,
        "completion_rate": round((row.completed / row.total * 100), 1) if row.total > 0 else 0.0,
    }


async def get_completed_over_time(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
    days: int = 30,
) -> list[dict]:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    since = datetime.now(timezone.utc) - timedelta(days=days)

    day_label = func.date_trunc("day", Task.completed_at).label("day")

    result = await db.execute(
        select(
            day_label,
            func.count(Task.id).label("count"),
        )
        .where(
            Task.workspace_id == workspace.id,
            Task.status == "done",
            Task.completed_at >= since,
            Task.is_archived == False,
        )
        .group_by(day_label)
        .order_by(day_label)
    )
    rows = result.all()

    return [
        {
            "date": row.day.strftime("%Y-%m-%d"),
            "completed": row.count,
        }
        for row in rows
    ]

async def get_team_productivity(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> list[dict]:
    """
    Returns tasks completed per workspace member.
    """
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(
            User.id,
            User.full_name,
            User.username,
            User.email,
            func.count(Task.id).label("completed_tasks"),
            func.count(
                case(((Task.status.in_(["todo", "in_progress", "in_review"])), Task.id))
            ).label("open_tasks"),
        )
        .join(Task, Task.assignee_id == User.id)
        .join(WorkspaceMember, (WorkspaceMember.user_id == User.id) & (WorkspaceMember.workspace_id == workspace.id))
        .where(
            Task.workspace_id == workspace.id,
            Task.is_archived == False,
        )
        .group_by(User.id, User.full_name, User.username, User.email)
        .order_by(func.count(Task.id).desc())
    )
    rows = result.all()

    return [
        {
            "user_id": str(row.id),
            "full_name": row.full_name,
            "username": row.username,
            "email": row.email,
            "completed_tasks": row.completed_tasks,
            "open_tasks": row.open_tasks,
        }
        for row in rows
    ]


async def get_time_to_completion(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> list[dict]:
    """
    Returns average time from task creation to completion, grouped by priority.
    """
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(
            Task.priority,
            func.count(Task.id).label("count"),
            func.avg(
                func.extract("epoch", Task.completed_at - Task.created_at)
            ).label("avg_seconds"),
        )
        .where(
            Task.workspace_id == workspace.id,
            Task.status == "done",
            Task.completed_at.isnot(None),
            Task.is_archived == False,
        )
        .group_by(Task.priority)
        .order_by(Task.priority)
    )
    rows = result.all()

    return [
        {
            "priority": row.priority,
            "tasks_completed": row.count,
            "avg_hours": round(row.avg_seconds / 3600, 1) if row.avg_seconds else 0.0,
            "avg_days": round(row.avg_seconds / 86400, 1) if row.avg_seconds else 0.0,
        }
        for row in rows
    ]