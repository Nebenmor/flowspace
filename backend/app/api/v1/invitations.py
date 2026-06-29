import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.invitation import (
    InvitationCreateRequest,
    InvitationResponse,
)
from app.services.invitation_service import (
    send_invitation,
    accept_invitation,
    list_invitations,
    revoke_invitation,
)

router = APIRouter(tags=["Invitations"])


@router.post(
    "/organizations/{org_slug}/invitations",
    response_model=InvitationResponse,
    status_code=201,
)
async def invite_member(
    org_slug: str,
    data: InvitationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await send_invitation(db, org_slug, data, current_user)


@router.get(
    "/organizations/{org_slug}/invitations",
    response_model=list[InvitationResponse],
)
async def get_invitations(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await list_invitations(db, org_slug, current_user)


@router.delete(
    "/organizations/{org_slug}/invitations/{invitation_id}",
    status_code=204,
)
async def cancel_invitation(
    org_slug: str,
    invitation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await revoke_invitation(db, org_slug, invitation_id, current_user)


@router.post("/invitations/accept", response_model=dict)
async def accept_invite(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    await accept_invitation(db, token, current_user)
    return {"message": "Invitation accepted successfully"}