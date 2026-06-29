from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.services.analytics_service import (
    get_tasks_summary,
    get_completed_over_time,
    get_team_productivity,
    get_time_to_completion,
)

router = APIRouter(
    prefix="/organizations/{org_slug}/workspaces/{workspace_slug}/analytics",
    tags=["Analytics"],
)


@router.get(
    "/tasks-summary",
    summary="Task count breakdown",
    description="Returns total, completed, in-progress, todo, in-review, and overdue task counts with a completion rate percentage.",
)
async def tasks_summary(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_tasks_summary(db, org_slug, workspace_slug, current_user)


@router.get(
    "/completed-over-time",
    summary="Tasks completed per day",
    description="Returns a time series of tasks completed per day over the last N days (default 30).",
)
async def completed_over_time(
    org_slug: str,
    workspace_slug: str,
    days: int = Query(default=30, ge=7, le=365, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_completed_over_time(db, org_slug, workspace_slug, current_user, days)


@router.get(
    "/team-productivity",
    summary="Tasks assigned and completed per member",
    description="Returns a breakdown of completed vs open tasks for each workspace member.",
)
async def team_productivity(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_team_productivity(db, org_slug, workspace_slug, current_user)


@router.get(
    "/time-to-completion",
    summary="Average time from creation to completion by priority",
    description="Returns average completion time in hours and days, grouped by task priority.",
)
async def time_to_completion(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_time_to_completion(db, org_slug, workspace_slug, current_user)