import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.custom_field import (
    CustomFieldCreateRequest,
    CustomFieldResponse,
    CustomFieldValueSetRequest,
    CustomFieldValueResponse,
)
from app.services.custom_field_service import (
    create_custom_field,
    list_custom_fields,
    delete_custom_field,
    set_field_value,
    get_task_field_values,
)

router = APIRouter(tags=["Custom Fields"])


@router.post(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/custom-fields",
    response_model=CustomFieldResponse,
    status_code=201,
)
async def create_cf(
    org_slug: str,
    workspace_slug: str,
    data: CustomFieldCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await create_custom_field(db, org_slug, workspace_slug, data, current_user)


@router.get(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/custom-fields",
    response_model=list[CustomFieldResponse],
)
async def list_cf(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_custom_fields(db, org_slug, workspace_slug, current_user)


@router.delete(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/custom-fields/{field_id}",
    status_code=204,
)
async def delete_cf(
    org_slug: str,
    workspace_slug: str,
    field_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_custom_field(db, org_slug, workspace_slug, field_id, current_user)


@router.put(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/tasks/{task_id}/custom-fields/{field_id}",
    response_model=CustomFieldValueResponse,
)
async def set_cf_value(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    field_id: uuid.UUID,
    data: CustomFieldValueSetRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await set_field_value(
        db, org_slug, workspace_slug, task_id, field_id, data.value, current_user
    )


@router.get(
    "/organizations/{org_slug}/workspaces/{workspace_slug}/tasks/{task_id}/custom-fields",
    response_model=list[CustomFieldValueResponse],
)
async def get_cf_values(
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_task_field_values(
        db, org_slug, workspace_slug, task_id, current_user
    )