import uuid
from sqlalchemy import String, Boolean, Float, ForeignKey, UniqueConstraint, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import TimeStampedBase
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR

class Task(TimeStampedBase):
    __tablename__ = "tasks"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tasks.id"))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="todo")
    priority: Mapped[str] = mapped_column(String(50), default="medium")
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[float] = mapped_column(Float, default=0.0)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    workspace: Mapped["Workspace"] = relationship(back_populates="tasks")
    subtasks: Mapped[list["Task"]] = relationship(back_populates="parent")
    parent: Mapped["Task | None"] = relationship(back_populates="subtasks", remote_side="Task.id")
    labels: Mapped[list["Label"]] = relationship(secondary="task_labels", back_populates="tasks")
    activities: Mapped[list["TaskActivity"]] = relationship(back_populates="task")
    comments: Mapped[list["Comment"]] = relationship(back_populates="task")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="task")
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)



class TaskDependency(TimeStampedBase):
    __tablename__ = "task_dependencies"
    __table_args__ = (UniqueConstraint("task_id", "depends_on_id"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    depends_on_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(50), default="blocks")


class Label(TimeStampedBase):
    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)

    tasks: Mapped[list["Task"]] = relationship(secondary="task_labels", back_populates="labels")


class TaskLabel(TimeStampedBase):
    __tablename__ = "task_labels"
    __table_args__ = (UniqueConstraint("task_id", "label_id"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    label_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("labels.id"), nullable=False)


class CustomField(TimeStampedBase):
    __tablename__ = "custom_fields"

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[str] = mapped_column(String(50), nullable=False)
    options: Mapped[dict | None] = mapped_column(JSONB)


class TaskCustomFieldValue(TimeStampedBase):
    __tablename__ = "task_custom_field_values"
    __table_args__ = (UniqueConstraint("task_id", "field_id"),)

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    field_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("custom_fields.id"), nullable=False)
    value: Mapped[dict] = mapped_column(JSONB, nullable=False)