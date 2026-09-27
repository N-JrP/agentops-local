import re
from typing import Literal

from backend.config import settings

ToolMode = Literal["read_only", "write"]

TOOL_POLICIES: dict[str, ToolMode] = {
    "status": "read_only",
    "incidents": "read_only",
    "incident_metrics": "read_only",
    "metrics": "read_only",
    "sql": "read_only",
    "logs": "read_only",
    "knowledge": "read_only",
}

# These patterns are intentionally narrow. They block attempts to manipulate the
# agent/tool layer rather than ordinary incident language.
ABUSE_PATTERNS = (
    # Covers common prompt-injection forms such as:
    # "ignore previous instructions", "ignore system instructions", and
    # "ignore previous system instructions".
    r"ignore\s+(?:all\s+)?(?:previous\s+)?(?:system\s+)?instructions",
    r"reveal\s+(?:the\s+)?system\s+prompt",
    r"show\s+(?:me\s+)?(?:the\s+)?hidden\s+prompt",
    r"execute\s+(?:a\s+)?shell\s+command",
    r"delete\s+(?:the\s+)?database",
    r"drop\s+table",
    r"bypass\s+(?:the\s+)?tool\s+(?:policy|permissions?)",
)


def tool_is_allowed(tool_name: str) -> bool:
    return tool_name in TOOL_POLICIES


def requires_approval(tool_name: str) -> bool:
    return TOOL_POLICIES.get(tool_name) == "write"


def validate_user_question(question: str) -> tuple[bool, str]:
    normalized = question.strip()
    if not normalized:
        return False, "Question cannot be empty."
    if len(normalized) > settings.max_question_chars:
        return False, (
            f"Question exceeds the {settings.max_question_chars}-character safety limit."
        )
    if "\x00" in normalized:
        return False, "Question contains a null byte."

    lowered = normalized.lower()
    for pattern in ABUSE_PATTERNS:
        if re.search(pattern, lowered):
            return False, "Question contains an instruction that attempts to bypass agent safety."
    return True, ""


def validate_tool_input(tool_name: str, tool_input: str) -> str:
    if not tool_is_allowed(tool_name):
        raise PermissionError(f"Tool is not allowed: {tool_name}")

    normalized = (tool_input or "").strip()
    if len(normalized) > settings.max_tool_input_chars:
        raise ValueError(
            f"Tool input exceeds {settings.max_tool_input_chars} characters: {tool_name}"
        )
    if "\x00" in normalized:
        raise ValueError(f"Tool input contains a null byte: {tool_name}")
    return normalized


def approval_granted(tool_name: str, approved_tools: list[str]) -> bool:
    if not requires_approval(tool_name):
        return True
    return tool_name in approved_tools
