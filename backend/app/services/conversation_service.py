import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import cache_service, CacheService
from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.conversation import (
    ConversationCreateDTO,
    ConversationResponseDTO,
    ConversationUpdateDTO,
)
from app.schemas.message import MessageCreateDTO, MessageResponseDTO


class ConversationService:
    """Conversation and Message management service with caching and LangGraph thread decoupling."""

    def __init__(self, session: AsyncSession, cache: Optional[CacheService] = None):
        self.session = session
        self.repo = ConversationRepository(session)
        self.msg_repo = MessageRepository(session)
        self.project_repo = ProjectRepository(session)
        self.cache = cache or cache_service

    async def _check_access(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.project_repo.get_membership(project_id, user_id)
        if not membership:
            raise PermissionDeniedError("You do not have access to this project.")

    async def create_conversation(
        self,
        user_id: uuid.UUID,
        dto: ConversationCreateDTO,
    ) -> ConversationResponseDTO:
        await self._check_access(dto.project_id, user_id)

        conversation = Conversation(
            project_id=dto.project_id,
            created_by_user_id=user_id,
            title=dto.title,
            langgraph_thread_id=dto.langgraph_thread_id,
        )
        created = await self.repo.create(conversation)
        await self.cache.delete_pattern(f"{self.cache.version}:conversations:list:{dto.project_id}:*")

        return ConversationResponseDTO.model_validate(created)

    async def get_conversation(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> ConversationResponseDTO:
        cache_key = self.cache.build_key("conversations", "detail", str(conversation_id))
        cached = await self.cache.get(cache_key)
        if cached:
            return ConversationResponseDTO.model_validate(cached)

        conv = await self.repo.get_by_id(conversation_id)
        if not conv:
            raise EntityNotFoundError("Conversation", conversation_id)

        await self._check_access(conv.project_id, user_id)

        response = ConversationResponseDTO.model_validate(conv)
        await self.cache.set(cache_key, response.model_dump(mode="json"))
        return response

    async def list_conversations(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> PaginatedResponse[ConversationResponseDTO]:
        await self._check_access(project_id, user_id)
        pagination = params or PaginationParams()

        cache_key = self.cache.build_key(
            "conversations",
            "list",
            str(project_id),
            pagination.page,
            pagination.limit,
        )
        cached = await self.cache.get(cache_key)
        if cached:
            return PaginatedResponse[ConversationResponseDTO].model_validate(cached)

        convs = await self.repo.list_by_project(project_id, pagination)
        total = await self.repo.count(project_id=project_id)

        items = [ConversationResponseDTO.model_validate(c) for c in convs]
        response = PaginatedResponse.create(items, total, pagination)

        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=120)
        return response

    async def add_message(
        self,
        user_id: uuid.UUID,
        dto: MessageCreateDTO,
    ) -> MessageResponseDTO:
        conv = await self.repo.get_by_id(dto.conversation_id)
        if not conv:
            raise EntityNotFoundError("Conversation", dto.conversation_id)

        await self._check_access(conv.project_id, user_id)

        message = Message(
            conversation_id=dto.conversation_id,
            role=dto.role,
            content=dto.content,
            model=dto.model,
            input_tokens=dto.input_tokens,
            output_tokens=dto.output_tokens,
            metadata_=dto.metadata or {},
        )
        created = await self.msg_repo.create(message)

        # Invalidate messages cache for this conversation
        await self.cache.delete_pattern(f"{self.cache.version}:messages:list:{dto.conversation_id}:*")

        return MessageResponseDTO.model_validate(created)

    async def list_messages(
        self,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> List[MessageResponseDTO]:
        conv = await self.repo.get_by_id(conversation_id)
        if not conv:
            raise EntityNotFoundError("Conversation", conversation_id)

        await self._check_access(conv.project_id, user_id)
        pagination = params or PaginationParams(limit=100)

        cache_key = self.cache.build_key(
            "messages",
            "list",
            str(conversation_id),
            pagination.page,
            pagination.limit,
        )
        cached = await self.cache.get(cache_key)
        if cached:
            return [MessageResponseDTO.model_validate(m) for m in cached]

        messages = await self.msg_repo.list_by_conversation(conversation_id, pagination)
        items = [MessageResponseDTO.model_validate(m) for m in messages]

        await self.cache.set(cache_key, [m.model_dump(mode="json") for m in items], ttl_seconds=60)
        return items

    async def delete_conversation(self, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
        conv = await self.repo.get_by_id(conversation_id)
        if not conv:
            raise EntityNotFoundError("Conversation", conversation_id)

        await self._check_access(conv.project_id, user_id)
        await self.repo.soft_delete(conv)
        await self.cache.invalidate_conversation(conversation_id, project_id=conv.project_id)
