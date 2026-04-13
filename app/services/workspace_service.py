import re
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.db.models.workspace import Workspace, WorkspaceMember
from app.db.models.organization import Organization, OrganizationMember
from app.db.models.user import User
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceUpdateRequest
from app.services.organization_service import _require_org_member


def _generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug


async def create_workspace(
    db: AsyncSession,
    org_slug: str,
    data: WorkspaceCreateRequest,
    current_user: User,
) -> Workspace:
    # Verify org exists
    org = await _get_org_or_404(db, org_slug)

    # Must be org member to create workspace
    await _require_org_member(db, org.id, current_user.id)

    slug = data.slug or _generate_slug(data.name)

    # Slug must be unique within the org
    result = await db.execute(
        select(Workspace).where(
            Workspace.org_id == org.id,
            Workspace.slug == slug,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A workspace with slug '{slug}' already exists in this organization",
        )

    workspace = Workspace(
        org_id=org.id,
        name=data.name,
        slug=slug,
        description=data.description,
        created_by=current_user.id,
    )
    db.add(workspace)
    await db.flush()

    # Add creator as workspace admin
    db.add(WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role="admin",
        joined_at=datetime.now(timezone.utc),
    ))

    return workspace


async def list_workspaces(
    db: AsyncSession,
    org_slug: str,
    current_user: User,
) -> list[Workspace]:
    org = await _get_org_or_404(db, org_slug)
    await _require_org_member(db, org.id, current_user.id)

    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(
            Workspace.org_id == org.id,
            Workspace.is_archived == False,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    return list(result.scalars().all())


async def get_workspace(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> Workspace:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)
    return workspace


async def update_workspace(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    data: WorkspaceUpdateRequest,
    current_user: User,
) -> Workspace:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)

    # Only workspace admin or org owner/admin can update
    await _require_workspace_role(db, workspace.id, current_user.id, ["admin"])

    if data.name is not None:
        workspace.name = data.name
    if data.description is not None:
        workspace.description = data.description

    return workspace


async def archive_workspace(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> None:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_role(db, workspace.id, current_user.id, ["admin"])
    workspace.is_archived = True


async def get_workspace_members(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    current_user: User,
) -> list[dict]:
    org = await _get_org_or_404(db, org_slug)
    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_member(db, workspace.id, current_user.id)

    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(WorkspaceMember.workspace_id == workspace.id)
    )
    rows = result.all()

    members = []
    for member, user in rows:
        members.append({
            "id": member.id,
            "workspace_id": member.workspace_id,
            "user_id": member.user_id,
            "role": member.role,
            "joined_at": member.joined_at,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
        })
    return members


async def add_workspace_member(
    db: AsyncSession,
    org_slug: str,
    workspace_slug: str,
    user_id: uuid.UUID,
    role: str,
    current_user: User,
) -> dict:
    valid_roles = ["admin", "member", "viewer"]
    if role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    org = await _get_org_or_404(db, org_slug)

    # User being added must already be an org member
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.org_id == org.id,
            OrganizationMember.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be a member of the organization before being added to a workspace",
        )

    workspace = await _get_workspace_or_404(db, org.id, workspace_slug)
    await _require_workspace_role(db, workspace.id, current_user.id, ["admin"])

    # Check not already a member
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this workspace",
        )

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user_id,
        role=role,
        joined_at=datetime.now(timezone.utc),
    )
    db.add(member)
    await db.flush()

    # Fetch user details for response
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    return {
        "id": member.id,
        "workspace_id": member.workspace_id,
        "user_id": member.user_id,
        "role": member.role,
        "joined_at": member.joined_at,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
    }


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _get_org_or_404(db: AsyncSession, slug: str) -> Organization:
    result = await db.execute(
        select(Organization).where(
            Organization.slug == slug,
            Organization.is_active == True,
        )
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return org


async def _get_workspace_or_404(
    db: AsyncSession,
    org_id: uuid.UUID,
    slug: str,
) -> Workspace:
    result = await db.execute(
        select(Workspace).where(
            Workspace.org_id == org_id,
            Workspace.slug == slug,
            Workspace.is_archived == False,
        )
    )
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return workspace


async def _require_workspace_member(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
) -> WorkspaceMember:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )
    return member


async def _require_workspace_role(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    allowed_roles: list[str],
) -> WorkspaceMember:
    member = await _require_workspace_member(db, workspace_id, user_id)
    if member.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This action requires one of these roles: {', '.join(allowed_roles)}",
        )
    return member