import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.label import LabelCreateRequest, LabelResponse, TaskLabelRequest
from app.services.label_service import (
    create_label,
    list_labels,
    delete_label,
    add_label_to_task,
    remove_label_from_task,
    list_task_labels,
)

router = APIRouter(tags=["Labels"])


@router.post(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/labels",
    response_model=LabelResponse,
    status_code=201,
)
async def create_l(
    org_slug: str,
    workspace_slug: str,
    data: LabelCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await create_label(db, org_slug, workspace_slug, data, current_user)


@router.get(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/labels",
    response_model=list[LabelResponse],
)
async def list_l(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_labels(db, org_slug, workspace_slug, current_user)


@router.delete(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/labels/{label_id}",
    status_code=204,
)
async def delete_l(
    org_slug: str,
    workspace_slug: str,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_label(db, org_slug, workspace_slug, label_id, current_user)


@router.post(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/tasks/{task_id}/labels",
    status_code=204,
)
async def add_label(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    data: TaskLabelRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await add_label_to_task(
        db, org_slug, workspace_slug, task_id, data.label_id, current_user
    )


@router.delete(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/tasks/{task_id}/labels/{label_id}",
    status_code=204,
)
async def remove_label(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    label_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await remove_label_from_task(
        db, org_slug, workspace_slug, task_id, label_id, current_user
    )


@router.get(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/tasks/{task_id}/labels",
    response_model=list[LabelResponse],
)
async def list_task_l(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_task_labels(
        db, org_slug, workspace_slug, task_id, current_user
    )