import uuid
from datetime import datetime
from typing import Optional
from pydantic import Field
from app.schemas.common import BaseDTO


class ConversationCreateDTO(BaseDTO):
    project_id: uuid.UUID
    title: str = Field(default="New Conversation", min_length=1, max_length=255)
    langgraph_thread_id: Optional[str] = None


class ConversationUpdateDTO(BaseDTO):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    langgraph_thread_id: Optional[str] = None


class ConversationResponseDTO(BaseDTO):
    id: uuid.UUID
    project_id: uuid.UUID
    created_by_user_id: Optional[uuid.UUID] = None
    title: str
    langgraph_thread_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
