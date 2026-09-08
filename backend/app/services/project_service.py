import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import cache_service, CacheService
from app.core.exceptions import EntityNotFoundError, PermissionDeniedError
from app.models.audit import AuditLog
from app.models.project import Project, ProjectMember
from app.repositories.audit_repository import AuditRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.project import (
    AddMemberDTO,
    ProjectCreateDTO,
    ProjectMemberDTO,
    ProjectResponseDTO,
    ProjectUpdateDTO,
)


class ProjectService:
    """Project / Workspace business logic with Redis caching and multi-tenant authorization."""

    def __init__(self, session: AsyncSession, cache: Optional[CacheService] = None):
        self.session = session
        self.repo = ProjectRepository(session)
        self.audit_repo = AuditRepository(session)
        self.cache = cache or cache_service

    async def create_project(self, user_id: uuid.UUID, dto: ProjectCreateDTO) -> ProjectResponseDTO:
        project = Project(
            name=dto.name,
            description=dto.description,
        )
        created = await self.repo.create(project)

        # Initial creator is the workspace 'owner'
        await self.repo.add_member(created.id, user_id, role="owner")

        # Audit log
        await self.audit_repo.create(
            AuditLog(
                user_id=user_id,
                project_id=created.id,
                action="project.create",
                resource_type="project",
                resource_id=str(created.id),
                payload={"name": dto.name},
            )
        )

        # Invalidate cached list for this user
        await self.cache.invalidate_project(created.id, user_id=user_id)

        # Re-fetch with members
        full_project = await self.repo.get_with_members(created.id)
        return ProjectResponseDTO.model_validate(full_project)

    async def get_project(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        is_superuser: bool = False,
    ) -> ProjectResponseDTO:
        # Check authorization (bypass for platform superusers)
        if not is_superuser:
            membership = await self.repo.get_membership(project_id, user_id)
            if not membership:
                raise PermissionDeniedError("You do not have access to this project.")

        # Check cache
        cache_key = self.cache.build_key("projects", "detail", str(project_id))
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return ProjectResponseDTO.model_validate(cached_data)

        project = await self.repo.get_with_members(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        response = ProjectResponseDTO.model_validate(project)
        await self.cache.set(cache_key, response.model_dump(mode="json"))
        return response

    async def list_user_projects(
        self,
        user_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[ProjectResponseDTO]:
        pagination = params or PaginationParams()

        # Build namespaced cache key: v1:projects:list:{user_id}:{page}:{limit}:{filters_hash}
        cache_key = self.cache.build_key(
            "projects",
            "list",
            str(user_id),
            pagination.page,
            pagination.limit,
            search=search,
        )
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return PaginatedResponse[ProjectResponseDTO].model_validate(cached_data)

        projects = await self.repo.list_by_user(user_id, pagination, search=search)
        total = await self.repo.count_by_user(user_id, search=search)

        dtos = [ProjectResponseDTO.model_validate(p) for p in projects]
        response = PaginatedResponse.create(dtos, total, pagination)

        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=120)
        return response

    async def update_project(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        dto: ProjectUpdateDTO,
    ) -> ProjectResponseDTO:
        membership = await self.repo.get_membership(project_id, user_id)
        if not membership or membership.role not in ("owner", "admin"):
            raise PermissionDeniedError("Only project owners and admins can update project settings.")

        project = await self.repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        if dto.name is not None:
            project.name = dto.name
        if dto.description is not None:
            project.description = dto.description

        await self.repo.update(project)

        # Invalidate caches
        await self.cache.invalidate_project(project_id, user_id=user_id)

        # Audit log
        await self.audit_repo.create(
            AuditLog(
                user_id=user_id,
                project_id=project_id,
                action="project.update",
                resource_type="project",
                resource_id=str(project_id),
                payload=dto.model_dump(exclude_none=True),
            )
        )

        full = await self.repo.get_with_members(project_id)
        return ProjectResponseDTO.model_validate(full)

    async def delete_project(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Soft deletes the project and invalidates all related caches."""
        membership = await self.repo.get_membership(project_id, user_id)
        if not membership or membership.role != "owner":
            raise PermissionDeniedError("Only project owners can delete a project.")

        project = await self.repo.get_by_id(project_id)
        if not project:
            raise EntityNotFoundError("Project", project_id)

        await self.repo.soft_delete(project)

        # Invalidate caches
        await self.cache.invalidate_project(project_id, user_id=user_id)

        # Audit log
        await self.audit_repo.create(
            AuditLog(
                user_id=user_id,
                project_id=project_id,
                action="project.delete",
                resource_type="project",
                resource_id=str(project_id),
            )
        )

    async def add_member(self, acting_user_id: uuid.UUID, project_id: uuid.UUID, dto: AddMemberDTO) -> ProjectMemberDTO:
        actor_perm = await self.repo.get_membership(project_id, acting_user_id)
        if not actor_perm or actor_perm.role not in ("owner", "admin"):
            raise PermissionDeniedError("Only owners and admins can invite members.")

        # Admin-on-Admin Privilege Escalation Guard:
        # Admins can ONLY invite/modify users with strictly lower roles ('member', 'viewer')
        if actor_perm.role == "admin" and dto.role in ("owner", "admin"):
            raise PermissionDeniedError(
                "Admins can only assign 'member' or 'viewer' roles. Only owners can assign 'admin' or 'owner'."
            )

        member = await self.repo.add_member(project_id, dto.user_id, dto.role)
        await self.cache.invalidate_project(project_id, user_id=dto.user_id)

        return ProjectMemberDTO.model_validate(member)

    async def remove_member(self, acting_user_id: uuid.UUID, project_id: uuid.UUID, target_user_id: uuid.UUID) -> None:
        actor_perm = await self.repo.get_membership(project_id, acting_user_id)
        if not actor_perm:
            raise PermissionDeniedError("You do not have access to this project.")

        target_member = await self.repo.get_membership(project_id, target_user_id)
        if not target_member:
            raise EntityNotFoundError("ProjectMember", target_user_id)

        # The Last Owner Problem:
        # An owner cannot remove themselves or leave without transferring ownership or deleting the project.
        if target_member.role == "owner":
            raise PermissionDeniedError(
                "The project owner cannot be removed or leave the project. Please transfer ownership first or delete the project."
            )

        # Admin privilege check:
        # Admins can only remove users with strictly lower roles (member, viewer), never another admin or owner.
        if actor_perm.role == "admin":
            if target_member.role in ("owner", "admin"):
                raise PermissionDeniedError("Admins cannot remove other admins or the project owner.")
        elif actor_perm.role != "owner":
            # Member/viewer can only remove themselves (leave project)
            if acting_user_id != target_user_id:
                raise PermissionDeniedError("You can only remove yourself from the project.")

        await self.repo.remove_member(project_id, target_user_id)
        await self.cache.invalidate_project(project_id, user_id=target_user_id)

    async def transfer_ownership(
        self,
        acting_user_id: uuid.UUID,
        project_id: uuid.UUID,
        new_owner_user_id: uuid.UUID,
    ) -> None:
        """Transfers project ownership from current owner to an existing member."""
        actor_perm = await self.repo.get_membership(project_id, acting_user_id)
        if not actor_perm or actor_perm.role != "owner":
            raise PermissionDeniedError("Only the current project owner can transfer ownership.")

        if acting_user_id == new_owner_user_id:
            return  # Already owner

        target_member = await self.repo.get_membership(project_id, new_owner_user_id)
        if not target_member:
            raise EntityNotFoundError("ProjectMember", new_owner_user_id)

        # Demote current owner to admin
        actor_perm.role = "admin"
        # Promote target to owner
        target_member.role = "owner"

        await self.session.flush()

        # Invalidate caches
        await self.cache.invalidate_project(project_id, user_id=acting_user_id)
        await self.cache.invalidate_project(project_id, user_id=new_owner_user_id)

        # Audit log
        await self.audit_repo.create(
            AuditLog(
                user_id=acting_user_id,
                project_id=project_id,
                action="project.transfer_ownership",
                resource_type="project",
                resource_id=str(project_id),
                payload={"new_owner": str(new_owner_user_id)},
            )
        )
