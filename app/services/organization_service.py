import re
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.db.models.organization import Organization, OrganizationMember
from app.db.models.user import User
from app.schemas.organization import OrganizationCreateRequest, OrganizationUpdateRequest


def _generate_slug(name: str) -> str:
    """Convert organization name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


async def create_organization(
    db: AsyncSession,
    data: OrganizationCreateRequest,
    current_user: User,
) -> Organization:
    # Generate slug from name if not provided
    slug = data.slug or _generate_slug(data.name)

    # Check slug is unique
    result = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An organization with slug '{slug}' already exists",
        )

    # Create organization
    org = Organization(
        name=data.name,
        slug=slug,
        owner_id=current_user.id,
    )
    db.add(org)
    await db.flush()  # get org.id before creating membership

    # Add creator as owner member
    db.add(OrganizationMember(
        org_id=org.id,
        user_id=current_user.id,
        role="owner",
        joined_at=datetime.now(timezone.utc),
    ))

    return org


async def get_organization(
    db: AsyncSession,
    slug: str,
    current_user: User,
) -> Organization:
    result = await db.execute(
        select(Organization)
        .where(Organization.slug == slug)
        .options(selectinload(Organization.members))
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Verify requester is a member
    await _require_org_member(db, org.id, current_user.id)

    return org


async def list_user_organizations(
    db: AsyncSession,
    current_user: User,
) -> list[Organization]:
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember, OrganizationMember.org_id == Organization.id)
        .where(OrganizationMember.user_id == current_user.id)
        .where(Organization.is_active == True)
    )
    return list(result.scalars().all())


async def update_organization(
    db: AsyncSession,
    slug: str,
    data: OrganizationUpdateRequest,
    current_user: User,
) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Only owner or admin can update
    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    if data.name is not None:
        org.name = data.name
    if data.logo_url is not None:
        org.logo_url = data.logo_url

    return org


async def delete_organization(
    db: AsyncSession,
    slug: str,
    current_user: User,
) -> None:
    result = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Only owner can delete
    await _require_org_role(db, org.id, current_user.id, ["owner"])

    # Soft delete — never hard delete organizations
    org.is_active = False


async def get_org_members(
    db: AsyncSession,
    slug: str,
    current_user: User,
) -> list[dict]:
    result = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    await _require_org_member(db, org.id, current_user.id)

    # Fetch members with user details
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.org_id == org.id)
    )
    rows = result.all()

    members = []
    for member, user in rows:
        members.append({
            "id": member.id,
            "user_id": member.user_id,
            "org_id": member.org_id,
            "role": member.role,
            "joined_at": member.joined_at,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
        })
    return members


async def update_member_role(
    db: AsyncSession,
    slug: str,
    member_user_id: uuid.UUID,
    new_role: str,
    current_user: User,
) -> OrganizationMember:
    valid_roles = ["admin", "member", "guest"]
    if new_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    result = await db.execute(
        select(Organization).where(Organization.slug == slug)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Only owner or admin can change roles
    await _require_org_role(db, org.id, current_user.id, ["owner", "admin"])

    # Cannot change the owner's role
    if member_user_id == org.owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change the role of the organization owner",
        )

    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org.id,
            OrganizationMember.user_id == member_user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in this organization",
        )

    member.role = new_role
    return member


# ── Internal permission helpers ──────────────────────────────────────────────

async def _require_org_member(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> OrganizationMember:
    """Verify user is any member of the organization."""
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )
    return member


async def _require_org_role(
    db: AsyncSession,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    allowed_roles: list[str],
) -> OrganizationMember:
    """Verify user has one of the required roles in the organization."""
    member = await _require_org_member(db, org_id, user_id)
    if member.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join(allowed_roles)}",
        )
    return member