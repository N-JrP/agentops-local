import json
import re
import time

from opentelemetry import trace

from backend.agent.router_models import InvestigationPlan
from backend.agent.state import AgentState
from backend.config import settings
from backend.llm import ask_llm_with_metadata
from backend.security import validate_user_question
from backend.tool_registry import execute_tool

tracer = trace.get_tracer("agentops.agent")

TOOL_ORDER = (
    "status",
    "incidents",
    "incident_metrics",
    "metrics",
    "sql",
    "logs",
    "knowledge",
)


def security_guard(state: AgentState) -> dict:
    allowed, reason = validate_user_question(state["question"])
    return {
        "security_blocked": not allowed,
        "security_reason": reason,
    }


def security_blocked_answer(state: AgentState) -> dict:
    return {
        "answer": f"Request blocked by AgentOps safety guard: {state['security_reason']}",
        "answer_valid": True,
        "answer_validation_issues": [],
        "answer_attempts": 0,
        "answer_duration_ms": 0.0,
        "requires_human_review": True,
    }


def approval_required(state: AgentState) -> dict:
    return {
        "answer": (
            f"Tool '{state['selected_tool']}' requires explicit human approval before "
            "execution. No action was performed."
        ),
        "answer_valid": True,
        "answer_validation_issues": [],
        "answer_attempts": 0,
        "answer_duration_ms": 0.0,
        "requires_human_review": True,
    }


def _required_tools_from_question(question: str) -> list[str]:
    """Return the minimal tool set implied by the user's explicit request."""
    q = question.lower()
    required: set[str] = set()

    public_context = any(
        term in q
        for term in (
            "github",
            "github status",
            "public status",
            "status page",
            "statuspage",
        )
    )

    if public_context:
        status_intent = any(
            term in q
            for term in (
                "current status",
                "service status",
                "component status",
                "right now",
                "currently",
                "all systems operational",
                "operational now",
                "degraded now",
                "active outage",
                "active incident",
                "unresolved incident",
                "unresolved incidents",
            )
        )

        incident_metrics_intent = any(
            term in q
            for term in (
                "incident metric",
                "incident metrics",
                "incident trend",
                "incident trends",
                "how many incidents",
                "how many major",
                "how many critical",
                "how many minor",
                "number of incidents",
                "count of incidents",
                "major incidents",
                "critical incidents",
                "minor incidents",
                "average resolution",
                "mean resolution",
                "resolution time",
                "last 7 days",
            )
        )

        incident_detail_intent = any(
            term in q
            for term in (
                "latest incident",
                "most recent incident",
                "recent incident",
                "latest outage",
                "recent outage",
                "what happened",
                "root cause",
                "affected",
                "how was it resolved",
                "how it was resolved",
                "resolution details",
                "mitigation",
                "incident update",
                "incident updates",
                "postmortem",
            )
        )

        knowledge_intent = any(
            term in q
            for term in (
                "what should",
                "what to do",
                "how to troubleshoot",
                "how to respond",
                "runbook",
                "procedure",
                "engineer do",
            )
        )

        if status_intent:
            required.add("status")
        if incident_metrics_intent:
            required.add("incident_metrics")
        if incident_detail_intent:
            required.add("incidents")
        if knowledge_intent:
            required.add("knowledge")

        # Generic public incident questions should retrieve incident history,
        # while generic GitHub status questions default to live current status.
        if not required:
            if "incident" in q or "outage" in q:
                required.add("incidents")
            else:
                required.add("status")

        return [tool for tool in TOOL_ORDER if tool in required]

    if any(
        term in q
        for term in (
            "metric",
            "metrics",
            "operational change",
            "operational changes",
            "conversion rate",
            "error rate",
            "latency",
            "performance",
        )
    ):
        required.add("metrics")

    if any(
        term in q
        for term in (
            " log ",
            " logs",
            "log error",
            "log errors",
            "what errors",
            "errors occurred",
            "exception",
            "exceptions",
        )
    ):
        required.add("logs")

    if any(
        term in q
        for term in (
            "total orders",
            "total order count",
            "failed orders",
            "failed order count",
            "orders database",
            "show failed orders",
            "show successful orders",
            "successful orders",
            "order id",
            "order_id",
        )
    ) or re.search(r"\border\s+\d{3,}\b", q):
        required.add("sql")

    if any(
        term in q
        for term in (
            "what should",
            "what to do",
            "how to troubleshoot",
            "how to fix",
            "remediation",
            "runbook",
            "procedure",
            "engineer do",
        )
    ):
        required.add("knowledge")

    if not required and ("investigate" in q or "incident" in q):
        required.update({"metrics", "logs", "knowledge"})

    return [tool for tool in TOOL_ORDER if tool in required]


