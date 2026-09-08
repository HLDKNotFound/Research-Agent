import hashlib
import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File as FastAPIFile, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.file import FileCreateDTO, FileResponseDTO
from app.services.file_service import FileService
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["Files & Documents"])


@router.get(
    "/api/v1/projects/{project_id}/files",
    response_model=PaginatedResponse[FileResponseDTO],
    summary="List files in a project",
)
async def list_files(
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FileService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.list_files(current_user.id, project_id, pagination)


@router.post(
    "/api/v1/projects/{project_id}/files",
    response_model=FileResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Register file upload metadata in a project",
)
async def register_file(
    project_id: uuid.UUID,
    dto: FileCreateDTO,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FileService(db)
    dto.project_id = project_id
    return await service.register_file_upload(current_user.id, dto)


@router.post(
    "/api/v1/projects/{project_id}/files/upload",
    response_model=FileResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a document file (PDF, Word, Excel, CSV, TXT)",
)
async def upload_and_ingest_file(
    project_id: uuid.UUID,
    file: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    size_bytes = len(content)
    checksum = hashlib.sha256(content).hexdigest()

    # Ensure storage folder exists
    os.makedirs(settings.STORAGE_LOCAL_PATH, exist_ok=True)
    storage_key = f"{project_id}/{checksum}_{file.filename}"
    file_path = os.path.join(settings.STORAGE_LOCAL_PATH, f"{checksum}_{file.filename}")

    with open(file_path, "wb") as fp:
        fp.write(content)

    file_service = FileService(db)
    ingestion_service = IngestionService(db)

    create_dto = FileCreateDTO(
        project_id=project_id,
        filename=file.filename or "uploaded_document",
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        storage_provider="local",
        storage_key=storage_key,
        checksum=checksum,
    )

    file_record = await file_service.register_file_upload(current_user.id, create_dto)

    # Ingest document chunks & embeddings asynchronously
    await ingestion_service.ingest_document(
        file_id=file_record.id,
        content=content,
        filename=file.filename or "uploaded_document",
        mime_type=file.content_type,
    )

    return await file_service.get_file(current_user.id, file_record.id)


@router.delete(
    "/api/v1/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a file",
)
async def delete_file(
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = FileService(db)
    await service.delete_file(current_user.id, file_id)
    return None
