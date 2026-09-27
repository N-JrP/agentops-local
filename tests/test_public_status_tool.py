from backend.tools import public_status_tool

SUMMARY_PAYLOAD = {
    "page": {"updated_at": "2026-09-22T10:00:00Z"},
    "status": {"indicator": "minor", "description": "Minor Service Outage"},
    "components": [
        {"name": "API Requests", "status": "degraded_performance", "showcase": True},
        {"name": "Actions", "status": "operational", "showcase": True},
    ],
    "incidents": [
        {
            "id": "inc-1",
            "name": "API degradation",
            "status": "investigating",
            "impact": "minor",
            "updated_at": "2026-09-22T10:00:00Z",
        }
    ],
}

INCIDENTS_PAYLOAD = {
    "incidents": [
        {
            "id": "inc-1",
            "name": "API degradation",
            "status": "resolved",
            "impact": "major",
            "created_at": "2026-09-22T08:00:00Z",
            "started_at": "2026-09-22T08:00:00Z",
            "resolved_at": "2026-09-22T09:00:00Z",
            "shortlink": "https://example.test/inc-1",
            "components": [{"name": "API Requests"}],
            "incident_updates": [
                {
                    "status": "resolved",
                    "body": "Issue resolved.<br />Traffic is normal.",
                    "created_at": "2026-09-22T09:00:00Z",
                    "affected_components": [
                        {
                            "name": "API Requests",
                            "old_status": "degraded_performance",
                            "new_status": "operational",
                        }
                    ],
                },
                {
                    "status": "investigating",
                    "body": "Investigating elevated API errors.",
                    "created_at": "2026-09-22T08:00:00Z",
                    "affected_components": [],
                },
            ],
        },
        {
            "id": "inc-2",
            "name": "Actions delay",
            "status": "resolved",
            "impact": "minor",
            "created_at": "2026-09-21T08:00:00Z",
            "started_at": "2026-09-21T08:00:00Z",
            "resolved_at": "2026-09-21T08:30:00Z",
            "shortlink": "https://example.test/inc-2",
            "components": [{"name": "Actions"}],
            "incident_updates": [],
        },
    ]
}


def _fake_fetch(path: str):
    if path == "summary.json":
        return SUMMARY_PAYLOAD
    if path == "incidents.json":
        return INCIDENTS_PAYLOAD
    raise AssertionError(path)


def test_live_status_summary_shape(monkeypatch):
    monkeypatch.setattr(public_status_tool, "_fetch_json", _fake_fetch)
    result = public_status_tool.get_public_status_summary()
    assert result["description"] == "Minor Service Outage"
    assert result["non_operational_components"][0]["name"] == "API Requests"
    assert result["source_url"].endswith("/summary.json")


def test_public_incident_search(monkeypatch):
    monkeypatch.setattr(public_status_tool, "_fetch_json", _fake_fetch)
    result = public_status_tool.search_public_incidents("API errors", limit=3)
    assert len(result) == 1
    assert result[0]["name"] == "API degradation"
    assert result[0]["duration_minutes"] == 60.0
    assert result[0]["updates"][1]["body"] == "Issue resolved.\nTraffic is normal."


def test_public_incident_metrics(monkeypatch):
    monkeypatch.setattr(public_status_tool, "_fetch_json", _fake_fetch)
    result = public_status_tool.get_public_incident_metrics()
    assert result["recent_incident_count"] == 2
    assert result["major_incident_count"] == 1
    assert result["minor_incident_count"] == 1
    assert result["average_resolution_minutes"] == 45.0
    assert result["current_non_operational_component_count"] == 1


def test_latest_incident_uses_recency_not_keyword_score(monkeypatch):
    monkeypatch.setattr(public_status_tool, "_fetch_json", _fake_fetch)
    result = public_status_tool.search_public_incidents(
        "latest GitHub incident affected resolved",
        limit=3,
    )
    assert len(result) == 1
    assert result[0]["id"] == "inc-1"
