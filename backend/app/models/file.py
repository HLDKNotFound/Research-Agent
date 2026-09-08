import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    BigInteger,
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
from app.core.config import settings
from app.models.base import UUIDMixin, TimestampMixin, SoftDeleteMixin, VectorType

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.evidence import Evidence


class File(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """File metadata and object storage reference. Decoupled from binary content."""
    __tablename__ = "files"

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

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # Object storage location
    storage_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)

    # Processing lifecycle status
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded", index=True)

    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    metadata_: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
        default=dict,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="files")
    chunks: Mapped[List["FileChunk"]] = relationship(
        "FileChunk",
        back_populates="file",
        cascade="all, delete-orphan",
        order_by="FileChunk.chunk_index",
    )
    evidences: Mapped[List["Evidence"]] = relationship(
        "Evidence",
        back_populates="file",
    )

    __table_args__ = (
        Index("idx_files_project_created", "project_id", "created_at"),
        Index("idx_files_project_status", "project_id", "status"),
        Index("idx_files_deleted_at", "deleted_at"),
        UniqueConstraint("project_id", "idempotency_key", name="uq_files_project_idempotency"),
    )

    def __repr__(self) -> str:
        return f"<File id={self.id} filename={self.filename} status={self.status}>"


class FileChunk(Base, UUIDMixin):
    """Text chunk extracted from file with vector embedding for semantic search."""
    __tablename__ = "file_chunks"

    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Dynamic embedding dimension vector column
    embedding: Mapped[Optional[Any]] = mapped_column(
        VectorType(dim=settings.EMBEDDING_DIMENSION),
        nullable=True,
    )

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
    file: Mapped["File"] = relationship("File", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("file_id", "chunk_index", name="uq_file_chunks_file_index"),
        Index("idx_file_chunks_file_page", "file_id", "page_number"),
    )

    def __repr__(self) -> str:
        return f"<FileChunk id={self.id} file_id={self.file_id} index={self.chunk_index}>"
