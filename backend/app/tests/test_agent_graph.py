import pytest
import uuid
from app.agents.agentic import (
    critic_node,
    data_analyst_node,
    file_analyst_node,
    planner_node,
    report_writer_node,
    web_researcher_node,
)
from app.agents.graph import execute_research_workflow
from app.agents.state import ResearchState


@pytest.mark.asyncio
async def test_langgraph_multi_agent_execution():
    project_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    prompt = "Compare error mitigation techniques in NISQ quantum computing"

    final_state = await execute_research_workflow(
        project_id=project_id,
        run_id=run_id,
        user_id=user_id,
        prompt=prompt,
        thread_id=f"thread-{run_id}",
    )

    # 1. State Progression & Completion
    assert final_state["current_step"] == "completed"
    assert final_state["progress_pct"] == 100
    assert final_state["is_verified"] is True
    assert final_state["error"] is None

    # 2. Strict Sub-Queries Validation
    sub_queries = final_state["sub_queries"]
    assert len(sub_queries) == 4
    for q in sub_queries:
        assert isinstance(q, str) and len(q) > 10
        assert any(word in q.lower() for word in ["quantum", "mitigation", "error", "nisq"]) or prompt.lower() in q.lower()

    # 3. Strict Evidence Validation (File & Web)
    file_ev = final_state["file_evidence"]
    web_ev = final_state["web_evidence"]
    assert len(file_ev) >= 1
    assert len(web_ev) >= 1

    for ev in file_ev + web_ev:
        # Validate UUID
        uuid.UUID(ev["id"])
        assert ev["source_type"] in ("document", "web")
        assert len(ev["title"]) > 3
        assert len(ev["content"]) > 10
        assert 0.0 <= ev["relevance_score"] <= 1.0
        assert ev["relevance_score"] >= 0.80

    # 4. Strict Statistical & Empirical Data Validation
    data_res = final_state["data_analysis_results"]
    assert "mean" in data_res
    assert "confidence_interval_95" in data_res
    ci = data_res["confidence_interval_95"]
    assert isinstance(ci, list) and len(ci) == 2
    assert ci[0] < data_res["mean"] < ci[1], f"Mean {data_res['mean']} not in CI [{ci[0]}, {ci[1]}]"
    assert data_res["sample_size"] == 8
    assert data_res["p_value"] < 0.001
    assert data_res["statistical_significance"] is True

    # 5. Strict Critic / Verifier Validation
    critic = final_state["critic_verdict"]
    assert critic["verified"] is True
    assert critic["confidence_score"] >= 0.95
    assert critic["hallucinations_detected"] == 0
    assert critic["total_sources_evaluated"] == len(file_ev) + len(web_ev)

    # 6. Strict Report Sections & Citations Validation
    sections = final_state["report_sections"]
    assert len(sections) in (3, 4)
    section_keys = [s["section_key"] for s in sections]
    assert "executive_summary" in section_keys
    assert "strategic_recommendations" in section_keys

    # Section orders must be strictly monotonically increasing
    orders = [s["section_order"] for s in sections]
    assert orders == list(range(1, len(sections) + 1))

    citations = final_state["citations"]
    assert len(citations) >= 2
    for idx, cit in enumerate(citations, 1):
        assert cit["marker"] == f"[{idx}]"
        assert len(cit["snippet"]) > 0
        assert len(cit["title"]) > 0
        assert 0.0 <= cit["relevance_score"] <= 1.0

    # Verify citation markers appear in the section text
    assert "[1]" in sections[0]["content"]
    assert "[2]" in sections[1]["content"] or "[3]" in sections[1]["content"]

    # 7. Strict Multi-Agent Workflow Sequence & Monotonic Progress
    steps_log = final_state["steps_log"]
    assert len(steps_log) == 6
    expected_agents = [
        "Planner Agent",
        "File Analyst Agent",
        "Web Researcher Agent",
        "Data Analyst Agent",
        "Critic / Verifier Agent",
        "Report Writer Agent",
    ]
    agents = [step["agent"] for step in steps_log]
    assert agents == expected_agents

    last_pct = 0
    for step in steps_log:
        assert step["status"] == "completed"
        assert len(step["message"]) > 0
        assert len(step["step"]) > 0
        assert step["progress_pct"] >= last_pct, f"Progress decreased: {step['progress_pct']} < {last_pct}"
        last_pct = step["progress_pct"]
    assert last_pct == 100


@pytest.mark.asyncio
async def test_agent_nodes_individual_unit_isolation():
    """Unit tests verifying individual nodes in isolation with edge-case states."""
    test_state: ResearchState = {
        "project_id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "prompt": "Quantum gate fidelity",
        "sub_queries": [],
        "file_evidence": [],
        "web_evidence": [],
        "data_analysis_results": {},
        "critic_verdict": {},
        "report_title": "",
        "report_sections": [],
        "citations": [],
        "current_step": "init",
        "progress_pct": 0,
        "steps_log": [],
        "is_verified": False,
        "retry_count": 0,
        "error": None,
    }

    # 1. Planner Node isolation
    planner_out = await planner_node(test_state)
    assert len(planner_out["sub_queries"]) == 4
    assert planner_out["progress_pct"] == 20
    assert planner_out["current_step"] == "planning_completed"

    # 2. File Analyst Node isolation
    file_out = await file_analyst_node(test_state)
    assert len(file_out["file_evidence"]) == 1
    assert file_out["file_evidence"][0]["relevance_score"] >= 0.90

    # 3. Web Researcher Node isolation
    web_out = await web_researcher_node(test_state)
    assert len(web_out["web_evidence"]) >= 1
    assert web_out["web_evidence"][0]["source_type"] == "web"

    # 4. Data Analyst Node isolation
    data_out = await data_analyst_node(test_state)
    assert data_out["data_analysis_results"]["statistical_significance"] is True

    # 5. Critic Node isolation with mock evidence
    test_state_with_ev = {
        **test_state,
        "file_evidence": file_out["file_evidence"],
        "web_evidence": web_out["web_evidence"],
    }
    critic_out = await critic_node(test_state_with_ev)
    assert critic_out["critic_verdict"]["verified"] is True
    assert critic_out["is_verified"] is True

    # 6. Report Writer Node isolation
    test_state_full = {
        **test_state_with_ev,
        "data_analysis_results": data_out["data_analysis_results"],
    }
    writer_out = await report_writer_node(test_state_full)
    assert len(writer_out["report_sections"]) in (3, 4)
    assert len(writer_out["citations"]) >= 2
    assert writer_out["progress_pct"] == 100
