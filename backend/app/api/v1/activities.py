import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.activity import ActivityListResponse
from app.services.activity_service import (
    get_task_activity,
    get_workspace_activity,
    get_user_activity,
)

router = APIRouter(tags=["Activity"])


@router.get(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/tasks/{task_id}/activity",
    response_model=ActivityListResponse,
)
async def task_activity(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_task_activity(
        db, org_slug, workspace_slug, task_id, current_user, page, page_size
    )


@router.get(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/activity",
    response_model=ActivityListResponse,
)
async def workspace_activity(
    org_slug: str,
    workspace_slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_workspace_activity(
        db, org_slug, workspace_slug, current_user, page, page_size
    )


@router.get(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/members/{user_id}/activity",
    response_model=ActivityListResponse,
)
async def user_activity(
    org_slug: str,
    workspace_slug: str,
    user_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_user_activity(
        db, org_slug, workspace_slug, user_id, current_user, page, page_size
    )