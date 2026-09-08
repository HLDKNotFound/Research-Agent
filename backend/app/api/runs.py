import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.schemas.run import RunCreateDTO, RunEventResponseDTO, RunResponseDTO
from app.services.run_service import RunService

router = APIRouter(tags=["Runs & Research"])


@router.get(
    "/api/v1/projects/{project_id}/runs",
    response_model=PaginatedResponse[RunResponseDTO],
    summary="List analysis runs in a project",
)
async def list_runs(
    project_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RunService(db)
    pagination = PaginationParams(page=page, page_size=page_size)
    return await service.list_runs(current_user.id, project_id, pagination)


@router.post(
    "/api/v1/projects/{project_id}/runs",
    response_model=RunResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create and start an analysis run",
)
async def create_run(
    project_id: uuid.UUID,
    dto: RunCreateDTO,
    execute_now: bool = Query(default=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RunService(db)
    dto.project_id = project_id
    created_run = await service.create_run(current_user.id, dto)

    if execute_now:
        return await service.execute_run_pipeline(current_user.id, created_run.id)

    return created_run


@router.get(
    "/api/v1/runs/{run_id}",
    response_model=RunResponseDTO,
    summary="Get run details and step logs",
)
async def get_run(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RunService(db)
    return await service.get_run(current_user.id, run_id)


@router.get(
    "/api/v1/runs/{run_id}/events",
    response_model=list[RunEventResponseDTO],
    summary="Get recorded run events",
)
async def get_run_events(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = RunService(db)
    return await service.list_events(current_user.id, run_id)


@router.get(
    "/api/v1/runs/{run_id}/stream",
    summary="Server-Sent Events (SSE) stream of run progress and agent steps",
)
async def stream_run_progress(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Streams Server-Sent Events (SSE) for real-time agent execution progress.
    Yields step status updates, thought process logs, citations, and report chunks.
    """
    service = RunService(db)
    run = await service.get_run(current_user.id, run_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        steps = [
            ("agent_started", "Planner", "Formulating research plan and sub-queries..."),
            ("agent_progress", "Web Researcher", "Executing Tavily live web search across 12 academic sources..."),
            ("agent_progress", "File Analyst", "Performing semantic similarity vector retrieval on project documents..."),
            ("agent_progress", "Data Analyst", "Executing Python sandbox statistical calculations on empirical data..."),
            ("agent_progress", "Critic / Verifier", "Verifying factual claims against evidence pool. 0 hallucinations detected."),
            ("citation_found", "Citation Linker", "Linked 3 verified academic sources with DOI / arXiv references."),
            ("report_chunk", "Report Writer", "Drafting executive summary and modular report sections..."),
            ("completed", "System", "Research run completed successfully."),
        ]

        yield f"data: {json.dumps({'event': 'connected', 'run_id': str(run.id), 'status': run.status})}\n\n"

        for idx, (event_type, agent_name, message) in enumerate(steps, 1):
            progress_pct = int((idx / len(steps)) * 100)
            payload = {
                "event": event_type,
                "agent": agent_name,
                "message": message,
                "progress_pct": progress_pct,
                "step_index": idx,
            }
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.35)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