def plan_investigation(state: AgentState) -> dict:
    question = state["question"]
    required_tools = _required_tools_from_question(question)

    if not required_tools:
        return {
            "plan": [],
            "current_step": 0,
            "planner_duration_ms": 0.0,
            "planner_attempts": 0,
        }

    prompt = f"""
You are the planner for an AI incident investigation agent.

Available tools:
- status: current live service/component status from a public Statuspage API
- incidents: real recent public incidents, affected components, and incident updates
- incident_metrics: metrics derived from real recent public incident history
- metrics: local checkout fixture metrics for deterministic regression tests
- sql: safe parameterized local fixture order queries, including counts, status filters, and IDs
- logs: local fixture technical error logs
- knowledge: local runbooks and troubleshooting instructions

User question:
{question}

The deterministic policy layer has already identified these required tools:
{required_tools}

Create one step for each required tool and no others.
Select each tool exactly once.
Use a short, useful tool_input that preserves the user's service/incident/context terms.
Never add background tools that are not listed above.

Return ONLY valid JSON:
{{"steps": [{{"tool": "incidents", "tool_input": "latest GitHub incident"}}]}}

The JSON above is only a format example.
Do not include markdown or explanations.
"""

    generated_inputs: dict[str, str] = {}
    planner_start_time = time.perf_counter()
    planner_attempts = 0
    llm_history = list(state.get("llm_history", []))

    with tracer.start_as_current_span("agentops.plan") as span:
        span.set_attribute("agentops.investigation_id", state["investigation_id"])
        span.set_attribute("agentops.prompt.version", settings.planner_prompt_version)
        span.set_attribute("agentops.required_tools", ",".join(required_tools))

        for attempt in range(2):
            planner_attempts = attempt + 1
            llm_result = ask_llm_with_metadata(
                prompt,
                purpose="planner",
                prompt_version=settings.planner_prompt_version,
                investigation_id=state["investigation_id"],
            )
            planner_response = llm_result["content"].strip()
            llm_history.append(
                {key: value for key, value in llm_result.items() if key != "content"}
            )

            if planner_response.startswith("```json"):
                planner_response = planner_response[len("```json") :].strip()
            elif planner_response.startswith("```"):
                planner_response = planner_response[len("```") :].strip()
            if planner_response.endswith("```"):
                planner_response = planner_response[:-3].strip()

            try:
                planner_data = json.loads(planner_response)
                investigation_plan = InvestigationPlan(**planner_data)
                generated_inputs = {
                    step.tool: step.tool_input
                    for step in investigation_plan.steps
                    if step.tool in required_tools
                }
                break
            except Exception as error:
                span.add_event(
                    "planner_parse_error",
                    {"attempt": planner_attempts, "error": str(error)[:300]},
                )
                continue

    plan = [
        {
            "tool": tool,
            "tool_input": generated_inputs.get(tool, question),
        }
        for tool in required_tools
    ]

    planner_duration_ms = round(
        (time.perf_counter() - planner_start_time) * 1000,
        2,
    )

    return {
        "plan": plan,
        "current_step": 0,
        "planner_duration_ms": planner_duration_ms,
        "planner_attempts": planner_attempts,
        "llm_history": llm_history,
    }


def prepare_current_step(state: AgentState) -> dict:
    index = state["current_step"]
    if index >= len(state["plan"]):
        return {
            "selected_tool": "unsupported",
            "tool_input": state["question"],
        }

    step = state["plan"][index]
    return {
        "selected_tool": step["tool"],
        "tool_input": step["tool_input"],
    }


def advance_step(state: AgentState) -> dict:
    return {"current_step": state["current_step"] + 1}


def _empty_value_for_result(result_key: str):
    if result_key in {"log_result", "incident_result"}:
        return []
    if result_key == "knowledge_result":
        return ""
    return {}


def _run_tool(state: AgentState, tool_name: str, result_key: str) -> dict:
    start = time.perf_counter()
    history = list(state["tool_history"])
    query = state["tool_input"]
    if tool_name in {"logs", "incidents"}:
        query = f"{state['question']} {state['tool_input']}"

    max_attempts = settings.tool_max_attempts if tool_name in {
        "status",
        "incidents",
        "incident_metrics",
    } else 1
    retry_errors: list[str] = []

    with tracer.start_as_current_span(f"agentops.tool.{tool_name}") as span:
        span.set_attribute("agentops.investigation_id", state["investigation_id"])
        span.set_attribute("agentops.tool.name", tool_name)

        for attempt in range(1, max_attempts + 1):
            try:
                result = execute_tool(tool_name, query)
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                span.set_attribute("agentops.tool.status", "success")
                span.set_attribute("agentops.tool.attempts", attempt)
                history.append(
                    {
                        "tool": tool_name,
                        "tool_input": state["tool_input"],
                        "status": "success",
                        "duration_ms": duration_ms,
                        "attempts": attempt,
                        "retry_errors": retry_errors,
                        "result": result,
                    }
                )
                return {result_key: result, "tool_history": history}
            except Exception as error:
                retry_errors.append(str(error))
                span.add_event(
                    "tool_attempt_error",
                    {"attempt": attempt, "error": str(error)[:300]},
                )
                if attempt < max_attempts:
                    time.sleep(settings.tool_retry_backoff_seconds * attempt)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        span.set_attribute("agentops.tool.status", "error")
        span.set_attribute("agentops.tool.attempts", max_attempts)
        history.append(
            {
                "tool": tool_name,
                "tool_input": state["tool_input"],
                "status": "error",
                "duration_ms": duration_ms,
                "attempts": max_attempts,
                "retry_errors": retry_errors,
                "result": None,
                "error": retry_errors[-1] if retry_errors else "Unknown tool error",
            }
        )
        return {
            result_key: _empty_value_for_result(result_key),
            "tool_history": history,
        }


def get_public_status(state: AgentState) -> dict:
    return _run_tool(state, "status", "status_result")


def get_public_incidents(state: AgentState) -> dict:
    return _run_tool(state, "incidents", "incident_result")


def get_incident_metrics(state: AgentState) -> dict:
    return _run_tool(state, "incident_metrics", "incident_metrics")


def get_metrics(state: AgentState) -> dict:
    return _run_tool(state, "metrics", "metrics")


def get_sql_data(state: AgentState) -> dict:
    return _run_tool(state, "sql", "sql_result")


def get_log_data(state: AgentState) -> dict:
    return _run_tool(state, "logs", "log_result")


def get_knowledge_data(state: AgentState) -> dict:
    return _run_tool(state, "knowledge", "knowledge_result")


