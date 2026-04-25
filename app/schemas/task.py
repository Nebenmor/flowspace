import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator


class TaskCreateRequest(BaseModel):
    title: str
    description: str | None = None
    status: str = "todo"
    priority: str = "medium"
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None
    parent_id: uuid.UUID | None = None

    @field_validator("title")
    @classmethod
    def title_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Title cannot be empty")
        if len(v) > 500:
            raise ValueError("Title must be under 500 characters")
        return v

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str) -> str:
        valid = ["todo", "in_progress", "in_review", "done", "cancelled"]
        if v not in valid:
            raise ValueError(f"Status must be one of: {', '.join(valid)}")
        return v

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str) -> str:
        valid = ["urgent", "high", "medium", "low", "none"]
        if v not in valid:
            raise ValueError(f"Priority must be one of: {', '.join(valid)}")
        return v


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: uuid.UUID | None = None
    due_date: datetime | None = None

    @field_validator("status")
    @classmethod
    def status_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = ["todo", "in_progress", "in_review", "done", "cancelled"]
        if v not in valid:
            raise ValueError(f"Status must be one of: {', '.join(valid)}")
        return v

    @field_validator("priority")
    @classmethod
    def priority_valid(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = ["urgent", "high", "medium", "low", "none"]
        if v not in valid:
            raise ValueError(f"Priority must be one of: {', '.join(valid)}")
        return v


class TaskResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    parent_id: uuid.UUID | None
    title: str
    description: str | None
    status: str
    priority: str
    assignee_id: uuid.UUID | None
    created_by: uuid.UUID
    due_date: datetime | None
    completed_at: datetime | None
    position: float
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class TaskFilterParams(BaseModel):
    status: str | None = None
    priority: str | None = None
    assignee_id: uuid.UUID | None = None
    is_overdue: bool | None = None
    parent_id: uuid.UUID | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 20

class TaskDependencyCreateRequest(BaseModel):
    depends_on_id: uuid.UUID
    dependency_type: str = "blocks"

    @field_validator("dependency_type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        valid = ["blocks", "relates_to", "duplicates"]
        if v not in valid:
            raise ValueError(f"Dependency type must be one of: {', '.join(valid)}")
        return v


class TaskDependencyResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    depends_on_id: uuid.UUID
    dependency_type: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SubtaskResponse(TaskResponse):
    pass