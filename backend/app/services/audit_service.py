import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogCreateDTO, AuditLogResponseDTO
from app.schemas.common import PaginatedResponse, PaginationParams


class AuditService:
    """Service providing query and recording capabilities for system audit logs."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditRepository(session)

    async def log_action(self, dto: AuditLogCreateDTO) -> AuditLogResponseDTO:
        log = AuditLog(
            user_id=dto.user_id,
            project_id=dto.project_id,
            action=dto.action,
            resource_type=dto.resource_type,
            resource_id=dto.resource_id,
            payload=dto.payload or {},
            ip_address=dto.ip_address,
        )
        created = await self.repo.create(log)
        return AuditLogResponseDTO.model_validate(created)

    async def list_project_logs(
        self,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
    ) -> PaginatedResponse[AuditLogResponseDTO]:
        pagination = params or PaginationParams()
        logs = await self.repo.list_by_project(project_id, pagination)
        total = await self.repo.count(project_id=project_id)

        items = [AuditLogResponseDTO.model_validate(log) for log in logs]
        return PaginatedResponse.create(items, total, pagination)
