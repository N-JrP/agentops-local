import os

from mcp.server import MCPServer

from backend.agent.graph import run_investigation
from backend.tool_registry import tool_catalog
from backend.tools.knowledge_tool import search_knowledge
from backend.tools.log_tool import search_logs
from backend.tools.metrics_tool import get_checkout_metrics
from backend.tools.public_status_tool import (
    get_public_incident_metrics,
    get_public_status_summary,
    search_public_incidents,
)
from backend.tools.sql_tool import get_order_stats, query_orders

mcp = MCPServer("AgentOps Local")


@mcp.tool()
def agentops_tool_catalog() -> dict:
    """Return AgentOps tool descriptions and structured JSON input schemas."""
    return tool_catalog()


@mcp.tool()
def live_service_status() -> dict:
    """Fetch live service/component status from the configured public Statuspage."""
    return get_public_status_summary()


@mcp.tool()
def recent_public_incidents(query: str = "latest", limit: int = 3) -> list[dict]:
    """Search real recent public incidents and their updates."""
    return search_public_incidents(query, limit=limit)


@mcp.tool()
def public_incident_metrics() -> dict:
    """Compute metrics from the real recent public incident history."""
    return get_public_incident_metrics()


@mcp.tool()
def checkout_metrics() -> dict:
    """Return local deterministic checkout fixture metrics."""
    return get_checkout_metrics()


@mcp.tool()
def order_stats() -> dict:
    """Return local deterministic total and failed order counts."""
    return get_order_stats()




@mcp.tool()
def query_fixture_orders(
    status: str | None = None,
    order_id: int | None = None,
    limit: int = 50,
) -> dict:
    """Safely query local fixture orders using parameterized read-only filters."""
    return query_orders(status=status, order_id=order_id, limit=limit)


@mcp.tool()
def incident_logs(query: str) -> list[str]:
    """Search local deterministic incident fixture logs."""
    return search_logs(query)


@mcp.tool()
def incident_runbook(query: str) -> str:
    """Retrieve the most relevant local incident runbook section."""
    return search_knowledge(query)


@mcp.tool()
def investigate(question: str) -> dict:
    """Run the complete AgentOps LangGraph investigation workflow."""
    return run_investigation(question)


if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=os.getenv("MCP_HOST", "127.0.0.1"),
            port=int(os.getenv("MCP_PORT", "8001")),
        )
    else:
        mcp.run()
