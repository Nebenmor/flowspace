import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.db.models.task import CustomField, TaskCustomFieldValue, Task
from app.db.models.user import User
from app.schemas.custom_field import CustomFieldCreateRequest
from app.services.workspace_service import (
    _get_org_or_404,
    _get_workspace_or_404,
    _require_workspace_member,
    _require_workspace_role,
)


async def create_custom_field(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    data: CustomFieldCreateRequest,
    current_user: User,
) -> CustomField:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_role(db, workspace.id, current_user.id, ["admin"])

    # Select type requires options
    if data.field_type == "select" and not data.options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select fields must include at least one option",
        )

    # Non-select types should not have options
    if data.field_type != "select" and data.options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Field type '{data.field_type}' does not support options",
        )

    field = CustomField(
        workspace_id=workspace.id,
        name=data.name,
        field_type=data.field_type,
        options=data.options,
    )
    db.add(field)
    await db.flush()
    await db.refresh(field)
    return field


async def list_custom_fields(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> list[CustomField]:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(CustomField)
        .where(CustomField.workspace_id == workspace.id)
        .order_by(CustomField.name)
    )
    return list(result.scalars().all())


async def delete_custom_field(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    field_id: uuid.UUID,
    current_user: User,
) -> None:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_role(db, workspace.id, current_user.id, ["admin"])

    result = await db.execute(
        select(CustomField).where(
            CustomField.id == field_id,
            CustomField.workspace_id == workspace.id,
        )
    )
    field = result.scalar_one_or_none()
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found",
        )

    await db.delete(field)


async def set_field_value(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    field_id: uuid.UUID,
    value: Any,
    current_user: User,
) -> TaskCustomFieldValue:
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
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Verify field belongs to workspace
    result = await db.execute(
        select(CustomField).where(
            CustomField.id == field_id,
            CustomField.workspace_id == workspace.id,
        )
    )
    field = result.scalar_one_or_none()
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom field not found in this workspace",
        )

    # Validate value against field type
    _validate_field_value(field, value)

    # Upsert — update if exists, create if not
    result = await db.execute(
        select(TaskCustomFieldValue).where(
            TaskCustomFieldValue.task_id == task_id,
            TaskCustomFieldValue.field_id == field_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.value = value
        field_value = existing
    else:
        field_value = TaskCustomFieldValue(
            task_id=task_id,
            field_id=field_id,
            value=value,
        )
        db.add(field_value)

    await db.flush()

    from app.services.task_service import _record_activity
    await _record_activity(db, task_id, current_user.id, "custom_field_updated", None, {
        "field_id": str(field_id),
        "value": value,
    })

    return field_value


async def get_task_field_values(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    task_id: uuid.UUID,
    current_user: User,
) -> list[TaskCustomFieldValue]:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(TaskCustomFieldValue).where(
            TaskCustomFieldValue.task_id == task_id,
        )
    )
    return list(result.scalars().all())


# ── Value validator ───────────────────────────────────────────────────────────

def _validate_field_value(field: CustomField, value: Any) -> None:
    if field.field_type == "text":
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Value must be a string for text fields",
            )
    elif field.field_type == "number":
        if not isinstance(value, (int, float)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Value must be a number for number fields",
            )
    elif field.field_type == "boolean":
        if not isinstance(value, bool):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Value must be true or false for boolean fields",
            )
    elif field.field_type == "select":
        if value not in (field.options or []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid option. Must be one of: {', '.join(field.options or [])}",
            )
    elif field.field_type == "date":
        if not isinstance(value, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Date value must be an ISO 8601 string e.g. 2026-04-25T00:00:00Z",
            )