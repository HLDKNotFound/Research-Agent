import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.run import Run, RunStep
from app.models.run_event import RunEvent
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class RunRepository(BaseRepository[Run]):
    def __init__(self, session: AsyncSession):
        super().__init__(Run, session)

    async def get_by_idempotency(
        self,
        project_id: uuid.UUID,
        idempotency_key: str,
    ) -> Optional[Run]:
        query = select(Run).where(
            Run.project_id == project_id,
            Run.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_with_steps(self, run_id: uuid.UUID) -> Optional[Run]:
        query = (
            select(Run)
            .options(selectinload(Run.steps))
            .where(Run.id == run_id)
        )
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
        status: Optional[str] = None,
    ) -> Sequence[Run]:
        query = (
            select(Run)
            .where(Run.project_id == project_id)
            .order_by(Run.created_at.desc())
        )
        if status:
            query = query.where(Run.status == status)

        if params:
            query = query.offset(params.offset).limit(params.limit)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_status(
        self,
        run: Run,
        status: str,
        current_step: Optional[str] = None,
        progress_pct: Optional[int] = None,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> Run:
        run.status = status
        if current_step is not None:
            run.current_step = current_step
        if progress_pct is not None:
            run.progress_pct = progress_pct
        if error_code is not None:
            run.error_code = error_code
        if error_message is not None:
            run.error_message = error_message
        if error_details is not None:
            run.error_details = error_details

        now = datetime.now(timezone.utc)
        if status == "running" and not run.started_at:
            run.started_at = now
        elif status in ("completed", "failed", "cancelled"):
            run.completed_at = now
            if run.started_at:
                run.duration_ms = int((now - run.started_at).total_seconds() * 1000)

        await self.session.flush()
        return run

    async def add_step(self, step: RunStep) -> RunStep:
        self.session.add(step)
        await self.session.flush()
        return step

    async def add_event(self, event: RunEvent) -> RunEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def get_events(self, run_id: uuid.UUID, limit: int = 100) -> Sequence[RunEvent]:
        query = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
