import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookUpdateRequest,
    WebhookResponse,
    WebhookDeliveryResponse,
)
from app.services.webhook_service import (
    create_webhook,
    list_webhooks,
    update_webhook,
    delete_webhook,
    list_webhook_deliveries,
)

router = APIRouter(tags=["Webhooks"])


@router.post(
    "/organizations/{org_slug}/webhooks",
    response_model=WebhookResponse,
    status_code=201,
)
async def create_wh(
    org_slug: str,
    data: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await create_webhook(db, org_slug, data, current_user)


@router.get(
    "/organizations/{org_slug}/webhooks",
    response_model=list[WebhookResponse],
)
async def list_wh(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_webhooks(db, org_slug, current_user)


@router.patch(
    "/organizations/{org_slug}/webhooks/{webhook_id}",
    response_model=WebhookResponse,
)
async def update_wh(
    org_slug: str,
    webhook_id: uuid.UUID,
    data: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await update_webhook(db, org_slug, webhook_id, data, current_user)


@router.delete(
    "/organizations/{org_slug}/webhooks/{webhook_id}",
    status_code=204,
)
async def delete_wh(
    org_slug: str,
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_webhook(db, org_slug, webhook_id, current_user)


@router.get(
    "/organizations/{org_slug}/webhooks/{webhook_id}/deliveries",
    response_model=list[WebhookDeliveryResponse],
)
async def list_wh_deliveries(
    org_slug: str,
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_webhook_deliveries(db, org_slug, webhook_id, current_user)