def recover_failed_tools(state: AgentState) -> dict:
    """One deterministic recovery/replan pass for tools that still failed after retries."""
    if state.get("recovery_attempted"):
        return {}

    latest_by_tool: dict[str, dict] = {}
    for item in state.get("tool_history", []):
        latest_by_tool[item.get("tool", "unknown")] = item

    failed_tools = [
        step["tool"]
        for step in state.get("plan", [])
        if latest_by_tool.get(step["tool"], {}).get("status") == "error"
    ]
    if not failed_tools:
        return {"recovery_attempted": False, "recovery_actions": []}

    result_key_by_tool = {
        "status": "status_result",
        "incidents": "incident_result",
        "incident_metrics": "incident_metrics",
        "metrics": "metrics",
        "sql": "sql_result",
        "logs": "log_result",
        "knowledge": "knowledge_result",
    }
    update: dict = {
        "recovery_attempted": True,
        "recovery_actions": [],
        "tool_history": list(state.get("tool_history", [])),
    }

    with tracer.start_as_current_span("agentops.recovery") as span:
        span.set_attribute("agentops.investigation_id", state["investigation_id"])
        span.set_attribute("agentops.failed_tools", ",".join(failed_tools))

        for tool_name in failed_tools:
            step = next(step for step in state["plan"] if step["tool"] == tool_name)
            query = step["tool_input"]
            if tool_name in {"logs", "incidents"}:
                query = f"{state['question']} {query}"

            action = {"tool": tool_name, "status": "error"}
            start = time.perf_counter()
            try:
                result = execute_tool(tool_name, query)
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                update[result_key_by_tool[tool_name]] = result
                update["tool_history"].append(
                    {
                        "tool": tool_name,
                        "tool_input": step["tool_input"],
                        "status": "success",
                        "duration_ms": duration_ms,
                        "attempts": 1,
                        "recovery": True,
                        "result": result,
                    }
                )
                action = {"tool": tool_name, "status": "recovered"}
            except Exception as error:
                duration_ms = round((time.perf_counter() - start) * 1000, 2)
                update["tool_history"].append(
                    {
                        "tool": tool_name,
                        "tool_input": step["tool_input"],
                        "status": "error",
                        "duration_ms": duration_ms,
                        "attempts": 1,
                        "recovery": True,
                        "result": None,
                        "error": str(error),
                    }
                )
                action = {
                    "tool": tool_name,
                    "status": "failed",
                    "error": str(error),
                }
            update["recovery_actions"].append(action)

    return update


def validate_answer(answer: str, evidence: dict) -> tuple[bool, list[str]]:
    """Validate answer grounding with deterministic claim-level safety checks."""
    issues: list[str] = []
    evidence_text = str(evidence)

    if "%" in answer and "%" not in evidence_text:
        issues.append(
            "Answer contains a % symbol that is not present in the evidence."
        )

    evidence_identifiers: set[str] = set()
    for line in evidence.get("logs", []):
        evidence_identifiers.update(
            re.findall(r"(?:order_id|provider)=[A-Za-z0-9_-]+", line)
        )

    answer_identifiers = set(
        re.findall(r"(?:order_id|provider)=[A-Za-z0-9_-]+", answer)
    )
    for identifier in sorted(answer_identifiers - evidence_identifiers):
        issues.append(f"Unsupported identifier in answer: {identifier}")

    incident_ids = {
        incident.get("id")
        for incident in evidence.get("incidents", [])
        if incident.get("id")
    }
    answer_incident_ids = set(re.findall(r"incident_id=([A-Za-z0-9_-]+)", answer))
    for incident_id in sorted(answer_incident_ids - incident_ids):
        issues.append(f"Unsupported incident ID in answer: {incident_id}")

    # Broader numeric hallucination check. Markdown list ordinals are stripped first so
    # an answer can use 1., 2., 3. without those being treated as factual claims.
    answer_without_ordinals = re.sub(r"(?m)^\s*\d+[.)]\s+", "", answer)
    answer_numbers = set(
        re.findall(r"(?<![A-Za-z])\b\d+(?:\.\d+)?\b", answer_without_ordinals)
    )
    evidence_numbers = set(
        re.findall(r"(?<![A-Za-z])\b\d+(?:\.\d+)?\b", evidence_text)
    )
    for number in sorted(answer_numbers - evidence_numbers):
        issues.append(f"Unsupported numeric claim in answer: {number}")

    # Source URLs are part of evidence provenance; do not allow an invented source link.
    answer_urls = {
        url.rstrip(".,;]")
        for url in re.findall(r"https?://[^\s)]+", answer)
    }
    evidence_urls = {
        url.rstrip(".,;]")
        for url in re.findall(r"https?://[^\s)']+", evidence_text)
    }
    for url in sorted(answer_urls - evidence_urls):
        issues.append(f"Unsupported source URL in answer: {url}")

    return len(issues) == 0, issues


