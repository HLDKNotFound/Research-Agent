import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.common import BaseDTO


class EvidenceCreateDTO(BaseDTO):
    run_id: uuid.UUID
    type: str = Field(..., pattern="^(file|web|generated)$")
    content: str = Field(..., min_length=1)
    file_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    page_number: Optional[int] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_domain: Optional[str] = None
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class EvidenceFilterDTO(BaseDTO):
    run_id: uuid.UUID
    type: Optional[str] = None
    min_score: Optional[float] = None
    file_id: Optional[uuid.UUID] = None


class EvidenceResponseDTO(BaseDTO):
    id: uuid.UUID
    run_id: uuid.UUID
    type: str
    content: str
    file_id: Optional[uuid.UUID] = None
    chunk_id: Optional[uuid.UUID] = None
    page_number: Optional[int] = None
    source_url: Optional[str] = None
    source_title: Optional[str] = None
    source_domain: Optional[str] = None
    relevance_score: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="metadata_")
    created_at: datetime
