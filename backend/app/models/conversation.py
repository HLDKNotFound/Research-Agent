import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.message import Message
    from app.models.run import Run


class Conversation(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Business conversation model. Decoupled from runtime LangGraph thread."""
    __tablename__ = "conversations"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")

    # Reference only to the agent execution thread (persisted separately by LangGraph checkpointer)
    langgraph_thread_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="conversations")
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    runs: Mapped[List["Run"]] = relationship(
        "Run",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_conversations_project_created", "project_id", "created_at"),
        Index("idx_conversations_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} project={self.project_id} title={self.title}>"
