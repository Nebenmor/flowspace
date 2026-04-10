import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


class OrganizationCreateRequest(BaseModel):
    name: str
    slug: str | None = None  # auto-generated from name if not provided

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Organization name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Organization name must be under 255 characters")
        return v

    @field_validator("slug")
    @classmethod
    def slug_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().lower()
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Slug can only contain letters, numbers, hyphens, underscores")
        if len(v) > 100:
            raise ValueError("Slug must be under 100 characters")
        return v


class OrganizationUpdateRequest(BaseModel):
    name: str | None = None
    logo_url: str | None = None


class MemberResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str
    joined_at: datetime
    email: str
    username: str
    full_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None
    owner_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrganizationDetailResponse(OrganizationResponse):
    members: list[MemberResponse] = []