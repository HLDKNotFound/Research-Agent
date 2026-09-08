from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class ResearchState(TypedDict):
    """LangGraph State representation for the multi-agent research workflow."""
    project_id: str
    run_id: str
    user_id: str
    prompt: str
    sub_queries: List[str]
    file_evidence: List[Dict[str, Any]]
    web_evidence: List[Dict[str, Any]]
    data_analysis_results: Dict[str, Any]
    critic_verdict: Dict[str, Any]
    report_title: str
    report_sections: List[Dict[str, Any]]
    citations: List[Dict[str, Any]]
    current_step: str
    progress_pct: int
    steps_log: List[Dict[str, Any]]
    is_verified: bool
    retry_count: int
    error: Optional[str]
