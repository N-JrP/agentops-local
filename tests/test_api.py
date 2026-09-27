from fastapi.testclient import TestClient

from backend import main


def _fake_result(question: str) -> dict:
    return {
        "investigation_id": "inv-test",
        "question": question,
        "plan": [{"tool": "status", "tool_input": "current"}],
        "current_step": 1,
        "answer": "All Systems Operational",
        "answer_valid": True,
        "answer_validation_issues": [],
        "requires_human_review": False,
        "planner_duration_ms": 1.0,
        "answer_duration_ms": 2.0,
        "investigation_duration_ms": 4.0,
        "tool_history": [],
        "llm_history": [],
        "observability_summary": {},
        "recovery_attempted": False,
        "recovery_actions": [],
        "status_result": {},
        "incident_result": [],
        "incident_metrics": {},
        "metrics": {},
        "sql_result": {},
        "log_result": [],
        "knowledge_result": "",
        "answer_attempts": 1,
        "selected_tool": "status",
        "tool_input": "current",
        "planner_attempts": 1,
        "security_blocked": False,
        "security_reason": "",
        "approved_tools": [],
    }


def test_health_endpoint():
    with TestClient(main.app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_investigate_returns_structured_response(monkeypatch):
    monkeypatch.setattr(
        main,
        "run_investigation",
        lambda question, approved_tools=None: _fake_result(question),
    )
    monkeypatch.setattr(main, "save_investigation", lambda question, result: 123)
    monkeypatch.setattr(main, "record_investigation_metrics", lambda result: None)

    with TestClient(main.app) as client:
        response = client.post(
            "/investigate",
            json={"question": "What is GitHub's current status?"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["investigation_id"] == "inv-test"
    assert payload["persistence_id"] == 123
    assert payload["answer_valid"] is True
