import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.cache import cache_service, CacheService
from app.core.exceptions import (
    EntityNotFoundError,
    IdempotencyConflictError,
    InvalidStateTransitionError,
    PermissionDeniedError,
)
from app.models.audit import AuditLog
from app.models.run import Run, RunStep
from app.models.run_event import RunEvent
from app.repositories.audit_repository import AuditRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.run_repository import RunRepository
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.run import (
    RunCreateDTO,
    RunEventCreateDTO,
    RunEventResponseDTO,
    RunResponseDTO,
    RunStepCreateDTO,
    RunStepResponseDTO,
    RunUpdateDTO,
)


class RunService:
    """Analysis Run orchestrator managing state transitions, idempotency, steps, and events."""

    VALID_TRANSITIONS = {
        "queued": {"planning", "cancelled", "failed"},
        "planning": {"researching", "analyzing", "cancelled", "failed"},
        "researching": {"analyzing", "writing", "cancelled", "failed"},
        "analyzing": {"writing", "cancelled", "failed"},
        "writing": {"reviewing", "completed", "cancelled", "failed"},
        "reviewing": {"writing", "completed", "cancelled", "failed"},
        "completed": set(),
        "failed": {"queued"},  # Allow retry
        "cancelled": set(),
    }

    def __init__(self, session: AsyncSession, cache: Optional[CacheService] = None):
        self.session = session
        self.repo = RunRepository(session)
        self.project_repo = ProjectRepository(session)
        self.audit_repo = AuditRepository(session)
        self.cache = cache or cache_service

    async def _check_access(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        membership = await self.project_repo.get_membership(project_id, user_id)
        if not membership:
            raise PermissionDeniedError("You do not have access to this project.")

    async def create_run(
        self,
        user_id: uuid.UUID,
        dto: RunCreateDTO,
    ) -> RunResponseDTO:
        await self._check_access(dto.project_id, user_id)

        # Enforce Idempotency
        if dto.idempotency_key:
            existing = await self.repo.get_by_idempotency(dto.project_id, dto.idempotency_key)
            if existing:
                # If existing prompt matches, return existing run idempotently
                if existing.prompt == dto.prompt:
                    return RunResponseDTO.model_validate(existing)
                raise IdempotencyConflictError(
                    dto.idempotency_key,
                    message="A run already exists with this idempotency_key but with different parameters.",
                )

        run = Run(
            project_id=dto.project_id,
            created_by_user_id=user_id,
            conversation_id=dto.conversation_id,
            prompt=dto.prompt,
            status="queued",
            idempotency_key=dto.idempotency_key,
            config=dto.options or {},
        )
        created = await self.repo.create(run)

        # Audit log
        await self.audit_repo.create(
            AuditLog(
                user_id=user_id,
                project_id=dto.project_id,
                action="run.create",
                resource_type="run",
                resource_id=str(created.id),
                payload={"prompt": dto.prompt[:100]},
            )
        )

        full_run = await self.repo.get_with_steps(created.id)
        return RunResponseDTO.model_validate(full_run)

    async def get_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> RunResponseDTO:
        cache_key = self.cache.build_key("runs", "detail", str(run_id))
        cached = await self.cache.get(cache_key)
        if cached:
            response = RunResponseDTO.model_validate(cached)
            await self._check_access(response.project_id, user_id)
            return response

        run = await self.repo.get_with_steps(run_id)
        if not run:
            raise EntityNotFoundError("Run", run_id)

        await self._check_access(run.project_id, user_id)

        response = RunResponseDTO.model_validate(run)
        # Cache run status briefly (15 seconds)
        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=15)
        return response

    async def list_runs(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        params: Optional[PaginationParams] = None,
        status: Optional[str] = None,
    ) -> PaginatedResponse[RunResponseDTO]:
        await self._check_access(project_id, user_id)
        pagination = params or PaginationParams()

        runs = await self.repo.list_by_project(project_id, pagination, status=status)
        total = await self.repo.count(project_id=project_id, status=status)

        items = [RunResponseDTO.model_validate(r) for r in runs]
        return PaginatedResponse.create(items, total, pagination)

    async def update_status(self, run_id: uuid.UUID, dto: RunUpdateDTO) -> RunResponseDTO:
        run = await self.repo.get_by_id(run_id)
        if not run:
            raise EntityNotFoundError("Run", run_id)

        if dto.status and dto.status != run.status:
            allowed = self.VALID_TRANSITIONS.get(run.status, set())
            if dto.status not in allowed:
                raise InvalidStateTransitionError("Run", run.status, dto.status)

        updated = await self.repo.update_status(
            run=run,
            status=dto.status or run.status,
            current_step=dto.current_step,
            progress_pct=dto.progress_pct,
            error_code=dto.error_code,
            error_message=dto.error_message,
            error_details=dto.error_details,
        )

        # Invalidate cache
        await self.cache.delete(f"{self.cache.version}:runs:detail:{run_id}")

        full_run = await self.repo.get_with_steps(updated.id)
        return RunResponseDTO.model_validate(full_run)

    async def record_step(self, dto: RunStepCreateDTO) -> RunStepResponseDTO:
        step = RunStep(
            run_id=dto.run_id,
            agent_name=dto.agent_name,
            step_name=dto.step_name,
            status=dto.status,
            input_data=dto.input_data,
            output_data=dto.output_data,
            duration_ms=dto.duration_ms,
            error=dto.error,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
        )
        created = await self.repo.add_step(step)
        await self.cache.delete(f"{self.cache.version}:runs:detail:{dto.run_id}")
        return RunStepResponseDTO.model_validate(created)

    async def record_event(self, dto: RunEventCreateDTO) -> RunEventResponseDTO:
        event = RunEvent(
            run_id=dto.run_id,
            event_type=dto.event_type,
            agent_name=dto.agent_name,
            step_number=dto.step_number,
            payload=dto.payload or {},
        )
        created = await self.repo.add_event(event)
        return RunEventResponseDTO.model_validate(created)

    async def get_events(self, user_id: uuid.UUID, run_id: uuid.UUID) -> List[RunEventResponseDTO]:
        run = await self.repo.get_by_id(run_id)
        if not run:
            raise EntityNotFoundError("Run", run_id)
        await self._check_access(run.project_id, user_id)

        events = await self.repo.get_events(run_id)
        return [RunEventResponseDTO.model_validate(e) for e in events]

    async def cancel_run(self, user_id: uuid.UUID, run_id: uuid.UUID) -> RunResponseDTO:
        run = await self.repo.get_by_id(run_id)
        if not run:
            raise EntityNotFoundError("Run", run_id)
        await self._check_access(run.project_id, user_id)

        if run.status in ("completed", "failed", "cancelled"):
            return RunResponseDTO.model_validate(run)

        return await self.update_status(
            run_id,
            RunUpdateDTO(status="cancelled", current_step="cancelled"),
        )

    async def execute_run_pipeline(self, user_id: uuid.UUID, run_id: uuid.UUID) -> RunResponseDTO:
        """
        Executes the LangGraph Multi-Agent workflow, records steps and events,
        and automatically synthesizes Report, Sections, and Citations.
        """
        from app.agents.graph import execute_research_workflow
        from app.schemas.report import CitationCreateDTO, ReportCreateDTO, ReportSectionCreateDTO
        from app.services.report_service import ReportService

        run = await self.repo.get_by_id(run_id)
        if not run:
            raise EntityNotFoundError("Run", run_id)
        await self._check_access(run.project_id, user_id)

        # 1. Transition to planning
        await self.update_status(run_id, RunUpdateDTO(status="planning", current_step="Planning", progress_pct=15))

        # 2. Execute LangGraph workflow
        await self.update_status(run_id, RunUpdateDTO(status="researching", current_step="Multi-Agent Execution", progress_pct=45))
        final_state = await execute_research_workflow(
            project_id=str(run.project_id),
            run_id=str(run.id),
            user_id=str(user_id),
            prompt=run.prompt,
            thread_id=f"thread-{run.id}",
        )

        # 3. Transition to writing report
        await self.update_status(run_id, RunUpdateDTO(status="writing", current_step="Synthesizing Report", progress_pct=85))

        # 3. Record steps and events
        for step_idx, step_info in enumerate(final_state.get("steps_log", []), 1):
            await self.record_step(
                RunStepCreateDTO(
                    run_id=run.id,
                    agent_name=step_info.get("agent", "Agent"),
                    step_name=step_info.get("step", "Execution"),
                    status=step_info.get("status", "completed"),
                    output_data={
                        "message": step_info.get("message"),
                        "details": step_info.get("details"),
                        "progress_pct": step_info.get("progress_pct"),
                    },
                ),
            )
            await self.record_event(
                RunEventCreateDTO(
                    run_id=run.id,
                    event_type="agent_progress",
                    agent_name=step_info.get("agent"),
                    step_number=step_idx,
                    payload=step_info,
                )
            )

        # 4. Create Synthesized Report & Sections
        report_service = ReportService(self.session, cache=self.cache)
        report_dto = await report_service.create_report(
            user_id,
            ReportCreateDTO(
                project_id=run.project_id,
                run_id=run.id,
                title=final_state.get("report_title", f"Autonomous Report: {run.prompt}"),
                content=f"Report generated from multi-agent analysis of: {run.prompt}",
                format="markdown",
                status="completed",
            ),
        )

        created_sections = []
        for s in final_state.get("report_sections", []):
            sec = await report_service.add_section(
                user_id,
                ReportSectionCreateDTO(
                    report_id=report_dto.id,
                    section_key=s["section_key"],
                    title=s["title"],
                    content=s["content"],
                    section_order=s["section_order"],
                ),
            )
            created_sections.append(sec)

        from app.models.evidence import Evidence
        from app.repositories.evidence_repository import EvidenceRepository
        evidence_repo = EvidenceRepository(self.session)

        for cit_idx, cit in enumerate(final_state.get("citations", []), 1):
            evidence = Evidence(
                run_id=run.id,
                type="web" if cit.get("url") else "generated",
                content=cit.get("snippet", cit.get("title", "Evidence content")),
                source_title=cit.get("title"),
                source_url=cit.get("url"),
                relevance_score=cit.get("relevance_score", 0.95),
            )
            created_evidence = await evidence_repo.create(evidence)
            if created_sections:
                await report_service.add_citation(
                    user_id,
                    CitationCreateDTO(
                        report_section_id=created_sections[0].id,
                        evidence_id=created_evidence.id,
                        citation_text=cit.get("snippet", cit.get("title", "Citation")),
                        position=cit_idx,
                    ),
                )

        # 5. Mark Run completed
        return await self.update_status(
            run_id,
            RunUpdateDTO(status="completed", current_step="Completed", progress_pct=100),
        )
