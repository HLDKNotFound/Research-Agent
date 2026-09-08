import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import Field
from app.schemas.common import BaseDTO


class ProjectCreateDTO(BaseDTO):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)


class ProjectUpdateDTO(BaseDTO):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)


class TransferOwnershipDTO(BaseDTO):
    new_owner_user_id: uuid.UUID


class ProjectMemberDTO(BaseDTO):
    user_id: uuid.UUID
    project_id: uuid.UUID
    role: str
    created_at: datetime


class AddMemberDTO(BaseDTO):
    user_id: uuid.UUID
    role: str = Field(default="member", pattern="^(owner|admin|member|viewer)$")


class ProjectResponseDTO(BaseDTO):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    members: Optional[List[ProjectMemberDTO]] = None
