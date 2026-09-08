import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation import Conversation
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class ConversationRepository(BaseRepository[Conversation]):
    def __init__(self, session: AsyncSession):
        super().__init__(Conversation, session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> Sequence[Conversation]:
        query = (
            select(Conversation)
            .where(
                Conversation.project_id == project_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.created_at.desc())
        )
        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_thread_id(self, langgraph_thread_id: str) -> Optional[Conversation]:
        query = select(Conversation).where(
            Conversation.langgraph_thread_id == langgraph_thread_id,
            Conversation.deleted_at.is_(None),
        )
        result = await self.session.execute(query)
        return result.scalars().first()
