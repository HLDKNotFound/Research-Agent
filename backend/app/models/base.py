import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from sqlalchemy import DateTime, TypeDecorator, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON
from app.core.database import Base
from app.core.config import settings

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False


class VectorType(TypeDecorator):
    """
    Cross-dialect Vector type:
    Uses PostgreSQL pgvector.sqlalchemy.Vector when on PostgreSQL,
    and falls back to JSON-serialized array for SQLite / test environments.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: Optional[int] = None, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.dim = dim or settings.EMBEDDING_DIMENSION

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name == "postgresql" and HAS_PGVECTOR:
            return value
        if isinstance(value, (list, tuple)):
            return list(value)
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        return value


class TimestampMixin:
    """Provides created_at and updated_at timestamps in UTC."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Provides soft-delete capability with deleted_at timestamp."""
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class UUIDMixin:
    """Standardized UUID primary key mixin using native SQLAlchemy 2.0 Uuid."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
