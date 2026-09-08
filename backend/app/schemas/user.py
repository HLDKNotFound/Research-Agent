import uuid
from datetime import datetime
from typing import Optional
from pydantic import EmailStr, Field
from app.schemas.common import BaseDTO


class UserCreateDTO(BaseDTO):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=72)
    name: Optional[str] = Field(None, max_length=255)
    avatar_url: Optional[str] = Field(None, max_length=2048)


class UserLoginDTO(BaseDTO):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., max_length=72)


class UserResponseDTO(BaseDTO):
    id: uuid.UUID
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponseDTO(BaseDTO):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponseDTO
