import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class InvitationAcceptRequest(BaseModel):
    token: str


class InvitationResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    email: str
    role: str
    invited_by: uuid.UUID
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}