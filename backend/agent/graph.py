import time
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from opentelemetry import trace

from backend.agent.nodes import (
    advance_step,
    approval_required,
    generate_investigation_answer,
    get_incident_metrics,
    get_knowledge_data,
    get_log_data,
    get_metrics,
    get_public_incidents,
    get_public_status,
    get_sql_data,
    plan_investigation,
    prepare_current_step,
    recover_failed_tools,
    security_blocked_answer,
    security_guard,
    unsupported_tool,
)
from backend.agent.state import AgentState
from backend.observability import build_observability_summary
from backend.security import approval_granted, requires_approval

tracer = trace.get_tracer("agentops.graph")


def security_route(state: AgentState) -> str:
    return "blocked" if state.get("security_blocked") else "continue"


def choose_tool(state: AgentState) -> str:
    selected = state["selected_tool"]
    if requires_approval(selected) and not approval_granted(
        selected, state.get("approved_tools", [])
    ):
        return "approval"
    if selected in {
        "status",
        "incidents",
        "incident_metrics",
        "metrics",
        "sql",
        "logs",
        "knowledge",
    }:
        return selected
    return "unsupported"


def continue_or_finish(state: AgentState) -> str:
    return "continue" if state["current_step"] < len(state["plan"]) else "finish"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("security_guard", security_guard)
    graph.add_node("security_blocked_answer", security_blocked_answer)
    graph.add_node("plan_investigation", plan_investigation)
    graph.add_node("prepare_current_step", prepare_current_step)
    graph.add_node("approval_required", approval_required)
    graph.add_node("get_public_status", get_public_status)
    graph.add_node("get_public_incidents", get_public_incidents)
    graph.add_node("get_incident_metrics", get_incident_metrics)
    graph.add_node("get_metrics", get_metrics)
    graph.add_node("get_sql_data", get_sql_data)
    graph.add_node("get_log_data", get_log_data)
    graph.add_node("get_knowledge_data", get_knowledge_data)
    graph.add_node("advance_step", advance_step)
    graph.add_node("recover_failed_tools", recover_failed_tools)
    graph.add_node("generate_investigation_answer", generate_investigation_answer)
    graph.add_node("unsupported_tool", unsupported_tool)

    graph.add_edge(START, "security_guard")
    graph.add_conditional_edges(
        "security_guard",
        security_route,
        {
            "blocked": "security_blocked_answer",
            "continue": "plan_investigation",
        },
    )
    graph.add_edge("security_blocked_answer", END)

    graph.add_edge("plan_investigation", "prepare_current_step")

    graph.add_conditional_edges(
        "prepare_current_step",
        choose_tool,
        {
            "status": "get_public_status",
            "incidents": "get_public_incidents",
            "incident_metrics": "get_incident_metrics",
            "metrics": "get_metrics",
            "sql": "get_sql_data",
            "logs": "get_log_data",
            "knowledge": "get_knowledge_data",
            "approval": "approval_required",
            "unsupported": "unsupported_tool",
        },
    )

    for node_name in (
        "get_public_status",
        "get_public_incidents",
        "get_incident_metrics",
        "get_metrics",
        "get_sql_data",
        "get_log_data",
        "get_knowledge_data",
    ):
        graph.add_edge(node_name, "advance_step")

    graph.add_conditional_edges(
        "advance_step",
        continue_or_finish,
        {
            "continue": "prepare_current_step",
            "finish": "recover_failed_tools",
        },
    )

    graph.add_edge("recover_failed_tools", "generate_investigation_answer")
    graph.add_edge("generate_investigation_answer", END)
    graph.add_edge("approval_required", END)
    graph.add_edge("unsupported_tool", END)
    return graph.compile()


app = build_graph()


def initial_state(question: str, approved_tools: list[str] | None = None) -> AgentState:
    return {
        "question": question,
        "investigation_id": str(uuid4()),
        "approved_tools": approved_tools or [],
        "security_blocked": False,
        "security_reason": "",
        "selected_tool": "",
        "tool_input": "",
        "plan": [],
        "current_step": 0,
        "recovery_attempted": False,
        "recovery_actions": [],
        "planner_duration_ms": 0.0,
        "planner_attempts": 0,
        "answer_duration_ms": 0.0,
        "answer_attempts": 0,
        "answer_valid": False,
        "answer_validation_issues": [],
        "requires_human_review": False,
        "tool_history": [],
        "llm_history": [],
        "status_result": {},
        "incident_result": [],
        "incident_metrics": {},
        "metrics": {},
        "sql_result": {},
        "log_result": [],
        "knowledge_result": "",
        "observability_summary": {},
        "answer": "",
    }


def run_investigation(question: str, approved_tools: list[str] | None = None) -> dict:
    state = initial_state(question, approved_tools=approved_tools)
    start = time.perf_counter()

    with tracer.start_as_current_span("agentops.investigation") as span:
        span.set_attribute("agentops.investigation_id", state["investigation_id"])
        result = app.invoke(state)
        result["investigation_duration_ms"] = round(
            (time.perf_counter() - start) * 1000,
            2,
        )
        result["observability_summary"] = build_observability_summary(result)
        span.set_attribute("agentops.answer_valid", bool(result.get("answer_valid")))
        span.set_attribute(
            "agentops.requires_human_review",
            bool(result.get("requires_human_review")),
        )
        return result


if __name__ == "__main__":
    result = run_investigation(
        "Investigate the latest GitHub incident. What happened, which components "
        "were affected, and how was it resolved?"
    )
    print(result)
