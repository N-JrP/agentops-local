LIVE_POLICY_CASES = [
    {
        "name": "github_current_status",
        "question": "What is GitHub's current service status right now?",
        "expected_tools": ["status"],
    },
    {
        "name": "github_latest_incident",
        "question": "Investigate the latest GitHub incident and explain what happened.",
        "expected_tools": ["incidents"],
    },
    {
        "name": "github_incident_metrics",
        "question": (
            "How many major GitHub incidents are in recent history and what is "
            "the average resolution time?"
        ),
        "expected_tools": ["incident_metrics"],
    },
    {
        "name": "github_actions_incidents",
        "question": (
            "Investigate recent GitHub Actions incidents and summarize what GitHub reported."
        ),
        "expected_tools": ["incidents"],
    },
    {
        "name": "github_status_and_metrics",
        "question": (
            "What is GitHub's current status and how many incidents occurred in the last 7 days?"
        ),
        "expected_tools": ["status", "incident_metrics"],
    },
    {
        "name": "github_status_and_latest_incident",
        "question": "What is GitHub's current status and what happened in the latest incident?",
        "expected_tools": ["status", "incidents"],
    },
]
