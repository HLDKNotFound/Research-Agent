from typing import Any, Dict
from app.agents.state import ResearchState
from app.core.llm import llm_client


async def planner_node(state: ResearchState) -> Dict[str, Any]:
    """
    Planner Agent Node:
    Analyzes the research question using GLM-4.7 to decompose it into
    structured, orthogonal sub-investigations (with deterministic fallback).
    """
    prompt = state["prompt"]

    # 1. Attempt GLM-4.7 LLM query decomposition
    sub_queries = []
    llm_text = await llm_client.chat_completion(
        messages=[
            {
                "role": "system",
                "content": "You are a senior scientific research planner. Given a research question, generate 4 orthogonal, targeted sub-questions for deep investigation. Output each sub-question on its own line.",
            },
            {"role": "user", "content": prompt},
        ]
    )
    if llm_text:
        lines = [line.strip().lstrip("1234567890.- ") for line in llm_text.split("\n") if line.strip()]
        if len(lines) >= 3:
            sub_queries = lines[:4]

    # 2. Fallback to structured analytical sub-queries if offline or API key omitted
    if not sub_queries:
        sub_queries = [
            f"Empirical benchmarks and literature on '{prompt}'",
            f"Theoretical frameworks and error analysis for '{prompt}'",
            f"Statistical datasets and telemetry relating to '{prompt}'",
            f"Practical implementations and future recommendations for '{prompt}'",
        ]

    step_record = {
        "agent": "Planner Agent",
        "step": "Planning & Sub-Query Formulation",
        "status": "completed",
        "message": f"Formulated {len(sub_queries)} targeted research sub-queries.",
        "progress_pct": 20,
    }

    return {
        "sub_queries": sub_queries,
        "current_step": "planning_completed",
        "progress_pct": 20,
        "steps_log": state.get("steps_log", []) + [step_record],
    }
