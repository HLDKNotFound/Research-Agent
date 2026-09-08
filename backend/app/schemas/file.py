import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.common import BaseDTO


class FileCreateDTO(BaseDTO):
    project_id: uuid.UUID
    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=1, max_length=100)
    size_bytes: int = Field(default=0, ge=0)
    storage_provider: str = Field(default="local")
    storage_key: str = Field(...)
    checksum: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class FileUpdateDTO(BaseDTO):
    status: Optional[str] = None
    page_count: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class FileResponseDTO(BaseDTO):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID] = None
    filename: str
    mime_type: str
    size_bytes: int
    storage_provider: str
    storage_key: str
    status: str
    page_count: Optional[int] = None
    checksum: Optional[str] = None
    idempotency_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata_")
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class FileChunkCreateDTO(BaseDTO):
    file_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    token_count: Optional[int] = None
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None


class FileChunkResponseDTO(BaseDTO):
    id: uuid.UUID
    file_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    token_count: Optional[int] = None
    created_at: datetime


class VectorFilterDTO(BaseDTO):
    """Metadata filtering criteria for vector similarity queries."""
    project_id: uuid.UUID
    file_ids: Optional[List[uuid.UUID]] = None
    mime_types: Optional[List[str]] = None
    page_numbers: Optional[List[int]] = None
    min_score: Optional[float] = None
    top_k: int = Field(default=5, ge=1, le=50)
