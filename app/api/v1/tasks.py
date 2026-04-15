import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.task import (
    TaskCreateRequest,
    TaskUpdateRequest,
    TaskResponse,
    TaskListResponse,
    TaskFilterParams,
)
from app.services.task_service import (
    create_task,
    list_tasks,
    get_task,
    update_task,
    delete_task,
)

router = APIRouter(
    prefix="/organizations/{org_slug}/workspaces/{workspace_slug}/tasks",
    tags=["Tasks"],
)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_t(
    org_slug: str,
    workspace_slug: str,
    data: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await create_task(db, org_slug, workspace_slug, data, current_user)


@router.get("", response_model=TaskListResponse)
async def list_t(
    org_slug: str,
    workspace_slug: str,
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assignee_id: uuid.UUID | None = Query(None),
    is_overdue: bool | None = Query(None),
    parent_id: uuid.UUID | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    filters = TaskFilterParams(
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        is_overdue=is_overdue,
        parent_id=parent_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return await list_tasks(db, org_slug, workspace_slug, filters, current_user)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_t(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_task(db, org_slug, workspace_slug, task_id, current_user)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_t(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    data: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await update_task(db, org_slug, workspace_slug, task_id, data, current_user)


@router.delete("/{task_id}", status_code=204)
async def delete_t(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_task(db, org_slug, workspace_slug, task_id, current_user)