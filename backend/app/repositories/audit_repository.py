import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> Sequence[AuditLog]:
        query = (
            select(AuditLog)
            .where(AuditLog.project_id == project_id)
            .order_by(AuditLog.created_at.desc())
        )
        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> Sequence[AuditLog]:
        query = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
        )
        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()
