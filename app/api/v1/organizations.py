import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationUpdateRequest,
    OrganizationResponse,
    OrganizationDetailResponse,
    MemberResponse,
)
from app.services.organization_service import (
    create_organization,
    get_organization,
    list_user_organizations,
    update_organization,
    delete_organization,
    get_org_members,
    update_member_role,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_org(
    data: OrganizationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await create_organization(db, data, current_user)


@router.get("", response_model=list[OrganizationResponse])
async def list_orgs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_user_organizations(db, current_user)


@router.get("/{slug}", response_model=OrganizationResponse)
async def get_org(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_organization(db, slug, current_user)


@router.patch("/{slug}", response_model=OrganizationResponse)
async def update_org(
    slug: str,
    data: OrganizationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await update_organization(db, slug, data, current_user)


@router.delete("/{slug}", status_code=204)
async def delete_org(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await delete_organization(db, slug, current_user)


@router.get("/{slug}/members", response_model=list[MemberResponse])
async def list_members(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_org_members(db, slug, current_user)


@router.patch("/{slug}/members/{user_id}/role", response_model=MemberResponse)
async def change_member_role(
    slug: str,
    user_id: uuid.UUID,
    role: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await update_member_role(db, slug, user_id, role, current_user)