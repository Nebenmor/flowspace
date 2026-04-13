import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


class WorkspaceCreateRequest(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Workspace name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Workspace name must be under 255 characters")
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


class WorkspaceUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class WorkspaceMemberResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    email: str
    username: str
    full_name: str | None
    avatar_url: str | None

    model_config = {"from_attributes": True}


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    created_by: uuid.UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}