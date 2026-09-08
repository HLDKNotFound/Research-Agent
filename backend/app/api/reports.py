import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
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
from app.services.report_service import ReportService

router = APIRouter(tags=["Reports & Citations"])


@router.get(
    "/api/v1/projects/{project_id}/reports",
    response_model=PaginatedResponse[ReportResponseDTO],
    summary="List research reports in a project",
)
async def list_reports(
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.list_reports(current_user.id, project_id, pagination)


@router.get(
    "/api/v1/reports/{report_id}",
    response_model=ReportResponseDTO,
    summary="Get report details with sections and citations",
)
async def get_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.get_report(current_user.id, report_id)


@router.patch(
    "/api/v1/reports/{report_id}",
    response_model=ReportResponseDTO,
    summary="Update report metadata",
)
async def update_report(
    report_id: uuid.UUID,
    dto: ReportUpdateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.update_report(current_user.id, report_id, dto)


@router.post(
    "/api/v1/reports/{report_id}/sections",
    response_model=ReportSectionResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add a modular section to a report",
)
async def add_section(
    report_id: uuid.UUID,
    dto: ReportSectionCreateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    dto.report_id = report_id
    return await service.add_section(current_user.id, dto)


@router.patch(
    "/api/v1/reports/{report_id}/sections/{section_id}",
    response_model=ReportSectionResponseDTO,
    summary="Update a report section",
)
async def update_section(
    report_id: uuid.UUID,
    section_id: uuid.UUID,
    dto: ReportSectionUpdateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.update_section(current_user.id, section_id, dto)


@router.post(
    "/api/v1/reports/{report_id}/citations",
    response_model=CitationResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Add a verified citation to a report",
)
async def add_citation(
    report_id: uuid.UUID,
    dto: CitationCreateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.add_citation(current_user.id, dto)


@router.delete(
    "/api/v1/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a report",
)
async def delete_report(
    report_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    await service.delete_report(current_user.id, report_id)
    return None
