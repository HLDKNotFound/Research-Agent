import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db, require_project_role
from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.core.sanitizer import sanitize_metadata_text
from app.models.project import ProjectMember
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.project import (
    AddMemberDTO,
    ProjectCreateDTO,
    ProjectMemberDTO,
    ProjectResponseDTO,
    ProjectUpdateDTO,
    TransferOwnershipDTO,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/api/v1/projects", tags=["Projects & RBAC"])


@router.post("", response_model=ProjectResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_project(
    dto: ProjectCreateDTO,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectResponseDTO:
    """Create a new project workspace. Creator automatically becomes 'owner'."""
    # Sanitize metadata title
    dto.name = sanitize_metadata_text(dto.name, max_length=255)
    service = ProjectService(session)
    return await service.create_project(current_user.id, dto)


@router.get("", response_model=PaginatedResponse[ProjectResponseDTO])
async def list_projects(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedResponse[ProjectResponseDTO]:
    """List all projects where current user has a membership."""
    service = ProjectService(session)
    params = PaginationParams(page=page, limit=limit)
    return await service.list_user_projects(current_user.id, params=params, search=search)


@router.get(
    "/{project_id}",
    response_model=ProjectResponseDTO,
    dependencies=[Depends(require_project_role("viewer"))],
)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectResponseDTO:
    """Get project details. Requires at least 'viewer' role."""
    service = ProjectService(session)
    try:
        return await service.get_project(
            current_user.id,
            project_id,
            is_superuser=current_user.is_superuser,
        )
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponseDTO,
    dependencies=[Depends(require_project_role("admin"))],
)
async def update_project(
    project_id: uuid.UUID,
    dto: ProjectUpdateDTO,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectResponseDTO:
    """Update project settings. Requires 'admin' or 'owner' role."""
    if dto.name:
        dto.name = sanitize_metadata_text(dto.name, max_length=255)

    service = ProjectService(session)
    try:
        return await service.update_project(current_user.id, project_id, dto)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_project_role("owner"))],
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete project. Strictly requires 'owner' role."""
    service = ProjectService(session)
    try:
        await service.delete_project(current_user.id, project_id)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_project_role("admin"))],
)
async def add_member(
    project_id: uuid.UUID,
    dto: AddMemberDTO,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectMemberDTO:
    """
    Add a new member to the project.
    Requires 'admin' or 'owner'. Admins can only assign 'member' or 'viewer' roles.
    """
    service = ProjectService(session)
    try:
        return await service.add_member(current_user.id, project_id, dto)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete(
    "/{project_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_project_role("member"))],
)
async def remove_member(
    project_id: uuid.UUID,
    target_user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Remove a member from the project.
    - Owners can remove anyone except leaving as last owner without transferring ownership.
    - Admins can only remove lower roles (member, viewer), never another admin or owner.
    - Members can only remove themselves (leave project).
    """
    service = ProjectService(session)
    try:
        await service.remove_member(current_user.id, project_id, target_user_id)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post(
    "/{project_id}/transfer-ownership",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_project_role("owner"))],
)
async def transfer_ownership(
    project_id: uuid.UUID,
    dto: TransferOwnershipDTO,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """
    Transfers project ownership to an existing project member.
    Strictly requires current 'owner'. Current owner is demoted to 'admin'.
    """
    service = ProjectService(session)
    try:
        await service.transfer_ownership(current_user.id, project_id, dto.new_owner_user_id)
    except PermissionDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except EntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
