import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ActivityResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    actor_id: uuid.UUID
    action: str
    old_value: Any
    new_value: Any
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int
    page: int
    page_size: int
    has_next: bool