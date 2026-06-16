import json
import asyncio
import hmac
import hashlib
import httpx
from celery import shared_task
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


def _make_session():
    """
    Create a fresh DB session for each Celery task.
    This avoids asyncpg 'another operation is in progress' errors
    that occur when tasks share a single AsyncSessionLocal in solo pool mode.
    """
    from app.core.config import settings
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory()


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    name="app.workers.webhook_tasks.deliver_webhook_task",
    bind=True,
    max_retries=5,
)
def deliver_webhook_task(
    self,
    delivery_id: str,
    webhook_url: str,
    webhook_secret: str,
    event_type: str,
    payload: dict,
):
    """
    Deliver a single webhook asynchronously.
    Called by FastAPI instead of making the HTTP request inline.
    """
    async def _deliver():
        from sqlalchemy import select
        from app.db.models.system import WebhookDelivery
        from app.services.webhook_service import sign_payload, _next_retry_time

        payload_str = json.dumps(payload)
        signature = sign_payload(webhook_secret, payload_str)

        async with _make_session() as db:
            result = await db.execute(
                select(WebhookDelivery).where(
                    WebhookDelivery.id == delivery_id
                )
            )
            delivery = result.scalar_one_or_none()
            if not delivery:
                return

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        webhook_url,
                        content=payload_str,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Event": event_type,
                            "X-Webhook-Signature": f"sha256={signature}",
                            "X-Webhook-Delivery": delivery_id,
                        },
                    )

                delivery.attempts += 1
                delivery.response_status = response.status_code

                if response.status_code < 400:
                    delivery.status = "success"
                    delivery.delivered_at = datetime.now(timezone.utc)
                    delivery.next_retry_at = None
                else:
                    delivery.status = "failed"
                    delivery.next_retry_at = _next_retry_time(delivery.attempts)

            except Exception:
                delivery.attempts += 1
                delivery.status = "failed"
                delivery.next_retry_at = _next_retry_time(delivery.attempts)

            await db.commit()

    _run_async(_deliver())


@shared_task(name="app.workers.webhook_tasks.retry_failed_webhooks")
def retry_failed_webhooks():
    """
    Scheduled task — runs every 5 minutes.
    Finds failed webhook deliveries that are due for retry and requeues them.
    """
    async def _run():
        from sqlalchemy import select
        from app.db.models.system import WebhookDelivery, Webhook
        from app.services.webhook_service import MAX_ATTEMPTS

        async with _make_session() as db:
            now = datetime.now(timezone.utc)

            result = await db.execute(
                select(WebhookDelivery, Webhook)
                .join(Webhook, Webhook.id == WebhookDelivery.webhook_id)
                .where(
                    WebhookDelivery.status == "failed",
                    WebhookDelivery.next_retry_at <= now,
                    WebhookDelivery.attempts < MAX_ATTEMPTS,
                    Webhook.is_active == True,
                )
            )
            rows = result.all()

            for delivery, webhook in rows:
                deliver_webhook_task.delay(
                    delivery_id=str(delivery.id),
                    webhook_url=webhook.url,
                    webhook_secret=webhook.secret,
                    event_type=delivery.event_type,
                    payload=delivery.payload,
                )
                print(f"Requeued delivery {delivery.id} for retry")

    _run_async(_run())