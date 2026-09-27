from typing import Any, Dict, List, TypedDict


class AgentState(TypedDict):
    question: str
    investigation_id: str
    approved_tools: List[str]
    security_blocked: bool
    security_reason: str

    selected_tool: str
    tool_input: str

    plan: List[Dict[str, str]]
    current_step: int
    recovery_attempted: bool
    recovery_actions: List[Dict[str, Any]]

    planner_duration_ms: float
    planner_attempts: int
    answer_duration_ms: float
    answer_attempts: int
    answer_valid: bool
    answer_validation_issues: List[str]
    requires_human_review: bool

    tool_history: List[Dict[str, Any]]
    llm_history: List[Dict[str, Any]]

    status_result: Dict[str, Any]
    incident_result: List[Dict[str, Any]]
    incident_metrics: Dict[str, Any]

    metrics: Dict[str, Any]
    sql_result: Dict[str, Any]
    log_result: List[str]
    knowledge_result: str

    observability_summary: Dict[str, Any]
    answer: str
