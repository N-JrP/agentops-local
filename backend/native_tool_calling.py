"""Optional comparison path: Ollama-native function/tool calling.

The LangGraph planner remains the primary AgentOps architecture because it gives
explicit planning state and deterministic orchestration. This module exists to
show a native tool-calling alternative using a tool-capable local Ollama model.
"""

import os

from ollama import Client

from backend.config import settings
from backend.tools.knowledge_tool import search_knowledge
from backend.tools.log_tool import search_logs
from backend.tools.metrics_tool import get_checkout_metrics
from backend.tools.public_status_tool import (
    get_public_incident_metrics,
    get_public_status_summary,
    search_public_incidents,
)
from backend.tools.sql_tool import get_order_stats


def live_service_status(query: str = "") -> dict:
    """Fetch live public service status.

    Args:
        query: Optional current-status context.

    Returns:
        Live status summary from the configured public Statuspage API.
    """
    del query
    return get_public_status_summary()


def recent_public_incidents(query: str = "latest") -> list[dict]:
    """Search real recent public incidents.

    Args:
        query: Incident name, component, outage, or recent-incident context.

    Returns:
        Matching public incidents and incident updates.
    """
    return search_public_incidents(query)


def public_incident_metrics(query: str = "") -> dict:
    """Compute metrics from real recent public incident history.

    Args:
        query: Optional incident-metrics context.

    Returns:
        Counts, impact totals, current component state, and resolution metrics.
    """
    del query
    return get_public_incident_metrics()


def checkout_metrics(query: str = "") -> dict:
    """Read local deterministic checkout fixture metrics.

    Args:
        query: Optional description of the requested metrics.

    Returns:
        Current and previous-day fixture checkout metrics.
    """
    del query
    return get_checkout_metrics()


def order_stats(query: str = "") -> dict:
    """Read local deterministic total and failed order counts.

    Args:
        query: Optional description of the requested order-count fact.

    Returns:
        Total and failed fixture order counts.
    """
    del query
    return get_order_stats()


def incident_logs(query: str) -> list[str]:
    """Search local deterministic incident fixture logs.

    Args:
        query: Error name or incident-search text.

    Returns:
        Matching fixture log lines.
    """
    return search_logs(query)


def incident_runbook(query: str) -> str:
    """Retrieve a local incident runbook section.

    Args:
        query: Incident or troubleshooting text.

    Returns:
        The most relevant runbook section.
    """
    return search_knowledge(query)


TOOLS = [
    live_service_status,
    recent_public_incidents,
    public_incident_metrics,
    checkout_metrics,
    order_stats,
    incident_logs,
    incident_runbook,
]
TOOL_MAP = {tool.__name__: tool for tool in TOOLS}


def run_native_tool_calling(question: str) -> str:
    client = Client(host=settings.ollama_host)
    model = os.getenv("NATIVE_TOOL_MODEL", "llama3.1:8b")
    messages = [{"role": "user", "content": question}]

    for _ in range(4):
        response = client.chat(
            model=model,
            messages=messages,
            tools=TOOLS,
            options={"temperature": 0},
        )
        messages.append(response.message)

        calls = response.message.tool_calls or []
        if not calls:
            return response.message.content or ""

        for call in calls:
            function = TOOL_MAP.get(call.function.name)
            if function is None:
                output = f"Unknown tool: {call.function.name}"
            else:
                output = function(**dict(call.function.arguments))

            messages.append(
                {
                    "role": "tool",
                    "tool_name": call.function.name,
                    "content": str(output),
                }
            )

    return "Native tool-calling loop stopped after the safety iteration limit."


if __name__ == "__main__":
    print(
        run_native_tool_calling(
            "Investigate the latest GitHub incident. What happened and how was it resolved?"
        )
    )
