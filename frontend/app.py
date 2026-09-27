import os
from uuid import uuid4

import pandas as pd
import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="AgentOps Local", layout="wide")
st.title("AgentOps Local")
st.caption(
    "Local-first AI incident investigation using live GitHub Status evidence, "
    "LangGraph orchestration, deterministic grounding checks, and observable tool traces."
)

if "session_id" not in st.session_state:
    st.session_state.session_id = f"demo-{uuid4().hex[:8]}"

with st.sidebar:
    st.subheader("Runtime")
    st.code(API_URL, language=None)
    st.text_input("Session ID", key="session_id")
    try:
        health = requests.get(f"{API_URL}/source-health", timeout=10).json()
        if health.get("ok"):
            st.success(f"Live source: {health.get('source')} - online")
            st.caption(f"Fetched: {health.get('fetched_at')}")
        else:
            st.warning("Live source health check did not pass.")
    except Exception:
        st.info("Start FastAPI to enable live source health status.")

question = st.text_area(
    "Investigation question",
    value=(
        "Investigate the latest GitHub incident. What happened, which components "
        "were affected, and how was it resolved?"
    ),
    height=110,
)

if st.button("Run investigation", type="primary", use_container_width=True):
    with st.spinner("Fetching live evidence and investigating locally..."):
        response = requests.post(
            f"{API_URL}/investigate",
            json={
                "question": question,
                "session_id": st.session_state.session_id,
                "approved_tools": [],
            },
            timeout=420,
        )

    if not response.ok:
        st.error(f"Backend error: {response.status_code} ÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Â {response.text}")
        st.stop()

    result = response.json()

    st.subheader("Final answer")
    st.markdown(result["answer"])

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Answer valid", str(result["answer_valid"]))
    c2.metric("Human review", str(result["requires_human_review"]))
    c3.metric("Planner ms", round(result["planner_duration_ms"], 1))
    c4.metric("Answer ms", round(result["answer_duration_ms"], 1))
    c5.metric("Total ms", round(result["investigation_duration_ms"], 1))

    st.caption(
        f"Investigation ID: `{result['investigation_id']}` | "
        f"Persistence ID: `{result.get('persistence_id')}`"
    )

    plan_tab, trace_tab, evidence_tab, obs_tab, validation_tab = st.tabs(
        ["Plan", "Execution trace", "Evidence", "Observability", "Validation & recovery"]
    )

    with plan_tab:
        st.dataframe(pd.DataFrame(result["plan"]), use_container_width=True)

    with trace_tab:
        trace_rows = []
        for item in result["tool_history"]:
            trace_rows.append(
                {
                    "tool": item.get("tool"),
                    "input": item.get("tool_input"),
                    "status": item.get("status"),
                    "attempts": item.get("attempts", 1),
                    "duration_ms": item.get("duration_ms"),
                    "recovery": item.get("recovery", False),
                    "error": item.get("error", ""),
                }
            )
        st.dataframe(pd.DataFrame(trace_rows), use_container_width=True)

    with evidence_tab:
        left, right = st.columns(2)
        with left:
            st.markdown("#### Live online evidence")
            st.json(
                {
                    "status": result.get("status_result", {}),
                    "incidents": result.get("incident_result", []),
                    "incident_metrics": result.get("incident_metrics", {}),
                }
            )
        with right:
            st.markdown("#### Local deterministic fixtures")
            st.json(
                {
                    "metrics": result.get("metrics", {}),
                    "sql": result.get("sql_result", {}),
                    "logs": result.get("log_result", []),
                    "knowledge": result.get("knowledge_result", ""),
                }
            )

    with obs_tab:
        summary = result.get("observability_summary", {})
        st.json(summary)
        if result.get("llm_history"):
            st.markdown("#### Local LLM calls")
            st.dataframe(pd.DataFrame(result["llm_history"]), use_container_width=True)

    with validation_tab:
        st.json(
            {
                "answer_attempts": result.get("answer_attempts", 1),
                "answer_valid": result["answer_valid"],
                "issues": result["answer_validation_issues"],
                "requires_human_review": result["requires_human_review"],
                "recovery_attempted": result.get("recovery_attempted", False),
                "recovery_actions": result.get("recovery_actions", []),
            }
        )