def _coverage_issues(state: AgentState, answer: str, evidence: dict) -> list[str]:
    """Check that the final answer covers the important retrieved evidence."""
    issues: list[str] = []
    answer_lower = answer.lower()
    planned_tools = {step["tool"] for step in state["plan"]}

    if "status" in planned_tools:
        description = evidence.get("status", {}).get("description")
        if description and description.lower() not in answer_lower:
            issues.append(f"Missing current status description: {description}")

    if "incidents" in planned_tools:
        for incident in evidence.get("incidents", []):
            name = incident.get("name")
            if name and name.lower() not in answer_lower:
                issues.append(f"Missing public incident: {name}")

    if "incident_metrics" in planned_tools:
        metrics = evidence.get("incident_metrics", {})
        for key in (
            "recent_incident_count",
            "incidents_last_7_days",
            "major_incident_count",
            "critical_incident_count",
            "average_resolution_minutes",
        ):
            value = metrics.get(key)
            if value is not None and str(value) not in answer:
                issues.append(f"Missing incident metric {key}: {value}")

    if "metrics" in planned_tools:
        for value in evidence.get("metrics", {}).values():
            if str(value) not in answer:
                issues.append(f"Missing metric value: {value}")

    if "logs" in planned_tools:
        log_text = "\n".join(evidence.get("logs", []))
        error_names = set(re.findall(r"ERROR\s+([A-Za-z0-9_-]+)", log_text))
        order_ids = set(re.findall(r"order_id=([A-Za-z0-9_-]+)", log_text))

        for error_name in sorted(error_names):
            if error_name.lower() not in answer_lower:
                issues.append(f"Missing log error type: {error_name}")
        for order_id in sorted(order_ids):
            if order_id.lower() not in answer_lower:
                issues.append(f"Missing affected order ID: {order_id}")

    if "sql" in planned_tools:
        q = state["question"].lower()
        sql_result = evidence.get("sql", {})
        if "total" in q and "total_orders" in sql_result:
            if str(sql_result["total_orders"]) not in answer:
                issues.append("Missing total order count")
        if "failed" in q and "failed_orders" in sql_result:
            if str(sql_result["failed_orders"]) not in answer:
                issues.append("Missing failed order count")
        for row in sql_result.get("orders", []):
            if str(row.get("id")) not in answer:
                issues.append(f"Missing order ID: {row.get('id')}")

    if "knowledge" in planned_tools:
        knowledge = evidence.get("knowledge", "")
        actions = re.findall(r"^\d+\.\s+(.+)$", knowledge, flags=re.MULTILINE)
        for action in actions[:2]:
            if action.rstrip(".").lower() not in answer_lower:
                issues.append(f"Missing runbook action: {action}")

    return issues


