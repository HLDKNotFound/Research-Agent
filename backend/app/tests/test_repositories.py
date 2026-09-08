import uuid
import pytest
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.file import File, FileChunk
from app.models.run import Run
from app.models.report import Report, ReportSection, Citation
from app.models.evidence import Evidence
from app.repositories.project_repository import ProjectRepository
from app.repositories.file_repository import FileRepository
from app.repositories.run_repository import RunRepository
from app.repositories.report_repository import ReportRepository
from app.schemas.file import VectorFilterDTO


@pytest.mark.asyncio
async def test_soft_delete_behavior(db_session):
    repo = ProjectRepository(db_session)
    project = Project(name="Temporary Project")
    await repo.create(project)

    # Active lookup
    found = await repo.get_by_id(project.id)
    assert found is not None
    assert found.deleted_at is None

    # Soft delete
    await repo.soft_delete(project)
    assert project.deleted_at is not None

    # Default lookup excludes soft-deleted
    hidden = await repo.get_by_id(project.id)
    assert hidden is None

    # Explicit lookup includes soft-deleted
    found_deleted = await repo.get_by_id(project.id, include_deleted=True)
    assert found_deleted is not None
    assert found_deleted.id == project.id


@pytest.mark.asyncio
async def test_project_membership_and_scoping(db_session):
    project_repo = ProjectRepository(db_session)

    # Two users
    u1 = User(email="u1@test.com", password_hash="hash")
    u2 = User(email="u2@test.com", password_hash="hash")
    db_session.add_all([u1, u2])
    await db_session.flush()

    # Project owned by u1
    p1 = Project(name="Project 1")
    await project_repo.create(p1)
    await project_repo.add_member(p1.id, u1.id, role="owner")

    # Project owned by u2
    p2 = Project(name="Project 2")
    await project_repo.create(p2)
    await project_repo.add_member(p2.id, u2.id, role="owner")

    # u1 list
    u1_projects = await project_repo.list_by_user(u1.id)
    assert len(u1_projects) == 1
    assert u1_projects[0].id == p1.id

    # Add u2 as member to p1
    await project_repo.add_member(p1.id, u2.id, role="viewer")
    u2_projects = await project_repo.list_by_user(u2.id)
    assert len(u2_projects) == 2


@pytest.mark.asyncio
async def test_vector_search_with_metadata_filtering(db_session):
    file_repo = FileRepository(db_session)

    project_id = uuid.uuid4()
    other_project_id = uuid.uuid4()

    # File 1 in target project (PDF)
    f1 = File(
        project_id=project_id,
        filename="market.pdf",
        mime_type="application/pdf",
        storage_provider="local",
        storage_key="/tmp/f1",
        status="ready",
    )
    # File 2 in target project (Excel)
    f2 = File(
        project_id=project_id,
        filename="sales.xlsx",
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        storage_provider="local",
        storage_key="/tmp/f2",
        status="ready",
    )
    # File 3 in different project
    f3 = File(
        project_id=other_project_id,
        filename="other.pdf",
        mime_type="application/pdf",
        storage_provider="local",
        storage_key="/tmp/f3",
        status="ready",
    )
    db_session.add_all([f1, f2, f3])
    await db_session.flush()

    # Add chunks with embeddings
    # Target query vector is close to [1.0, 0.0, 0.0]
    c1 = FileChunk(file_id=f1.id, chunk_index=0, content="AI market trends", embedding=[0.99, 0.01, 0.0], page_number=1)
    c2 = FileChunk(file_id=f1.id, chunk_index=1, content="Unrelated chunk", embedding=[0.0, 1.0, 0.0], page_number=2)
    c3 = FileChunk(file_id=f2.id, chunk_index=0, content="Revenue numbers", embedding=[0.95, 0.05, 0.0], page_number=1)
    c4 = FileChunk(file_id=f3.id, chunk_index=0, content="Leaked info", embedding=[1.0, 0.0, 0.0], page_number=1)

    await file_repo.create_chunks([c1, c2, c3, c4])

    query_vec = [1.0, 0.0, 0.0]

    # Filter 1: Project scoping should exclude chunk c4 from other project
    filter_dto = VectorFilterDTO(project_id=project_id, top_k=5)
    results = await file_repo.similarity_search(filter_dto, query_vec)
    result_chunk_ids = [chunk.id for chunk, score in results]
    assert c4.id not in result_chunk_ids
    assert c1.id in result_chunk_ids
    assert results[0][0].id == c1.id  # Highest similarity first

    # Filter 2: Filter by mime_type="application/pdf" should exclude c3 (excel)
    filter_pdf = VectorFilterDTO(project_id=project_id, mime_types=["application/pdf"], top_k=5)
    results_pdf = await file_repo.similarity_search(filter_pdf, query_vec)
    pdf_chunk_ids = [chunk.id for chunk, _ in results_pdf]
    assert c3.id not in pdf_chunk_ids
    assert c1.id in pdf_chunk_ids


@pytest.mark.asyncio
async def test_run_repository_idempotency_and_steps(db_session):
    run_repo = RunRepository(db_session)
    project_id = uuid.uuid4()

    run = Run(
        project_id=project_id,
        prompt="Analyze LLM market",
        status="queued",
        idempotency_key="unique_request_xyz",
    )
    await run_repo.create(run)

    # Check retrieval by idempotency key
    found = await run_repo.get_by_idempotency(project_id, "unique_request_xyz")
    assert found is not None
    assert found.id == run.id

    # Update status
    await run_repo.update_status(found, status="running", current_step="planner", progress_pct=20)
    assert found.status == "running"
    assert found.started_at is not None
