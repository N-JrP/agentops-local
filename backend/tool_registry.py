from typing import Any

from backend.security import validate_tool_input
from backend.tool_models import TOOL_INPUT_MODELS, structured_arguments
from backend.tools.knowledge_tool import search_knowledge
from backend.tools.log_tool import search_logs
from backend.tools.metrics_tool import get_checkout_metrics
from backend.tools.public_status_tool import (
    get_public_incident_metrics,
    get_public_status_summary,
    search_public_incidents,
)
from backend.tools.sql_tool import query_orders_from_text

TOOL_DESCRIPTIONS = {
    "status": "Fetch current live service/component status from a public Statuspage API.",
    "incidents": "Search real recent incidents and official incident updates.",
    "incident_metrics": "Compute metrics from real recent public incident history.",
    "metrics": "Read deterministic local checkout fixture metrics.",
    "sql": "Run safe parameterized read-only local fixture order queries.",
    "logs": "Search deterministic local fixture incident logs.",
    "knowledge": "Retrieve local incident runbook instructions.",
}


def tool_catalog() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "description": TOOL_DESCRIPTIONS[name],
            "mode": "read_only",
            "input_schema": model.model_json_schema(),
        }
        for name, model in TOOL_INPUT_MODELS.items()
    }


TOOL_SCHEMAS = tool_catalog()


def execute_tool(tool_name: str, tool_input: str | dict[str, Any]) -> Any:
    if isinstance(tool_input, dict):
        raw_text = str(tool_input)
        args_dict = tool_input
    else:
        raw_text = tool_input
        normalized_input = validate_tool_input(tool_name, tool_input)
        args_dict = structured_arguments(tool_name, normalized_input)

    validate_tool_input(tool_name, raw_text)
    model = TOOL_INPUT_MODELS.get(tool_name)
    if model is None:
        raise ValueError(f"Unsupported tool: {tool_name}")
    args = model(**args_dict)

    if tool_name == "status":
        return get_public_status_summary()
    if tool_name == "incidents":
        return search_public_incidents(args.query, limit=args.limit)
    if tool_name == "incident_metrics":
        return get_public_incident_metrics()
    if tool_name == "metrics":
        return get_checkout_metrics()
    if tool_name == "sql":
        return query_orders_from_text(args.query)
    if tool_name == "logs":
        return search_logs(args.query)
    if tool_name == "knowledge":
        return search_knowledge(args.query)

    raise ValueError(f"Unsupported tool: {tool_name}")
