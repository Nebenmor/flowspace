import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, field_validator


class CustomFieldCreateRequest(BaseModel):
    name: str
    field_type: str
    options: list[str] | None = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Field name cannot be empty")
        if len(v) > 100:
            raise ValueError("Field name must be under 100 characters")
        return v

    @field_validator("field_type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        valid = ["text", "number", "date", "boolean", "select"]
        if v not in valid:
            raise ValueError(f"Field type must be one of: {', '.join(valid)}")
        return v


class CustomFieldResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    field_type: str
    options: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomFieldValueSetRequest(BaseModel):
    value: Any

    @field_validator("value")
    @classmethod
    def value_not_none(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Value cannot be null")
        return v


class CustomFieldValueResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    field_id: uuid.UUID
    value: Any
    created_at: datetime

    model_config = {"from_attributes": True}