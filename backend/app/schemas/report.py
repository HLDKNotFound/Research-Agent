import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import Field
from app.schemas.common import BaseDTO


class CitationCreateDTO(BaseDTO):
    report_section_id: uuid.UUID
    evidence_id: uuid.UUID
    citation_text: str = Field(..., min_length=1)
    position: int = Field(default=1)


class CitationResponseDTO(BaseDTO):
    id: uuid.UUID
    report_section_id: uuid.UUID
    evidence_id: uuid.UUID
    citation_text: str
    position: int
    created_at: datetime


class ReportSectionCreateDTO(BaseDTO):
    report_id: uuid.UUID
    section_key: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    section_order: int
    status: str = "completed"


class ReportSectionUpdateDTO(BaseDTO):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None


class ReportSectionResponseDTO(BaseDTO):
    id: uuid.UUID
    report_id: uuid.UUID
    section_key: str
    title: str
    content: str
    section_order: int
    status: str
    created_at: datetime
    updated_at: datetime
    citations: Optional[List[CitationResponseDTO]] = None


class ReportCreateDTO(BaseDTO):
    run_id: uuid.UUID
    project_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    format: str = "markdown"
    status: str = "completed"


class ReportUpdateDTO(BaseDTO):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    version: Optional[int] = None


class ReportResponseDTO(BaseDTO):
    id: uuid.UUID
    run_id: uuid.UUID
    project_id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID] = None
    title: str
    status: str
    version: int
    content: str
    format: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    sections: Optional[List[ReportSectionResponseDTO]] = None
