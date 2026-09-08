import uuid
import pytest
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.file import File, FileChunk
from app.models.run import Run, RunStep
from app.models.run_event import RunEvent
from app.models.evidence import Evidence
from app.models.report import Report, ReportSection, Citation
from app.models.audit import AuditLog


@pytest.mark.asyncio
async def test_all_models_instantiation_and_persistence(db_session):
    # 1. Create User
    user = User(
        email="researcher@deepmind.com",
        password_hash="hashed_secret",
        name="Dr. Mercury",
    )
    db_session.add(user)
    await db_session.flush()
    assert user.id is not None
    assert user.is_active is True

    # 2. Create Project & Membership
    project = Project(
        name="Vietnam AI Ecosystem 2026",
        description="Comprehensive analysis of Vietnam's AI market landscape.",
    )
    db_session.add(project)
    await db_session.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role="owner",
    )
    db_session.add(member)
    await db_session.flush()

    # 3. Create Conversation
    conv = Conversation(
        project_id=project.id,
        created_by_user_id=user.id,
        title="Market Survey",
        langgraph_thread_id="lg_thread_999",
    )
    db_session.add(conv)
    await db_session.flush()

    # 4. Create Message
    msg = Message(
        conversation_id=conv.id,
        role="user",
        content="Analyze recent venture capital deals in Vietnam.",
    )
    db_session.add(msg)
    await db_session.flush()

    # 5. Create File & File Chunk
    file_obj = File(
        project_id=project.id,
        created_by_user_id=user.id,
        filename="report.pdf",
        mime_type="application/pdf",
        size_bytes=1048576,
        storage_provider="local",
        storage_key="/tmp/report.pdf",
        status="ready",
        idempotency_key="upload_key_001",
    )
    db_session.add(file_obj)
    await db_session.flush()

    chunk = FileChunk(
        file_id=file_obj.id,
        chunk_index=0,
        content="In 2025, VC funding for AI startups grew by 45%...",
        page_number=1,
        embedding=[0.1, 0.2, 0.3],
    )
    db_session.add(chunk)
    await db_session.flush()

    # 6. Create Run, RunStep & RunEvent
    run = Run(
        project_id=project.id,
        created_by_user_id=user.id,
        conversation_id=conv.id,
        prompt="Analyze venture capital growth",
        status="running",
        current_step="web_researcher",
        progress_pct=50,
        idempotency_key="run_key_001",
        langgraph_thread_id="lg_thread_999",
    )
    db_session.add(run)
    await db_session.flush()

    step = RunStep(
        run_id=run.id,
        agent_name="planner",
        step_name="generate_search_plan",
        status="completed",
        duration_ms=120,
    )
    db_session.add(step)

    event = RunEvent(
        run_id=run.id,
        event_type="agent_progress",
        agent_name="web_researcher",
        step_number=2,
        payload={"sources_found": 12},
    )
    db_session.add(event)
    await db_session.flush()

    # 7. Create Evidence
    evidence = Evidence(
        run_id=run.id,
        type="web",
        content="Vietnam AI startup funding hit record highs according to TechInAsia.",
        source_url="https://techinasia.com/vietnam-ai-2025",
        source_title="Vietnam AI Boom",
        source_domain="techinasia.com",
        relevance_score=0.95,
    )
    db_session.add(evidence)
    await db_session.flush()

    # 8. Create Report, Section & Citation
    report = Report(
        run_id=run.id,
        project_id=project.id,
        created_by_user_id=user.id,
        title="Vietnam AI Market Report",
        content="# Full Market Analysis...",
    )
    db_session.add(report)
    await db_session.flush()

    section = ReportSection(
        report_id=report.id,
        section_key="executive_summary",
        title="Executive Summary",
        content="AI investment experienced high momentum [1].",
        section_order=1,
    )
    db_session.add(section)
    await db_session.flush()

    citation = Citation(
        report_section_id=section.id,
        evidence_id=evidence.id,
        citation_text="[1] TechInAsia Vietnam AI Boom 2025",
        position=1,
    )
    db_session.add(citation)
    await db_session.flush()

    # 9. Create Audit Log
    audit = AuditLog(
        user_id=user.id,
        project_id=project.id,
        action="report.generate",
        resource_type="report",
        resource_id=str(report.id),
    )
    db_session.add(audit)
    await db_session.flush()

    assert report.id is not None
    assert section.id is not None
    assert citation.id is not None
    assert audit.id is not None
