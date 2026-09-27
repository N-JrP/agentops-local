import json
from datetime import datetime, timezone

from backend.config import settings
from backend.persistence import save_evaluation_report
from backend.tools.public_status_tool import (
    get_public_incident_metrics,
    get_public_status_summary,
    online_source_health,
    search_public_incidents,
)


def main() -> None:
    health = online_source_health()
    summary = get_public_status_summary()
    incidents = search_public_incidents("latest", limit=1)
    metrics = get_public_incident_metrics()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configured_source": settings.public_status_name,
        "base_url": settings.public_status_base_url,
        "health": health,
        "current_status": {
            "description": summary.get("description"),
            "indicator": summary.get("indicator"),
            "non_operational_components": summary.get("non_operational_components"),
        },
        "latest_incident": incidents[0] if incidents else None,
        "incident_metrics": metrics,
    }

    if not health.get("ok"):
        raise RuntimeError("Online source health check failed")
    if "githubstatus.com" in settings.public_status_base_url and not incidents:
        raise RuntimeError("GitHub Status returned no recent incidents")

    report["persistence_id"] = save_evaluation_report(report, evaluation_type="live-source")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
