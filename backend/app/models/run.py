import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.core.database import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.conversation import Conversation
    from app.models.evidence import Evidence
    from app.models.report import Report
    from app.models.run_event import RunEvent


class Run(Base, UUIDMixin):
    """Analysis Job Execution entity with robust state machine and idempotency."""
    __tablename__ = "runs"

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
    conversation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # State Machine: queued, planning, researching, analyzing, writing, reviewing, completed, failed, cancelled
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued", index=True)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Idempotency and Retries
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    # External reference to runtime LangGraph thread
    langgraph_thread_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    # Error handling
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )

    # Options, parameters, flags
    config: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        default=dict,
    )

    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="runs")
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation", back_populates="runs")
    steps: Mapped[List["RunStep"]] = relationship(
        "RunStep",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunStep.started_at",
        lazy="selectin",
    )
    events: Mapped[List["RunEvent"]] = relationship(
        "RunEvent",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunEvent.created_at",
        lazy="selectin",
    )
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="run",
        cascade="all, delete-orphan",
    )
    report: Mapped[Optional["Report"]] = relationship(
        "Report",
        back_populates="run",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_runs_project_created", "project_id", "created_at"),
        Index("idx_runs_project_status", "project_id", "status"),
        Index("idx_runs_conversation_created", "conversation_id", "created_at"),
        UniqueConstraint("project_id", "idempotency_key", name="uq_runs_project_idempotency"),
    )

    def __repr__(self) -> str:
        return f"<Run id={self.id} status={self.status} step={self.current_step}>"


class RunStep(Base, UUIDMixin):
    """Sub-agent step execution log within an analysis run."""
    __tablename__ = "run_steps"

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "input",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "output",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )

    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="steps")

    __table_args__ = (
        Index("idx_run_steps_run_started", "run_id", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<RunStep id={self.id} agent={self.agent_name} status={self.status}>"
