import uuid
from typing import List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.evidence import Evidence
from app.repositories.base import BaseRepository
from app.schemas.evidence import EvidenceFilterDTO


class EvidenceRepository(BaseRepository[Evidence]):
    def __init__(self, session: AsyncSession):
        super().__init__(Evidence, session)

    async def list_by_run(
        self,
        filters: EvidenceFilterDTO,
    ) -> Sequence[Evidence]:
        query = select(Evidence).where(Evidence.run_id == filters.run_id)

        if filters.type:
            query = query.where(Evidence.type == filters.type)
        if filters.file_id:
            query = query.where(Evidence.file_id == filters.file_id)
        if filters.min_score is not None:
            query = query.where(Evidence.relevance_score >= filters.min_score)

        query = query.order_by(Evidence.relevance_score.desc().nullslast(), Evidence.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_batch(self, evidences: List[Evidence]) -> List[Evidence]:
        self.session.add_all(evidences)
        await self.session.flush()
        return evidences
