from typing import Literal

from pydantic import BaseModel

ToolName = Literal[
    "status",
    "incidents",
    "incident_metrics",
    "metrics",
    "sql",
    "logs",
    "knowledge",
]


class RouterDecision(BaseModel):
    tool: ToolName
    tool_input: str


class ToolStep(BaseModel):
    tool: ToolName
    tool_input: str


class InvestigationPlan(BaseModel):
    steps: list[ToolStep]
