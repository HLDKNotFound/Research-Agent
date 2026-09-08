import uuid
import pytest
from app.core.exceptions import (
    AuthenticationError,
    EntityAlreadyExistsError,
    IdempotencyConflictError,
    InvalidStateTransitionError,
)
from app.schemas.file import FileChunkCreateDTO, FileCreateDTO
from app.schemas.project import ProjectCreateDTO, ProjectUpdateDTO
from app.schemas.run import RunCreateDTO, RunUpdateDTO
from app.schemas.user import UserCreateDTO, UserLoginDTO
from app.services.auth_service import AuthService
from app.services.file_service import FileService
from app.services.ingestion_service import IngestionService
from app.services.project_service import ProjectService
from app.services.run_service import RunService


@pytest.mark.asyncio
async def test_auth_service(db_session):
    auth_service = AuthService(db_session)

    # Register
    create_dto = UserCreateDTO(
        email="test_user@research.ai",
        password="securePassword123!",
        name="Alex",
    )
    reg_result = await auth_service.register(create_dto)
    assert reg_result.access_token is not None
    assert reg_result.user.email == "test_user@research.ai"

    # Duplicate registration should raise EntityAlreadyExistsError
    with pytest.raises(EntityAlreadyExistsError):
        await auth_service.register(create_dto)

    # Valid login
    login_result = await auth_service.login(
        UserLoginDTO(email="test_user@research.ai", password="securePassword123!")
    )
    assert login_result.access_token is not None

    # Invalid password login
    with pytest.raises(AuthenticationError):
        await auth_service.login(
            UserLoginDTO(email="test_user@research.ai", password="wrongPassword")
        )


@pytest.mark.asyncio
async def test_project_service_with_redis_cache(db_session, mock_cache_service):
    auth_service = AuthService(db_session)
    user = (
        await auth_service.register(
            UserCreateDTO(email="proj_owner@test.com", password="password123")
        )
    ).user

    project_service = ProjectService(db_session, cache=mock_cache_service)

    # Create project
    proj = await project_service.create_project(
        user_id=user.id,
        dto=ProjectCreateDTO(name="AI In Health", description="Healthcare AI in SEA"),
    )
    assert proj.name == "AI In Health"

    # First read (cache miss -> loads from DB and caches)
    cached_key = mock_cache_service.build_key("projects", "detail", str(proj.id))
    detail_1 = await project_service.get_project(user.id, proj.id)
    assert detail_1.id == proj.id

    # Verify item is now in Redis cache
    redis_val = await mock_cache_service.get(cached_key)
    assert redis_val is not None
    assert redis_val["id"] == str(proj.id)

    # Update project -> verifies cache is purged
    await project_service.update_project(
        user_id=user.id,
        project_id=proj.id,
        dto=ProjectUpdateDTO(name="AI In Health (Updated)"),
    )
    redis_val_after = await mock_cache_service.get(cached_key)
    assert redis_val_after is None  # Cache was invalidated!

    # Delete project
    await project_service.delete_project(user.id, proj.id)
    assert (await mock_cache_service.get(cached_key)) is None


@pytest.mark.asyncio
async def test_run_service_idempotency_and_state_machine(db_session, mock_cache_service):
    auth_service = AuthService(db_session)
    user = (
        await auth_service.register(
            UserCreateDTO(email="runner@test.com", password="password123")
        )
    ).user

    project_service = ProjectService(db_session, cache=mock_cache_service)
    proj = await project_service.create_project(
        user_id=user.id,
        dto=ProjectCreateDTO(name="Run Project"),
    )

    run_service = RunService(db_session, cache=mock_cache_service)

    # Create run with idempotency key
    run_dto = RunCreateDTO(
        project_id=proj.id,
        prompt="Analyze trends in semiconductors",
        idempotency_key="idemp_semiconductor_123",
    )
    run1 = await run_service.create_run(user.id, run_dto)
    assert run1.status == "queued"

    # Same idempotency key and same prompt returns the existing run
    run2 = await run_service.create_run(user.id, run_dto)
    assert run2.id == run1.id

    # Conflicting idempotency key with different prompt raises IdempotencyConflictError
    conflicting_dto = RunCreateDTO(
        project_id=proj.id,
        prompt="A completely different question",
        idempotency_key="idemp_semiconductor_123",
    )
    with pytest.raises(IdempotencyConflictError):
        await run_service.create_run(user.id, conflicting_dto)

    # State transition: queued -> planning (valid)
    updated = await run_service.update_status(run1.id, RunUpdateDTO(status="planning"))
    assert updated.status == "planning"

    # Invalid state transition: planning -> completed (must transition through writing/reviewing)
    with pytest.raises(InvalidStateTransitionError):
        await run_service.update_status(run1.id, RunUpdateDTO(status="completed"))