def _deterministic_grounded_answer(state: AgentState, evidence: dict) -> str:
    """Safe fallback used when LLM synthesis remains invalid/incomplete."""
    sections: list[str] = []
    planned_tools = {step["tool"] for step in state["plan"]}

    if "status" in planned_tools and evidence.get("status"):
        status = evidence["status"]
        lines = [
            f"Live source: {status.get('source')}",
            f"Source URL: {status.get('source_url')}",
            f"Current status: {status.get('description')} ({status.get('indicator')})",
        ]
        if status.get("non_operational_components"):
            lines.append("Non-operational components:")
            lines.extend(
                f"- {item.get('name')}: {item.get('status')}"
                for item in status["non_operational_components"]
            )
        sections.append("\n".join(lines))

    if "incidents" in planned_tools and evidence.get("incidents"):
        lines = ["Recent public incidents:"]
        for incident in evidence["incidents"]:
            lines.append(
                f"- {incident.get('name')} | status={incident.get('status')} | "
                f"impact={incident.get('impact')}"
            )
            if incident.get("components"):
                lines.append(f"  Components: {', '.join(incident['components'])}")
            for update in incident.get("updates", []):
                lines.append(
                    f"  {update.get('created_at')} [{update.get('status')}]: "
                    f"{update.get('body')}"
                )
            lines.append(f"  Source: {incident.get('source_url')}")
        sections.append("\n".join(lines))

    if "incident_metrics" in planned_tools and evidence.get("incident_metrics"):
        metrics = evidence["incident_metrics"]
        lines = [
            f"Live incident metrics from {metrics.get('source')}:",
            f"Source URL: {metrics.get('source_url')}",
        ]
        lines.extend(
            f"- {key}: {value}"
            for key, value in metrics.items()
            if key not in {"source", "source_url", "fetched_at"}
        )
        sections.append("\n".join(lines))

    if "logs" in planned_tools and evidence.get("logs"):
        lines = ["Local fixture errors / log evidence:"]
        lines.extend(f"- {line}" for line in evidence["logs"])
        sections.append("\n".join(lines))

    if "metrics" in planned_tools and evidence.get("metrics"):
        lines = ["Local fixture operational metrics:"]
        lines.extend(
            f"- {key}: {value}" for key, value in evidence["metrics"].items()
        )
        sections.append("\n".join(lines))

    if "sql" in planned_tools and evidence.get("sql"):
        lines = ["Local fixture database facts:"]
        lines.extend(f"- {key}: {value}" for key, value in evidence["sql"].items())
        sections.append("\n".join(lines))

    if "knowledge" in planned_tools and evidence.get("knowledge"):
        sections.append(f"Runbook guidance:\n{evidence['knowledge'].strip()}")

    if not sections:
        return "I could not find enough evidence to answer this question reliably."

    return "\n\n".join(sections)


def _truncate_prompt_text(value: str, max_chars: int = 2400) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + " ... [truncated for local LLM prompt]"


def _prompt_evidence(evidence: dict) -> dict:
    """Create a smaller LLM prompt view while retaining full evidence in state."""
    compact = dict(evidence)
    compact_incidents = []

    for incident in evidence.get("incidents", []):
        updates = incident.get("updates", [])
        if len(updates) <= 4:
            selected_updates = updates
        else:
            selected_updates = updates[:2] + updates[-2:]

        compact_updates = []
        seen = set()
        for update in selected_updates:
            key = (update.get("created_at"), update.get("status"), update.get("body"))
            if key in seen:
                continue
            seen.add(key)
            compact_updates.append(
                {
                    "status": update.get("status"),
                    "body": _truncate_prompt_text(update.get("body", "")),
                    "created_at": update.get("created_at"),
                    "affected_components": update.get("affected_components", []),
                }
            )

        compact_incidents.append(
            {
                "id": incident.get("id"),
                "name": incident.get("name"),
                "status": incident.get("status"),
                "impact": incident.get("impact"),
                "started_at": incident.get("started_at"),
                "resolved_at": incident.get("resolved_at"),
                "duration_minutes": incident.get("duration_minutes"),
                "components": incident.get("components", []),
                "shortlink": incident.get("shortlink"),
                "updates": compact_updates,
                "source": incident.get("source"),
                "source_url": incident.get("source_url"),
                "fetched_at": incident.get("fetched_at"),
            }
        )

    compact["incidents"] = compact_incidents
    return compact


