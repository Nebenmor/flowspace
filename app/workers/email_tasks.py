import resend
from celery import shared_task
from app.core.config import settings


@shared_task(
    name="app.workers.email_tasks.send_task_assigned_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_task_assigned_email(
    self,
    to_email: str,
    assignee_name: str,
    task_title: str,
    task_id: str,
    workspace_name: str,
):
    """Send email notification when a task is assigned to a user."""
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": to_email,
            "subject": f"Task assigned to you: {task_title}",
            "html": f"""
                <h2>You have been assigned a task</h2>
                <p>Hi {assignee_name},</p>
                <p>You have been assigned to the following task in
                <strong>{workspace_name}</strong>:</p>
                <h3>{task_title}</h3>
                <p>
                    <a href="{settings.BASE_URL}/tasks/{task_id}"
                       style="background:#2563eb;color:white;padding:12px 24px;
                              border-radius:6px;text-decoration:none;">
                        View Task
                    </a>
                </p>
            """,
        })
    except Exception as exc:
        # Retry up to 3 times with 60 second delay
        raise self.retry(exc=exc)


@shared_task(
    name="app.workers.email_tasks.send_invitation_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_invitation_email(
    self,
    to_email: str,
    invited_by_name: str,
    org_name: str,
    role: str,
    token: str,
):
    """Send organization invitation email."""
    invite_url = f"{settings.BASE_URL}/api/v1/invitations/accept?token={token}"
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": to_email,
            "subject": f"You've been invited to join {org_name}",
            "html": f"""
                <h2>You've been invited to join {org_name}</h2>
                <p>{invited_by_name} has invited you to join
                <strong>{org_name}</strong> as a
                <strong>{role}</strong>.</p>
                <p>
                    <a href="{invite_url}"
                       style="background:#2563eb;color:white;padding:12px 24px;
                              border-radius:6px;text-decoration:none;">
                        Accept Invitation
                    </a>
                </p>
                <p>This invitation expires in 7 days.</p>
            """,
        })
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(
    name="app.workers.email_tasks.send_due_date_reminders",
    bind=True,
)
def send_due_date_reminders(self):
    """
    Scheduled task — runs every morning at 8am UTC.
    Finds tasks due today and sends reminder emails to assignees.
    """
    import asyncio
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.db.models.task import Task
    from app.db.models.user import User

    async def _run():
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            tomorrow = now + timedelta(days=1)

            result = await db.execute(
                select(Task, User)
                .join(User, User.id == Task.assignee_id)
                .where(
                    Task.due_date >= now,
                    Task.due_date <= tomorrow,
                    Task.status.notin_(["done", "cancelled"]),
                    Task.assignee_id.isnot(None),
                    Task.is_archived == False,
                )
            )
            rows = result.all()

            for task, user in rows:
                try:
                    resend.api_key = settings.RESEND_API_KEY
                    resend.Emails.send({
                        "from": settings.EMAIL_FROM,
                        "to": user.email,
                        "subject": f"Task due today: {task.title}",
                        "html": f"""
                            <h2>Task Due Today</h2>
                            <p>Hi {user.full_name or user.username},</p>
                            <p>This task is due today:</p>
                            <h3>{task.title}</h3>
                            <p>Due: {task.due_date.strftime('%B %d, %Y')}</p>
                        """,
                    })
                except Exception as e:
                    print(f"Failed to send reminder for task {task.id}: {e}")

    asyncio.run(_run())