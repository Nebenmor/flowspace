import uuid
import secrets
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.db.models.organization import Organization, OrganizationMember, Invitation
from app.db.models.user import User
from app.schemas.invitation import InvitationCreateRequest
from app.services.organization_service import _require_org_role
from app.core.config import settings
from app.services.notification_service import create_notification
from app.workers.celery_app import celery_app  # noqa: F401 — ensures app is configured

INVITE_EXPIRE_DAYS = 7


async def send_invitation(
    db: AsyncSession,
    org_slug: str,
    data: InvitationCreateRequest,
    current_user: User,
) -> Invitation:
    valid_roles = ["admin", "member", "guest"]
    if data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    # Fetch org
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

    # Only owner or admin can invite
    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    # Check if user is already a member
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.org_id == org.id,
                OrganizationMember.user_id == existing_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user is already a member of the organization",
            )

    # Check for existing pending invitation
    result = await db.execute(
        select(Invitation).where(
            Invitation.org_id == org.id,
            Invitation.email == data.email,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(timezone.utc),
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        )

    # Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRE_DAYS)

    invitation = Invitation(
        org_id=org.id,
        invited_by=current_user.id,
        email=data.email,
        role=data.role,
        token=token,
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.flush()

    # Queue invitation email as background task
    _send_invite_email(
        to_email=data.email,
        org_name=org.name,
        invited_by_name=current_user.full_name or current_user.username,
        token=token,
        role=data.role,
    )

    return invitation


async def accept_invitation(
    db: AsyncSession,
    token: str,
    current_user: User,
) -> OrganizationMember:
    # Find invitation by token
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This invitation has already been accepted",
        )

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This invitation has expired",
        )

    # Email must match the invited email
    if current_user.email != invitation.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation was sent to a different email address",
        )

    # Check not already a member
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.org_id == invitation.org_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already a member of this organization",
        )

    # Mark invitation as accepted
    invitation.accepted_at = datetime.now(timezone.utc)

    # Add user as org member
    member = OrganizationMember(
        org_id=invitation.org_id,
        user_id=current_user.id,
        role=invitation.role,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(member)

    # Notify the org owner that someone accepted their invitation
    result = await db.execute(
        select(Organization).where(Organization.id == invitation.org_id)
    )
    org = result.scalar_one()
    await create_notification(
        db=db,
        user_id=org.owner_id,
        type="invitation.accepted",
        title="Invitation accepted",
        body=f"{current_user.full_name or current_user.username} joined your organization",
        meta={
            "org_id": str(org.id),
            "user_id": str(current_user.id),
        },
    )

    return member


async def list_invitations(
    db: AsyncSession,
    org_slug: str,
    current_user: User,
) -> list[Invitation]:
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
        select(Invitation).where(Invitation.org_id == org.id)
        .order_by(Invitation.created_at.desc())
    )
    return list(result.scalars().all())


async def revoke_invitation(
    db: AsyncSession,
    org_slug: str,
    invitation_id: uuid.UUID,
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
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.org_id == org.id,
        )
    )
    invitation = result.scalar_one_or_none()
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot revoke an already accepted invitation",
        )

    # Expire the invitation immediately
    invitation.expires_at = datetime.now(timezone.utc)


# ── Email helper ──────────────────────────────────────────────────────────────

def _send_invite_email(
    to_email: str,
    org_name: str,
    invited_by_name: str,
    token: str,
    role: str,
) -> None:
    """Queue invitation email as a Celery background task."""
    from app.workers.email_tasks import send_invitation_email
    send_invitation_email.delay(
        to_email=to_email,
        invited_by_name=invited_by_name,
        org_name=org_name,
        role=role,
        token=token,
    )