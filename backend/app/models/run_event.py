import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.core.database import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.run import Run


class RunEvent(Base, UUIDMixin):
    """Fine-grained runtime execution events recorded for streaming, debugging, and auditing."""
    __tablename__ = "run_events"

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    run: Mapped["Run"] = relationship("Run", back_populates="events")

    __table_args__ = (
        Index("idx_run_events_run_created", "run_id", "created_at"),
        Index("idx_run_events_run_type", "run_id", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<RunEvent id={self.id} run={self.run_id} type={self.event_type}>"
