from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "collab_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.email_tasks",
        "app.workers.webhook_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # only ack after task completes — safer
    worker_prefetch_multiplier=1,  # process one task at a time per worker
    beat_schedule={
        # Retry failed webhook deliveries every 5 minutes
        "retry-failed-webhooks": {
            "task": "app.workers.webhook_tasks.retry_failed_webhooks",
            "schedule": crontab(minute="*/5"),
        },
        # Send task due reminders every morning at 8am UTC
        "send-due-reminders": {
            "task": "app.workers.email_tasks.send_due_date_reminders",
            "schedule": crontab(hour=8, minute=0),
        },
    },
)