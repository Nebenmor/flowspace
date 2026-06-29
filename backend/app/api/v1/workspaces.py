import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.workspace import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceMemberResponse,
)
from app.services.workspace_service import (
    create_workspace,
    list_workspaces,
    get_workspace,
    update_workspace,
    archive_workspace,
    get_workspace_members,
    add_workspace_member,
)

router = APIRouter(
    prefix="/organizations/{org_slug}/workspaces",
    tags=["Workspaces"],
)


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_ws(
    org_slug: str,
    data: WorkspaceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await create_workspace(db, org_slug, data, current_user)


@router.get("", response_model=list[WorkspaceResponse])
async def list_ws(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_workspaces(db, org_slug, current_user)


@router.get("/{workspace_slug}", response_model=WorkspaceResponse)
async def get_ws(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_workspace(db, org_slug, workspace_slug, current_user)


@router.patch("/{workspace_slug}", response_model=WorkspaceResponse)
async def update_ws(
    org_slug: str,
    workspace_slug: str,
    data: WorkspaceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await update_workspace(db, org_slug, workspace_slug, data, current_user)


@router.delete("/{workspace_slug}", status_code=204)
async def archive_ws(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await archive_workspace(db, org_slug, workspace_slug, current_user)


@router.get("/{workspace_slug}/members", response_model=list[WorkspaceMemberResponse])
async def list_ws_members(
    org_slug: str,
    workspace_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_workspace_members(db, org_slug, workspace_slug, current_user)


@router.post("/{workspace_slug}/members", response_model=WorkspaceMemberResponse, status_code=201)
async def add_ws_member(
    org_slug: str,
    workspace_slug: str,
    user_id: uuid.UUID,
    role: str = "member",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await add_workspace_member(db, org_slug, workspace_slug, user_id, role, current_user)