import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import ConfigDict, Field
from app.schemas.common import BaseDTO


class MessageCreateDTO(BaseDTO):
    conversation_id: uuid.UUID
    role: str = Field(..., pattern="^(user|assistant|system|agent|tool)$")
    content: str = Field(..., min_length=1)
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    attachments: Optional[List[uuid.UUID]] = None


class MessageResponseDTO(BaseDTO):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, validation_alias="metadata_")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True, populate_by_name=True)
