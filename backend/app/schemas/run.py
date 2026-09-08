import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import Field
from app.schemas.common import BaseDTO


class RunCreateDTO(BaseDTO):
    project_id: uuid.UUID
    prompt: str = Field(..., min_length=1)
    conversation_id: Optional[uuid.UUID] = None
    file_ids: Optional[List[uuid.UUID]] = None
    idempotency_key: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class RunUpdateDTO(BaseDTO):
    status: Optional[str] = None
    current_step: Optional[str] = None
    progress_pct: Optional[int] = None
    duration_ms: Optional[int] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None


class RunStepCreateDTO(BaseDTO):
    run_id: uuid.UUID
    agent_name: str
    step_name: str
    status: str = "running"
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RunStepResponseDTO(BaseDTO):
    id: uuid.UUID
    run_id: uuid.UUID
    agent_name: str
    step_name: str
    status: str
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RunEventCreateDTO(BaseDTO):
    run_id: uuid.UUID
    event_type: str
    agent_name: Optional[str] = None
    step_number: int = 0
    payload: Optional[Dict[str, Any]] = None


class RunEventResponseDTO(BaseDTO):
    id: uuid.UUID
    run_id: uuid.UUID
    event_type: str
    agent_name: Optional[str] = None
    step_number: int
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime


class RunResponseDTO(BaseDTO):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    prompt: str
    status: str
    current_step: Optional[str] = None
    progress_pct: int
    retry_count: int
    max_retries: int
    idempotency_key: Optional[str] = None
    langgraph_thread_id: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    steps: Optional[List[RunStepResponseDTO]] = None
