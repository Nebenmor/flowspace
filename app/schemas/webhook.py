import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator


class WebhookCreateRequest(BaseModel):
    name: str
    url: str
    events: list[str]

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Webhook name cannot be empty")
        if len(v) > 255:
            raise ValueError("Webhook name must be under 255 characters")
        return v

    @field_validator("url")
    @classmethod
    def url_valid(cls, v: str) -> str:
        if not v.startswith("https://") and not v.startswith("http://"):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("events")
    @classmethod
    def events_valid(cls, v: list[str]) -> list[str]:
        valid_events = [
            "task.created",
            "task.updated",
            "task.deleted",
            "task.assigned",
            "task.completed",
            "member.invited",
            "member.joined",
        ]
        for event in v:
            if event not in valid_events:
                raise ValueError(
                    f"Invalid event '{event}'. "
                    f"Valid events: {', '.join(valid_events)}"
                )
        if len(v) == 0:
            raise ValueError("At least one event must be specified")
        return v


class WebhookUpdateRequest(BaseModel):
    name: str | None = None
    events: list[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    webhook_id: uuid.UUID
    event_type: str
    status: str
    response_status: int | None
    attempts: int
    next_retry_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}