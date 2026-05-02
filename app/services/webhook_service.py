import uuid
import hmac
import hashlib
import secrets
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.db.models.system import Webhook, WebhookDelivery
from app.db.models.organization import Organization
from app.db.models.user import User
from app.schemas.webhook import WebhookCreateRequest, WebhookUpdateRequest
from app.services.organization_service import _require_org_role
from sqlalchemy import select, delete

# Retry schedule — exponential backoff in minutes
RETRY_DELAYS = [1, 5, 30, 120, 480]  # 1min, 5min, 30min, 2hr, 8hr
MAX_ATTEMPTS = len(RETRY_DELAYS) + 1  # 6 total attempts


async def create_webhook(
    db: AsyncSession,
    org_slug: str,
    data: WebhookCreateRequest,
    current_user: User,
) -> Webhook:
    result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.is_active == True,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Only owner or admin can register webhooks
    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    # Generate a secure signing secret
    secret = secrets.token_hex(32)

    webhook = Webhook(
        org_id=org.id,
        name=data.name,
        url=data.url,
        secret=secret,
        events=data.events,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def list_webhooks(
    db: AsyncSession,
    org_slug: str,
    current_user: User,
) -> list[Webhook]:
    result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.is_active == True,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    result = await db.execute(
        select(Webhook).where(Webhook.org_id == org.id)
        .order_by(Webhook.created_at.desc())
    )
    return list(result.scalars().all())


async def update_webhook(
    db: AsyncSession,
    org_slug: str,
    webhook_id: uuid.UUID,
    data: WebhookUpdateRequest,
    current_user: User,
) -> Webhook:
    result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.is_active == True,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.org_id == org.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    if data.name is not None:
        webhook.name = data.name
    if data.events is not None:
        webhook.events = data.events
    if data.is_active is not None:
        webhook.is_active = data.is_active

    return webhook


async def delete_webhook(
    db: AsyncSession,
    org_slug: str,
    webhook_id: uuid.UUID,
    current_user: User,
) -> None:
    result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.is_active == True,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    result = await db.execute(
        select(Webhook).where(
            Webhook.id == webhook_id,
            Webhook.org_id == org.id,
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    await db.delete(webhook)


async def list_webhook_deliveries(
    db: AsyncSession,
    org_slug: str,
    webhook_id: uuid.UUID,
    current_user: User,
) -> list[WebhookDelivery]:
    result = await db.execute(
        select(Organization).where(
            Organization.slug == org_slug,
            Organization.is_active == True,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    result = await db.execute(
        select(WebhookDelivery)
        .join(Webhook, Webhook.id == WebhookDelivery.webhook_id)
        .where(
            WebhookDelivery.webhook_id == webhook_id,
            Webhook.org_id == org.id,
        )
        .order_by(WebhookDelivery.created_at.desc())
        .limit(50)
    )
    return list(result.scalars().all())


# ── Delivery logic ────────────────────────────────────────────────────────────

def sign_payload(secret: str, payload: str) -> str:
    """
    Generate HMAC-SHA256 signature for webhook payload.
    Receivers use this to verify the request came from us.
    """
    return hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


async def deliver_webhook(
    db: AsyncSession,
    webhook: Webhook,
    event_type: str,
    payload: dict,
) -> WebhookDelivery:
    """
    Attempt immediate delivery of a webhook.
    Creates a delivery record regardless of success or failure.
    """
    import json
    payload_str = json.dumps(payload)
    signature = sign_payload(webhook.secret, payload_str)

    delivery = WebhookDelivery(
        webhook_id=webhook.id,
        event_type=event_type,
        payload=payload,
        status="pending",
        attempts=0,
    )
    db.add(delivery)
    await db.flush()

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                content=payload_str,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": event_type,
                    "X-Webhook-Signature": f"sha256={signature}",
                    "X-Webhook-Delivery": str(delivery.id),
                },
            )

        delivery.attempts = 1
        delivery.response_status = response.status_code

        if response.status_code < 400:
            delivery.status = "success"
            delivery.delivered_at = datetime.now(timezone.utc)
        else:
            delivery.status = "failed"
            delivery.next_retry_at = _next_retry_time(1)

    except Exception as e:
        delivery.attempts = 1
        delivery.status = "failed"
        delivery.next_retry_at = _next_retry_time(1)

    return delivery


async def trigger_webhook_event(
    db: AsyncSession,
    org_id: uuid.UUID,
    event_type: str,
    payload: dict,
) -> None:
    """
    Find all active webhooks subscribed to this event and deliver to each.
    Called from service layer when events happen.
    """
    result = await db.execute(
        select(Webhook).where(
            Webhook.org_id == org_id,
            Webhook.is_active == True,
        )
    )
    webhooks = result.scalars().all()

    for webhook in webhooks:
        if event_type in webhook.events:
            await deliver_webhook(db, webhook, event_type, payload)


def _next_retry_time(attempt: int) -> datetime:
    """Calculate when to retry based on attempt number."""
    if attempt > len(RETRY_DELAYS):
        return None
    delay_minutes = RETRY_DELAYS[attempt - 1]
    return datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)