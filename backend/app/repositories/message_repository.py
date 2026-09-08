import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class MessageRepository(BaseRepository[Message]):
    def __init__(self, session: AsyncSession):
        super().__init__(Message, session)

    async def list_by_conversation(
        self,
        conversation_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> Sequence[Message]:
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()
