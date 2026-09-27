from backend.observability import build_observability_summary


def test_aggregate_observability_summary():
    result = {
        "investigation_id": "abc",
        "planner_duration_ms": 10,
        "answer_duration_ms": 20,
        "investigation_duration_ms": 40,
        "answer_valid": True,
        "requires_human_review": False,
        "recovery_attempted": True,
        "tool_history": [
            {"tool": "incidents", "status": "success", "duration_ms": 4, "attempts": 2},
            {"tool": "status", "status": "error", "duration_ms": 6, "attempts": 1},
        ],
        "llm_history": [
            {
                "purpose": "planner",
                "model": "qwen",
                "prompt_version": "p1",
                "prompt_tokens": 10,
                "completion_tokens": 5,
            }
        ],
    }
    summary = build_observability_summary(result)
    assert summary["tool_execution_count"] == 2
    assert summary["tool_error_count"] == 1
    assert summary["tool_retry_count"] == 1
    assert summary["llm_total_tokens"] == 15
    assert summary["prompt_versions"] == ["p1"]
