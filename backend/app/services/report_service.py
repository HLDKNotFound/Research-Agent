import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import cache_service, CacheService
from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.models.audit import AuditLog
from app.models.report import Citation, Report, ReportSection
from app.repositories.audit_repository import AuditRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.report import (
    CitationCreateDTO,
    CitationResponseDTO,
    ReportCreateDTO,
    ReportResponseDTO,
    ReportSectionCreateDTO,
    ReportSectionResponseDTO,
    ReportSectionUpdateDTO,
    ReportUpdateDTO,
)


class ReportService:
    """Report synthesis, modular section editing, citations, and Redis caching service."""

    def __init__(self, session: AsyncSession, cache: Optional[CacheService] = None):
        self.session = session
        self.repo = ReportRepository(session)
        self.project_repo = ProjectRepository(session)
        self.audit_repo = AuditRepository(session)
        self.cache = cache or cache_service

    async def _check_access(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.project_repo.get_membership(project_id, user_id)
        if not membership:
            raise PermissionDeniedError("You do not have access to this project.")

    async def create_report(
        self,
        user_id: uuid.UUID,
        dto: ReportCreateDTO,
    ) -> ReportResponseDTO:
        await self._check_access(dto.project_id, user_id)

        report = Report(
            run_id=dto.run_id,
            project_id=dto.project_id,
            created_by_user_id=user_id,
            title=dto.title,
            content=dto.content,
            format=dto.format,
            status=dto.status,
        )
        created = await self.repo.create(report)

        await self.cache.delete_pattern(f"{self.cache.version}:reports:list:{dto.project_id}:*")

        # Audit log
        await self.audit_repo.create(
            AuditLog(
                user_id=user_id,
                project_id=dto.project_id,
                action="report.create",
                resource_type="report",
                resource_id=str(created.id),
                payload={"title": dto.title, "run_id": str(dto.run_id)},
            )
        )

        full = await self.repo.get_with_sections_and_citations(created.id)
        return ReportResponseDTO.model_validate(full)

    async def list_reports(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> PaginatedResponse[ReportResponseDTO]:
        await self._check_access(project_id, user_id)
        pagination = params or PaginationParams()

        reports = await self.repo.list_by_project(project_id, pagination)
        total = await self.repo.count(project_id=project_id)

        items = [ReportResponseDTO.model_validate(r) for r in reports]
        return PaginatedResponse.create(items, total, pagination)

    async def get_report_by_run(
        self,
        user_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> ReportResponseDTO:
        cache_key = self.cache.build_key("reports", "by_run", str(run_id))
        cached = await self.cache.get(cache_key)
        if cached:
            response = ReportResponseDTO.model_validate(cached)
            await self._check_access(response.project_id, user_id)
            return response

        report = await self.repo.get_by_run(run_id)
        if not report:
            raise EntityNotFoundError("Report for Run", run_id)

        await self._check_access(report.project_id, user_id)

        response = ReportResponseDTO.model_validate(report)
        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=300)
        return response

    async def get_report(
        self,
        user_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> ReportResponseDTO:
        cache_key = self.cache.build_key("reports", "detail", str(report_id))
        cached = await self.cache.get(cache_key)
        if cached:
            response = ReportResponseDTO.model_validate(cached)
            await self._check_access(response.project_id, user_id)
            return response

        report = await self.repo.get_with_sections_and_citations(report_id)
        if not report:
            raise EntityNotFoundError("Report", report_id)

        await self._check_access(report.project_id, user_id)

        response = ReportResponseDTO.model_validate(report)
        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=300)
        return response

    async def update_report(
        self,
        user_id: uuid.UUID,
        report_id: uuid.UUID,
        dto: ReportUpdateDTO,
    ) -> ReportResponseDTO:
        report = await self.repo.get_by_id(report_id)
        if not report:
            raise EntityNotFoundError("Report", report_id)

        await self._check_access(report.project_id, user_id)

        if dto.title is not None:
            report.title = dto.title
        if dto.content is not None:
            report.content = dto.content
        if dto.status is not None:
            report.status = dto.status
        if dto.version is not None:
            report.version = dto.version

        await self.session.flush()
        await self.cache.invalidate_report(report.id, run_id=report.run_id, project_id=report.project_id)

        full = await self.repo.get_with_sections_and_citations(report_id)
        return ReportResponseDTO.model_validate(full)

    async def add_section(
        self,
        user_id: uuid.UUID,
        dto: ReportSectionCreateDTO,
    ) -> ReportSectionResponseDTO:
        report = await self.repo.get_by_id(dto.report_id)
        if not report:
            raise EntityNotFoundError("Report", dto.report_id)
        await self._check_access(report.project_id, user_id)

        section = ReportSection(
            report_id=dto.report_id,
            section_key=dto.section_key,
            title=dto.title,
            content=dto.content,
            section_order=dto.section_order,
            status=dto.status,
        )
        created = await self.repo.add_section(section)
        await self.cache.invalidate_report(report.id, run_id=report.run_id, project_id=report.project_id)

        full_section = await self.repo.get_section(created.id)
        return ReportSectionResponseDTO.model_validate(full_section)

    async def add_citation(
        self,
        user_id: uuid.UUID,
        dto: CitationCreateDTO,
    ) -> CitationResponseDTO:
        section = await self.repo.get_section(dto.report_section_id)
        if not section:
            raise EntityNotFoundError("ReportSection", dto.report_section_id)

        report = await self.repo.get_by_id(section.report_id)
        if not report:
            raise EntityNotFoundError("Report", section.report_id)
        await self._check_access(report.project_id, user_id)

        citation = Citation(
            report_section_id=dto.report_section_id,
            evidence_id=dto.evidence_id,
            citation_text=dto.citation_text,
            position=dto.position,
        )
        created = await self.repo.add_citation(citation)
        await self.cache.invalidate_report(report.id, run_id=report.run_id, project_id=report.project_id)

        return CitationResponseDTO.model_validate(created)

    async def update_section(
        self,
        user_id: uuid.UUID,
        section_id: uuid.UUID,
        dto: ReportSectionUpdateDTO,
    ) -> ReportSectionResponseDTO:
        section = await self.repo.get_section(section_id)
        if not section:
            raise EntityNotFoundError("ReportSection", section_id)

        report = await self.repo.get_by_id(section.report_id)
        if not report:
            raise EntityNotFoundError("Report", section.report_id)
        await self._check_access(report.project_id, user_id)

        if dto.title is not None:
            section.title = dto.title
        if dto.content is not None:
            section.content = dto.content
        if dto.status is not None:
            section.status = dto.status

        await self.session.flush()
        await self.cache.invalidate_report(report.id, run_id=report.run_id, project_id=report.project_id)

        updated = await self.repo.get_section(section_id)
        return ReportSectionResponseDTO.model_validate(updated)

    async def delete_report(self, user_id: uuid.UUID, report_id: uuid.UUID) -> None:
        report = await self.repo.get_by_id(report_id)
        if not report:
            raise EntityNotFoundError("Report", report_id)

        await self._check_access(report.project_id, user_id)
        await self.repo.soft_delete(report)
        await self.cache.invalidate_report(report.id, run_id=report.run_id, project_id=report.project_id)
