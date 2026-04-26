import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


class LabelCreateRequest(BaseModel):
    name: str
    color: str = "#6366f1"

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Label name cannot be empty")
        if len(v) > 100:
            raise ValueError("Label name must be under 100 characters")
        return v

    @field_validator("color")
    @classmethod
    def color_valid(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("#") or len(v) != 7:
            raise ValueError("Color must be a valid hex code e.g. #FF5733")
        return v


class LabelResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    color: str
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskLabelRequest(BaseModel):
    label_id: uuid.UUID