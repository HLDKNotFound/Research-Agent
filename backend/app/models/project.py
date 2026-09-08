import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Index, String, Text, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.conversation import Conversation
    from app.models.file import File
    from app.models.run import Run
    from app.models.report import Report


class Project(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Project/Workspace tenant container."""
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    files: Mapped[List["File"]] = relationship(
        "File",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_projects_created_at", "created_at"),
        Index("idx_projects_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name}>"


class ProjectMember(Base):
    """Membership table defining workspace access and role."""
    __tablename__ = "project_members"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        default="member",
        nullable=False,
    )  # 'owner', 'admin', 'member', 'viewer'

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User", back_populates="project_memberships")

    __table_args__ = (
        Index("idx_project_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<ProjectMember project={self.project_id} user={self.user_id} role={self.role}>"
