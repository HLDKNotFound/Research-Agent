import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.conversation import (
    ConversationCreateDTO,
    ConversationResponseDTO,
    ConversationUpdateDTO,
)
from app.schemas.message import MessageCreateDTO, MessageResponseDTO
from app.services.conversation_service import ConversationService

router = APIRouter(tags=["Conversations"])


@router.get(
    "/api/v1/projects/{project_id}/conversations",
    response_model=PaginatedResponse[ConversationResponseDTO],
    summary="List conversations in a project",
)
async def list_conversations(
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.list_conversations(current_user.id, project_id, pagination)


@router.post(
    "/api/v1/projects/{project_id}/conversations",
    response_model=ConversationResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation in a project",
)
async def create_conversation(
    project_id: uuid.UUID,
    dto: ConversationCreateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    # Ensure project_id matches path
    dto.project_id = project_id
    return await service.create_conversation(current_user.id, dto)


@router.get(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationResponseDTO,
    summary="Get conversation details",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    return await service.get_conversation(current_user.id, conversation_id)


@router.patch(
    "/api/v1/conversations/{conversation_id}",
    response_model=ConversationResponseDTO,
    summary="Update conversation title or LangGraph thread ID",
)
async def update_conversation(
    conversation_id: uuid.UUID,
    dto: ConversationUpdateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    return await service.update_conversation(current_user.id, conversation_id, dto)


@router.delete(
    "/api/v1/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    await service.delete_conversation(current_user.id, conversation_id)
    return None


@router.get(
    "/api/v1/conversations/{conversation_id}/messages",
    response_model=list[MessageResponseDTO],
    summary="List messages in a conversation",
)
async def list_messages(
    conversation_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.list_messages(current_user.id, conversation_id, pagination)


@router.post(
    "/api/v1/conversations/{conversation_id}/messages",
    response_model=MessageResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add a message to a conversation",
)
async def add_message(
    conversation_id: uuid.UUID,
    dto: MessageCreateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    dto.conversation_id = conversation_id
    return await service.add_message(current_user.id, dto)
