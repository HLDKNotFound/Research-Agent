import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.run import Run
    from app.models.evidence import Evidence


class Report(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Synthesized research report containing structured sections and academic citations."""
    __tablename__ = "reports"

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
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

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(String(50), nullable=False, default="markdown")

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="reports")
    run: Mapped["Run"] = relationship("Run", back_populates="report")
    sections: Mapped[List["ReportSection"]] = relationship(
        "ReportSection",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportSection.section_order",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_reports_project_created", "project_id", "created_at"),
        Index("idx_reports_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} title={self.title} version={self.version}>"


class ReportSection(Base, UUIDMixin, TimestampMixin):
    """Modular report section allowing targeted regeneration without regenerating the whole report."""
    __tablename__ = "report_sections"

    report_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    section_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="completed")

    # Relationships
    report: Mapped["Report"] = relationship("Report", back_populates="sections")
    citations: Mapped[List["Citation"]] = relationship(
        "Citation",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Citation.position",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_report_sections_order", "report_id", "section_order"),
    )

    def __repr__(self) -> str:
        return f"<ReportSection id={self.id} title={self.title} order={self.section_order}>"


class Citation(Base, UUIDMixin):
    """Academic citation mapping a report section claim to verified evidence."""
    __tablename__ = "citations"

    report_section_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("report_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evidence.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    citation_text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    section: Mapped["ReportSection"] = relationship("ReportSection", back_populates="citations")
    evidence: Mapped["Evidence"] = relationship("Evidence", back_populates="citations")

    __table_args__ = (
        Index("idx_citations_section_position", "report_section_id", "position"),
    )

    def __repr__(self) -> str:
        return f"<Citation id={self.id} section={self.report_section_id} evidence={self.evidence_id}>"
