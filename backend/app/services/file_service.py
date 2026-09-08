import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import cache_service, CacheService
from app.core.exceptions import EntityNotFoundError, IdempotencyConflictError, PermissionDeniedError
from app.models.audit import AuditLog
from app.models.file import File
from app.repositories.audit_repository import AuditRepository
from app.repositories.file_repository import FileRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.file import FileCreateDTO, FileResponseDTO, FileUpdateDTO


class FileService:
    """File metadata and lifecycle business service (decoupled from document ingestion)."""

    def __init__(self, session: AsyncSession, cache: Optional[CacheService] = None):
        self.session = session
        self.repo = FileRepository(session)
        self.project_repo = ProjectRepository(session)
        self.audit_repo = AuditRepository(session)
        self.cache = cache or cache_service

    async def _check_access(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.project_repo.get_membership(project_id, user_id)
        if not membership:
            raise PermissionDeniedError("You do not have access to this project.")

    async def register_file_upload(
        self,
        user_id: uuid.UUID,
        dto: FileCreateDTO,
    ) -> FileResponseDTO:
        await self._check_access(dto.project_id, user_id)

        # Check idempotency
        if dto.idempotency_key:
            existing = await self.repo.get_by_idempotency_key(dto.project_id, dto.idempotency_key)
            if existing:
                # If checksum or filename matches, return existing record idempotently
                if existing.filename == dto.filename and (not dto.checksum or existing.checksum == dto.checksum):
                    return FileResponseDTO.model_validate(existing)
                raise IdempotencyConflictError(
                    dto.idempotency_key,
                    message="Conflicting file upload with identical idempotency_key but different payload",
                )

        # Check duplicate by checksum within project
        if dto.checksum:
            existing_checksum = await self.repo.get_by_checksum(dto.project_id, dto.checksum)
            if existing_checksum:
                return FileResponseDTO.model_validate(existing_checksum)

        file_obj = File(
            project_id=dto.project_id,
            created_by_user_id=user_id,
            filename=dto.filename,
            mime_type=dto.mime_type,
            size_bytes=dto.size_bytes,
            storage_provider=dto.storage_provider,
            storage_key=dto.storage_key,
            status="uploaded",
            checksum=dto.checksum,
            idempotency_key=dto.idempotency_key,
            metadata_=dto.metadata or {},
        )
        created = await self.repo.create(file_obj)

        # Audit log
        await self.audit_repo.create(
            AuditLog(
                user_id=user_id,
                project_id=dto.project_id,
                action="file.upload",
                resource_type="file",
                resource_id=str(created.id),
                payload={"filename": dto.filename, "size_bytes": dto.size_bytes},
            )
        )

        # Invalidate project file list cache
        await self.cache.delete_pattern(f"{self.cache.version}:files:list:{dto.project_id}:*")

        return FileResponseDTO.model_validate(created)

    async def get_file(self, user_id: uuid.UUID, file_id: uuid.UUID) -> FileResponseDTO:
        cache_key = self.cache.build_key("files", "detail", str(file_id))
        cached = await self.cache.get(cache_key)
        if cached:
            return FileResponseDTO.model_validate(cached)

        file_obj = await self.repo.get_by_id(file_id)
        if not file_obj:
            raise EntityNotFoundError("File", file_id)

        await self._check_access(file_obj.project_id, user_id)

        response = FileResponseDTO.model_validate(file_obj)
        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=60)
        return response

    async def list_files(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
        status: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> PaginatedResponse[FileResponseDTO]:
        await self._check_access(project_id, user_id)
        pagination = params or PaginationParams()

        cache_key = self.cache.build_key(
            "files",
            "list",
            str(project_id),
            pagination.page,
            pagination.limit,
            status=status,
            mime_type=mime_type,
        )
        cached = await self.cache.get(cache_key)
        if cached:
            return PaginatedResponse[FileResponseDTO].model_validate(cached)

        files = await self.repo.list_by_project(project_id, pagination, status=status, mime_type=mime_type)
        total = await self.repo.count(project_id=project_id, status=status, mime_type=mime_type)

        items = [FileResponseDTO.model_validate(f) for f in files]
        response = PaginatedResponse.create(items, total, pagination)

        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=60)
        return response

    async def update_status(self, file_id: uuid.UUID, dto: FileUpdateDTO) -> FileResponseDTO:
        file_obj = await self.repo.get_by_id(file_id)
        if not file_obj:
            raise EntityNotFoundError("File", file_id)

        if dto.status:
            file_obj.status = dto.status
        if dto.page_count is not None:
            file_obj.page_count = dto.page_count
        if dto.metadata:
            meta = file_obj.metadata_ or {}
            meta.update(dto.metadata)
            file_obj.metadata_ = meta

        await self.repo.update(file_obj)

        # Invalidate cache
        await self.cache.delete(f"{self.cache.version}:files:detail:{file_id}")
        await self.cache.delete_pattern(f"{self.cache.version}:files:list:{file_obj.project_id}:*")

        return FileResponseDTO.model_validate(file_obj)

    async def delete_file(self, user_id: uuid.UUID, file_id: uuid.UUID) -> None:
        file_obj = await self.repo.get_by_id(file_id)
        if not file_obj:
            raise EntityNotFoundError("File", file_id)

        await self._check_access(file_obj.project_id, user_id)
        await self.repo.soft_delete(file_obj)

        # Invalidate cache
        await self.cache.delete(f"{self.cache.version}:files:detail:{file_id}")
        await self.cache.delete_pattern(f"{self.cache.version}:files:list:{file_obj.project_id}:*")
