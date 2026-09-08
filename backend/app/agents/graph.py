from typing import Any, Dict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from app.agents.agentic import (
    critic_node,
    data_analyst_node,
    file_analyst_node,
    planner_node,
    report_writer_node,
    web_researcher_node,
)
from app.agents.state import ResearchState


def build_research_graph():
    """
    Constructs the LangGraph StateGraph representing the multi-agent research workflow:
    START -> Planner -> File Analyst -> Web Researcher -> Data Analyst -> Critic -> Report Writer -> END
    """
    workflow = StateGraph(ResearchState)

    # 1. Add Agent Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("file_analyst", file_analyst_node)
    workflow.add_node("web_researcher", web_researcher_node)
    workflow.add_node("data_analyst", data_analyst_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("report_writer", report_writer_node)

    # 2. Add Transitions & Edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "file_analyst")
    workflow.add_edge("file_analyst", "web_researcher")
    workflow.add_edge("web_researcher", "data_analyst")
    workflow.add_edge("data_analyst", "critic")
    workflow.add_edge("critic", "report_writer")
    workflow.add_edge("report_writer", END)

    # 3. Attach checkpointer for thread persistence
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Compiled workflow instance
research_graph = build_research_graph()


async def execute_research_workflow(
    project_id: str,
    run_id: str,
    user_id: str,
    prompt: str,
    thread_id: str = "default-thread",
) -> ResearchState:
    """
    Executes the full LangGraph multi-agent research pipeline asynchronously.
    Returns the finalized ResearchState containing report sections, citations, and steps log.
    """
    initial_state: ResearchState = {
        "project_id": project_id,
        "run_id": run_id,
        "user_id": user_id,
        "prompt": prompt,
        "sub_queries": [],
        "file_evidence": [],
        "web_evidence": [],
        "data_analysis_results": {},
        "critic_verdict": {},
        "report_title": "",
        "report_sections": [],
        "citations": [],
        "current_step": "started",
        "progress_pct": 0,
        "steps_log": [],
        "is_verified": False,
        "retry_count": 0,
        "error": None,
    }

    config = {"configurable": {"thread_id": thread_id}}
    final_state = await research_graph.ainvoke(initial_state, config=config)
    return final_state
