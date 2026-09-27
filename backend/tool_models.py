from typing import Any

from pydantic import BaseModel, Field


class StatusArgs(BaseModel):
    context: str = Field(default="", max_length=1000)


class IncidentArgs(BaseModel):
    query: str = Field(default="latest", max_length=1000)
    limit: int = Field(default=3, ge=1, le=10)


class IncidentMetricsArgs(BaseModel):
    context: str = Field(default="", max_length=1000)


class FixtureMetricsArgs(BaseModel):
    context: str = Field(default="", max_length=1000)


class OrderQueryArgs(BaseModel):
    query: str = Field(default="", max_length=1000)


class LogSearchArgs(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


class KnowledgeArgs(BaseModel):
    query: str = Field(min_length=1, max_length=1000)


TOOL_INPUT_MODELS: dict[str, type[BaseModel]] = {
    "status": StatusArgs,
    "incidents": IncidentArgs,
    "incident_metrics": IncidentMetricsArgs,
    "metrics": FixtureMetricsArgs,
    "sql": OrderQueryArgs,
    "logs": LogSearchArgs,
    "knowledge": KnowledgeArgs,
}


def structured_arguments(tool_name: str, tool_input: str) -> dict[str, Any]:
    if tool_name == "incidents":
        return {"query": tool_input or "latest", "limit": 3}
    if tool_name == "sql":
        return {"query": tool_input}
    if tool_name in {"logs", "knowledge"}:
        return {"query": tool_input}
    return {"context": tool_input}