def generate_investigation_answer(state: AgentState) -> dict:
    evidence = {
        "status": state["status_result"],
        "incidents": state["incident_result"],
        "incident_metrics": state["incident_metrics"],
        "metrics": state["metrics"],
        "sql": state["sql_result"],
        "logs": state["log_result"],
        "knowledge": state["knowledge_result"],
    }
    prompt_evidence = _prompt_evidence(evidence)

    if not any(bool(value) for value in evidence.values()):
        answer = "I could not find enough evidence to answer this question reliably."
        return {
            "answer": answer,
            "answer_duration_ms": 0.0,
            "answer_attempts": 0,
            "answer_valid": True,
            "answer_validation_issues": [],
            "requires_human_review": True,
            "llm_history": list(state.get("llm_history", [])),
        }

    answer_start_time = time.perf_counter()
    answer = ""
    validation_issues: list[str] = []
    answer_attempts = 0
    llm_history = list(state.get("llm_history", []))

    for attempt in range(settings.max_answer_attempts):
        answer_attempts = attempt + 1
        validation_feedback = ""
        if validation_issues:
            validation_feedback = f"""
The previous answer failed deterministic checks:
{validation_issues}
Correct every listed problem in the new answer.
"""

        prompt = f"""
You are analyzing an operational incident.

User question:
{state['question']}

Collected evidence (compact prompt view; full evidence remains in agent state):
{prompt_evidence}

Rules:
- Use only facts explicitly present in the collected evidence.
- Treat status/incidents/incident_metrics as live public online evidence.
- When public evidence is used, name the source and include its source URL.
- Do not infer root causes unless evidence explicitly establishes them.
- Do not add recommendations absent from knowledge evidence or incident updates.
- Do not invent comparisons, time windows, thresholds, units, or symbols.
- Never add a percent sign unless a percent sign exists in the evidence.
- When public incidents are requested, report each retrieved incident name.
- When local metrics are requested, report every retrieved metric value.
- When local logs are requested, report every retrieved error type and affected order ID.
- Preserve canonical identifiers exactly when you choose canonical syntax.
- If a requested fact is not established, say that it is not established.
- Keep the answer concise and factual.

{validation_feedback}

Answer:
"""
        llm_result = ask_llm_with_metadata(
            prompt,
            purpose="answer",
            prompt_version=settings.answer_prompt_version,
            investigation_id=state["investigation_id"],
        )
        answer = llm_result["content"].strip()
        llm_history.append(
            {key: value for key, value in llm_result.items() if key != "content"}
        )
        grounding_valid, grounding_issues = validate_answer(answer, evidence)
        coverage_issues = _coverage_issues(state, answer, evidence)
        validation_issues = grounding_issues + coverage_issues

        if grounding_valid and not coverage_issues:
            break

    if validation_issues:
        answer = _deterministic_grounded_answer(state, evidence)
        grounding_valid, grounding_issues = validate_answer(answer, evidence)
        coverage_issues = _coverage_issues(state, answer, evidence)
        validation_issues = grounding_issues + coverage_issues
    else:
        grounding_valid = True

    answer_duration_ms = round(
        (time.perf_counter() - answer_start_time) * 1000,
        2,
    )

    latest_tool_status: dict[str, str] = {}
    for item in state.get("tool_history", []):
        latest_tool_status[item.get("tool", "unknown")] = item.get("status", "unknown")
    tool_failed = any(status == "error" for status in latest_tool_status.values())
    answer_valid = grounding_valid and not validation_issues

    return {
        "answer": answer,
        "answer_duration_ms": answer_duration_ms,
        "answer_attempts": answer_attempts,
        "answer_valid": answer_valid,
        "answer_validation_issues": validation_issues,
        "requires_human_review": tool_failed or not answer_valid,
        "llm_history": llm_history,
    }


def unsupported_tool(state: AgentState) -> dict:
    return {
        "answer": (
            "This question is outside the capabilities of the currently available "
            "AgentOps tools."
        ),
        "answer_valid": True,
        "answer_validation_issues": [],
        "answer_attempts": 0,
        "answer_duration_ms": 0.0,
        "requires_human_review": False,
    }
