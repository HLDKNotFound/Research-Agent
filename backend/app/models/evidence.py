import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON
from app.core.database import Base
from app.models.base import UUIDMixin

if TYPE_CHECKING:
    from app.models.run import Run
    from app.models.file import File
    from app.models.report import Citation


class Evidence(Base, UUIDMixin):
    """Normalized evidence item extracted by File Agent, Web Agent, or Data Analyst."""
    __tablename__ = "evidence"

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    file_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("file_chunks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
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
    run: Mapped["Run"] = relationship("Run", back_populates="evidences")
    file: Mapped[Optional["File"]] = relationship("File", back_populates="evidences")
    citations: Mapped[List["Citation"]] = relationship("Citation", back_populates="evidence")

    __table_args__ = (
        Index("idx_evidence_run_type", "run_id", "type"),
        Index("idx_evidence_run_created", "run_id", "created_at"),
        Index("idx_evidence_run_score", "run_id", "relevance_score"),
    )

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} run={self.run_id} type={self.type}>"
