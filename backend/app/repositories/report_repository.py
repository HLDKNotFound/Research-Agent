import uuid
from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.report import Citation, Report, ReportSection
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class ReportRepository(BaseRepository[Report]):
    def __init__(self, session: AsyncSession):
        super().__init__(Report, session)

    async def get_by_run(self, run_id: uuid.UUID) -> Optional[Report]:
        query = (
            select(Report)
            .options(
                selectinload(Report.sections).selectinload(ReportSection.citations)
            )
            .where(Report.run_id == run_id, Report.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_with_sections_and_citations(self, report_id: uuid.UUID) -> Optional[Report]:
        query = (
            select(Report)
            .options(
                selectinload(Report.sections).selectinload(ReportSection.citations)
            )
            .where(Report.id == report_id, Report.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> Sequence[Report]:
        query = (
            select(Report)
            .where(Report.project_id == project_id, Report.deleted_at.is_(None))
            .order_by(Report.created_at.desc())
        )
        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_section(self, section_id: uuid.UUID) -> Optional[ReportSection]:
        query = (
            select(ReportSection)
            .options(selectinload(ReportSection.citations))
            .where(ReportSection.id == section_id)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def add_section(self, section: ReportSection) -> ReportSection:
        self.session.add(section)
        await self.session.flush()
        return section

    async def add_citation(self, citation: Citation) -> Citation:
        self.session.add(citation)
        await self.session.flush()
        return citation
