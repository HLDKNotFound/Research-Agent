import uuid
from typing import Optional, Sequence
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.project import Project, ProjectMember
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession):
        super().__init__(Project, session)

    async def get_with_members(self, project_id: uuid.UUID) -> Optional[Project]:
        """Fetch project by ID with members preloaded."""
        query = (
            select(Project)
            .options(selectinload(Project.members))
            .where(Project.id == project_id, Project.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
        search: Optional[str] = None,
    ) -> Sequence[Project]:
        """List all projects where user is a registered member (owner/admin/member/viewer)."""
        query = (
            select(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(
                ProjectMember.user_id == user_id,
                Project.deleted_at.is_(None),
            )
            .order_by(Project.created_at.desc())
        )

        if search:
            query = query.where(Project.name.ilike(f"%{search}%"))

        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: uuid.UUID, search: Optional[str] = None) -> int:
        query = (
            select(func.count(Project.id))
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .where(
                ProjectMember.user_id == user_id,
                Project.deleted_at.is_(None),
            )
        )
        if search:
            query = query.where(Project.name.ilike(f"%{search}%"))

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def get_membership(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ProjectMember]:
        query = select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def add_member(self, project_id: uuid.UUID, user_id: uuid.UUID, role: str = "member") -> ProjectMember:
        member = ProjectMember(project_id=project_id, user_id=user_id, role=role)
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(self, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        member = await self.get_membership(project_id, user_id)
        if member:
            await self.session.delete(member)
            await self.session.flush()
            return True
        return False
