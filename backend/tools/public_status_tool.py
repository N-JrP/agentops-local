import html
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from backend.config import settings

_GENERIC_TERMS = {
    "a",
    "an",
    "and",
    "are",
    "current",
    "github",
    "incident",
    "incidents",
    "latest",
    "most",
    "of",
    "recent",
    "service",
    "status",
    "the",
    "what",
    "with",
}


def _strip_html(value: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _fetch_json(path: str) -> dict[str, Any]:
    url = f"{settings.public_status_base_url.rstrip('/')}/{path.lstrip('/')}"
    with httpx.Client(
        timeout=settings.external_http_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "AgentOps-Local/1.0"},
    ) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def get_public_status_summary() -> dict[str, Any]:
    """Fetch the configured public Statuspage summary in real time."""
    payload = _fetch_json("summary.json")
    components = payload.get("components", [])
    incidents = payload.get("incidents", [])
    non_operational = [
        {
            "name": component.get("name"),
            "status": component.get("status"),
            "description": component.get("description"),
        }
        for component in components
        if component.get("showcase", True)
        and component.get("status") != "operational"
    ]

    return {
        "source": settings.public_status_name,
        "source_url": f"{settings.public_status_base_url.rstrip('/')}/summary.json",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "page_updated_at": payload.get("page", {}).get("updated_at"),
        "indicator": payload.get("status", {}).get("indicator"),
        "description": payload.get("status", {}).get("description"),
        "component_count": len([c for c in components if c.get("showcase", True)]),
        "non_operational_components": non_operational,
        "unresolved_incidents": [
            {
                "id": incident.get("id"),
                "name": incident.get("name"),
                "status": incident.get("status"),
                "impact": incident.get("impact"),
                "updated_at": incident.get("updated_at"),
            }
            for incident in incidents
        ],
    }


def _compact_incident(incident: dict[str, Any]) -> dict[str, Any]:
    started_at = _parse_timestamp(incident.get("started_at") or incident.get("created_at"))
    resolved_at = _parse_timestamp(incident.get("resolved_at"))
    duration_minutes = None
    if started_at and resolved_at:
        duration_minutes = round((resolved_at - started_at).total_seconds() / 60, 1)

    component_names = {
        component.get("name")
        for component in incident.get("components", [])
        if component.get("name")
    }

    updates = []
    raw_updates = list(reversed(incident.get("incident_updates", [])))
    for update in raw_updates:
        affected_components = update.get("affected_components") or []
        for component in affected_components:
            if component.get("name"):
                component_names.add(component["name"])
        updates.append(
            {
                "status": update.get("status"),
                "body": _strip_html(update.get("body", "")),
                "created_at": update.get("created_at"),
                "affected_components": [
                    component.get("name")
                    for component in affected_components
                    if component.get("name")
                ],
            }
        )

    return {
        "id": incident.get("id"),
        "name": incident.get("name"),
        "status": incident.get("status"),
        "impact": incident.get("impact"),
        "started_at": incident.get("started_at") or incident.get("created_at"),
        "resolved_at": incident.get("resolved_at"),
        "duration_minutes": duration_minutes,
        "components": sorted(component_names),
        "shortlink": incident.get("shortlink"),
        "updates": updates,
    }


def search_public_incidents(query: str = "", limit: int = 3) -> list[dict[str, Any]]:
    """Search the 50 most recent incidents from the configured public status page."""
    payload = _fetch_json("incidents.json")
    incidents = payload.get("incidents", [])

    q = query.lower().strip()
    wants_latest = any(term in q for term in ("latest", "most recent"))
    requested_limit = 1 if wants_latest else limit
    requested_limit = max(1, min(requested_limit, 10))

    # Statuspage normally returns incidents newest-first, but sort explicitly so
    # "latest" always means latest by incident start/create timestamp rather
    # than the incident whose text happens to match the most query words.
    def incident_sort_key(incident: dict[str, Any]) -> datetime:
        return (
            _parse_timestamp(incident.get("started_at") or incident.get("created_at"))
            or datetime.min.replace(tzinfo=timezone.utc)
        )

    incidents = sorted(incidents, key=incident_sort_key, reverse=True)

    if wants_latest:
        selected = incidents[:requested_limit]
    else:
        terms = {
            term
            for term in re.findall(r"[a-z0-9][a-z0-9._-]+", q)
            if len(term) > 2 and term not in _GENERIC_TERMS
        }

        scored: list[tuple[int, int, dict[str, Any]]] = []
        for index, incident in enumerate(incidents):
            searchable_parts = [
                incident.get("name", ""),
                incident.get("status", ""),
                incident.get("impact", ""),
            ]
            searchable_parts.extend(
                component.get("name", "")
                for component in incident.get("components", [])
            )
            searchable_parts.extend(
                _strip_html(update.get("body", ""))
                for update in incident.get("incident_updates", [])
            )
            searchable = " ".join(searchable_parts).lower()
            score = sum(1 for term in terms if term in searchable)
            scored.append((score, -index, incident))

        if terms and any(score > 0 for score, _, _ in scored):
            selected = [
                incident
                for score, _, incident in sorted(scored, reverse=True)
                if score > 0
            ][:requested_limit]
        else:
            selected = incidents[:requested_limit]

    source_url = f"{settings.public_status_base_url.rstrip('/')}/incidents.json"
    result = []
    for incident in selected:
        compact = _compact_incident(incident)
        compact["source"] = settings.public_status_name
        compact["source_url"] = source_url
        compact["fetched_at"] = datetime.now(timezone.utc).isoformat()
        result.append(compact)
    return result


def get_public_incident_metrics() -> dict[str, Any]:
    """Compute reproducible metrics from live recent incident history."""
    payload = _fetch_json("incidents.json")
    incidents = payload.get("incidents", [])
    summary = _fetch_json("summary.json")

    impact_counts = Counter(incident.get("impact", "unknown") for incident in incidents)
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)

    durations: list[float] = []
    incidents_last_7_days = 0
    unresolved = 0

    for incident in incidents:
        started_at = _parse_timestamp(incident.get("started_at") or incident.get("created_at"))
        resolved_at = _parse_timestamp(incident.get("resolved_at"))

        if started_at and started_at >= seven_days_ago:
            incidents_last_7_days += 1
        if incident.get("status") not in {"resolved", "postmortem"}:
            unresolved += 1
        if started_at and resolved_at:
            durations.append((resolved_at - started_at).total_seconds() / 60)

    showcase_components = [
        component
        for component in summary.get("components", [])
        if component.get("showcase", True)
    ]
    non_operational = [
        component
        for component in showcase_components
        if component.get("status") != "operational"
    ]

    return {
        "source": settings.public_status_name,
        "source_url": f"{settings.public_status_base_url.rstrip('/')}/incidents.json",
        "fetched_at": now.isoformat(),
        "recent_incident_count": len(incidents),
        "incidents_last_7_days": incidents_last_7_days,
        "unresolved_incident_count": unresolved,
        "minor_incident_count": impact_counts.get("minor", 0),
        "major_incident_count": impact_counts.get("major", 0),
        "critical_incident_count": impact_counts.get("critical", 0),
        "average_resolution_minutes": (
            round(sum(durations) / len(durations), 1) if durations else None
        ),
        "current_component_count": len(showcase_components),
        "current_non_operational_component_count": len(non_operational),
    }


def online_source_health() -> dict[str, Any]:
    summary = get_public_status_summary()
    return {
        "ok": True,
        "source": summary["source"],
        "source_url": summary["source_url"],
        "fetched_at": summary["fetched_at"],
        "description": summary["description"],
    }
