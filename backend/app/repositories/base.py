import uuid
from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, Sequence, Type, TypeVar
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base
from app.schemas.common import PaginationParams

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic asynchronous repository with built-in soft-delete handling,
    pagination, and CRUD utilities.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(
        self,
        entity_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        """Fetch a single entity by primary key, filtering out soft-deleted records by default."""
        query = select(self.model).where(self.model.id == entity_id)

        if hasattr(self.model, "deleted_at") and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.session.execute(query)
        return result.scalars().first()

    async def list(
        self,
        params: Optional[PaginationParams] = None,
        include_deleted: bool = False,
        **filters: Any,
    ) -> Sequence[ModelType]:
        """List entities matching criteria with pagination support."""
        query = select(self.model)

        if hasattr(self.model, "deleted_at") and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)

        if hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())

        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, include_deleted: bool = False, **filters: Any) -> int:
        """Count entities matching criteria."""
        query = select(func.count(self.model.id))

        if hasattr(self.model, "deleted_at") and not include_deleted:
            query = query.where(self.model.deleted_at.is_(None))

        for field, value in filters.items():
            if value is not None and hasattr(self.model, field):
                query = query.where(getattr(self.model, field) == value)

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def create(self, entity: ModelType) -> ModelType:
        """Add and flush an entity."""
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: ModelType) -> ModelType:
        """Flush changes on an entity."""
        await self.session.flush()
        return entity

    async def soft_delete(self, entity: ModelType) -> ModelType:
        """Perform a soft-delete by setting deleted_at to UTC now."""
        if hasattr(entity, "deleted_at"):
            setattr(entity, "deleted_at", datetime.now(timezone.utc))
            await self.session.flush()
        else:
            await self.delete(entity)
        return entity

    async def delete(self, entity: ModelType) -> None:
        """Hard delete an entity from the database."""
        await self.session.delete(entity)
        await self.session.flush()
