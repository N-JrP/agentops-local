from backend.agent import nodes


def _minimal_state() -> dict:
    return {
        "question": "What is GitHub's current service status right now?",
        "investigation_id": "test-investigation",
        "tool_input": "current GitHub status",
        "tool_history": [],
        "plan": [{"tool": "status", "tool_input": "current GitHub status"}],
        "recovery_attempted": False,
        "recovery_actions": [],
    }


def test_online_tool_retries_transient_failure(monkeypatch):
    calls = {"count": 0}

    def flaky_execute(tool_name: str, tool_input: str):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("temporary timeout")
        return {"description": "All Systems Operational"}

    monkeypatch.setattr(nodes, "execute_tool", flaky_execute)
    monkeypatch.setattr(nodes.time, "sleep", lambda _: None)

    result = nodes._run_tool(_minimal_state(), "status", "status_result")
    assert calls["count"] == 2
    assert result["status_result"]["description"] == "All Systems Operational"
    assert result["tool_history"][-1]["attempts"] == 2
    assert result["tool_history"][-1]["status"] == "success"


def test_recovery_replans_failed_tool_once(monkeypatch):
    state = _minimal_state()
    state["tool_history"] = [
        {
            "tool": "status",
            "tool_input": "current GitHub status",
            "status": "error",
            "duration_ms": 10,
            "attempts": 2,
            "error": "temporary failure",
        }
    ]

    monkeypatch.setattr(
        nodes,
        "execute_tool",
        lambda tool_name, tool_input: {"description": "All Systems Operational"},
    )

    result = nodes.recover_failed_tools(state)
    assert result["recovery_attempted"] is True
    assert result["recovery_actions"] == [{"tool": "status", "status": "recovered"}]
    assert result["tool_history"][-1]["recovery"] is True
    assert result["tool_history"][-1]["status"] == "success"