@pytest.mark.asyncio
async def test_file_and_ingestion_service_separation(db_session, mock_cache_service):
    auth_service = AuthService(db_session)
    user = (
        await auth_service.register(
            UserCreateDTO(email="uploader@test.com", password="password123")
        )
    ).user

    project_service = ProjectService(db_session, cache=mock_cache_service)
    proj = await project_service.create_project(
        user_id=user.id,
        dto=ProjectCreateDTO(name="Doc Project"),
    )

    file_service = FileService(db_session, cache=mock_cache_service)
    ingestion_service = IngestionService(db_session)

    # 1. File metadata lifecycle managed by FileService
    file_dto = FileCreateDTO(
        project_id=proj.id,
        filename="ai_paper.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
        storage_provider="local",
        storage_key="/tmp/ai_paper.pdf",
        idempotency_key="upload_paper_001",
    )
    registered_file = await file_service.register_file_upload(user.id, file_dto)
    assert registered_file.status == "uploaded"

    # 2. Ingestion pipeline (chunking & embeddings) managed by IngestionService
    chunks = [
        FileChunkCreateDTO(
            file_id=registered_file.id,
            chunk_index=0,
            content="Neural networks represent state of the art...",
            page_number=1,
            embedding=[0.1, 0.2, 0.3],
        ),
        FileChunkCreateDTO(
            file_id=registered_file.id,
            chunk_index=1,
            content="Transformer attention mechanisms allow parallelization...",
            page_number=2,
            embedding=[0.4, 0.5, 0.6],
        ),
    ]
    ingested_chunks = await ingestion_service.ingest_chunks(registered_file.id, chunks)
    assert len(ingested_chunks) == 2

    # Check file status transitioned to 'ready'
    ready_file = await file_service.get_file(user.id, registered_file.id)
    assert ready_file.status == "ready"
    assert ready_file.page_count == 2


@pytest.mark.asyncio
async def test_report_service_and_citations(db_session, mock_cache_service):
    from app.services.report_service import ReportService
    from app.repositories.evidence_repository import EvidenceRepository
    from app.models.evidence import Evidence
    from app.schemas.report import ReportCreateDTO, ReportSectionCreateDTO, CitationCreateDTO

    auth_service = AuthService(db_session)
    user = (
        await auth_service.register(
            UserCreateDTO(email="reporter@test.com", password="password123")
        )
    ).user

    project_service = ProjectService(db_session, cache=mock_cache_service)
    proj = await project_service.create_project(
        user_id=user.id,
        dto=ProjectCreateDTO(name="Report Project"),
    )

    run_service = RunService(db_session, cache=mock_cache_service)
    run = await run_service.create_run(
        user_id=user.id,
        dto=RunCreateDTO(project_id=proj.id, prompt="Generate Market Summary"),
    )

    # 1. Add Evidence
    evidence_repo = EvidenceRepository(db_session)
    evidence = Evidence(
        run_id=run.id,
        type="web",
        content="Market size projected to reach $5B by 2030.",
        source_url="https://market-insights.com/ai-2030",
        source_title="AI Market 2030",
        relevance_score=0.98,
    )
    await evidence_repo.create(evidence)

    # 2. Create Report
    report_service = ReportService(db_session, cache=mock_cache_service)
    report = await report_service.create_report(
        user_id=user.id,
        dto=ReportCreateDTO(
            run_id=run.id,
            project_id=proj.id,
            title="AI Market 2030 Projection",
            content="# Full Market Report...",
        ),
    )
    assert report.title == "AI Market 2030 Projection"

    # 3. Add Modular Section
    section = await report_service.add_section(
        user_id=user.id,
        dto=ReportSectionCreateDTO(
            report_id=report.id,
            section_key="market_projection",
            title="Market Projection",
            content="Rapid expansion is anticipated [1].",
            section_order=1,
        ),
    )
    assert section.section_key == "market_projection"

    # 4. Add Academic Citation
    citation = await report_service.add_citation(
        user_id=user.id,
        dto=CitationCreateDTO(
            report_section_id=section.id,
            evidence_id=evidence.id,
            citation_text="[1] Market Insights AI 2030",
            position=1,
        ),
    )
    assert citation.position == 1

    # 5. Fetch report with sections & citations (verified cached on second read)
    cached_key = mock_cache_service.build_key("reports", "detail", str(report.id))
    retrieved = await report_service.get_report(user.id, report.id)
    assert len(retrieved.sections) == 1
    assert len(retrieved.sections[0].citations) == 1

    cached_val = await mock_cache_service.get(cached_key)
    assert cached_val is not None
    assert cached_val["id"] == str(report.id)
