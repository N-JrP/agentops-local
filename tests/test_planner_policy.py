from backend.agent.nodes import _required_tools_from_question


def test_multi_tool_policy_is_minimal():
    question = (
        "Investigate the PaymentGatewayTimeout incident. What errors occurred, "
        "what operational metrics changed, and what should an engineer do?"
    )
    assert _required_tools_from_question(question) == [
        "metrics",
        "logs",
        "knowledge",
    ]


def test_knowledge_only_does_not_add_logs():
    question = "What should an engineer do when investigating PaymentGatewayTimeout?"
    assert _required_tools_from_question(question) == ["knowledge"]


def test_live_github_status_uses_status_tool():
    question = "What is GitHub's current service status right now?"
    assert _required_tools_from_question(question) == ["status"]


def test_latest_github_incident_uses_online_incident_tool():
    question = "Investigate the latest GitHub incident and explain what happened."
    assert _required_tools_from_question(question) == ["incidents"]


def test_github_incident_metrics_use_online_metrics_tool():
    question = "How many major GitHub incidents were there and what is average resolution time?"
    assert _required_tools_from_question(question) == ["incident_metrics"]


def test_unsupported_question_returns_no_tools():
    assert _required_tools_from_question("What is the weather in Berlin today?") == []


def test_latest_github_incident_does_not_add_current_status():
    question = (
        "Investigate the latest GitHub incident. What happened, which components "
        "were affected, and how was it resolved?"
    )
    assert _required_tools_from_question(question) == ["incidents"]


def test_dynamic_sql_order_lookup_uses_sql_tool():
    assert _required_tools_from_question("Show order 1002 from the local database") == ["sql"]


def test_github_status_plus_incident_metrics_is_multi_tool():
    question = "What is GitHub's current status and how many incidents occurred in the last 7 days?"
    assert _required_tools_from_question(question) == ["status", "incident_metrics"]
