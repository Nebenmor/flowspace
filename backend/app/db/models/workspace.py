import uuid
from sqlalchemy import String, Boolean, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.models.base import TimeStampedBase
from datetime import datetime

class Workspace(TimeStampedBase):
    __tablename__ = "workspaces"
    __table_args__ = (UniqueConstraint("org_id", "slug"),)

    org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None]
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    organization: Mapped["Organization"] = relationship(back_populates="workspaces")
    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace")
    tasks: Mapped[list["Task"]] = relationship(back_populates="workspace")


class WorkspaceMember(TimeStampedBase):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id"),)

    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # admin, member, viewer
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    workspace: Mapped["Workspace"] = relationship(back_populates="members")