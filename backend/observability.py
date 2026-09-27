from statistics import mean
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram

from backend.config import settings

INVESTIGATIONS = Counter(
    "agentops_investigations_total",
    "Total investigations",
    ["answer_valid", "human_review"],
)
INVESTIGATION_LATENCY = Histogram(
    "agentops_investigation_duration_seconds",
    "Total investigation latency",
)
PLANNER_LATENCY = Histogram(
    "agentops_planner_duration_seconds",
    "Planner latency",
)
ANSWER_LATENCY = Histogram(
    "agentops_answer_duration_seconds",
    "Answer generation latency",
)
TOOL_LATENCY = Histogram(
    "agentops_tool_duration_seconds",
    "Tool latency",
    ["tool", "status"],
)
TOOL_EXECUTIONS = Counter(
    "agentops_tool_executions_total",
    "Tool executions including retries",
    ["tool", "status"],
)
ANSWER_CHECKS = Counter(
    "agentops_answer_validation_total",
    "Answer validation outcomes",
    ["valid"],
)
LLM_CALL_LATENCY = Histogram(
    "agentops_llm_call_duration_seconds",
    "Local LLM call latency",
    ["purpose", "model"],
)
LLM_TOKENS = Counter(
    "agentops_llm_tokens_total",
    "Local LLM tokens where reported by Ollama",
    ["purpose", "model", "kind"],
)

_tracing_initialized = False


def init_tracing() -> None:
    global _tracing_initialized
    if _tracing_initialized:
        return

    endpoint = settings.otel_exporter_otlp_endpoint.strip()
    if not endpoint:
        _tracing_initialized = True
        return

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )

    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": "agentops-local",
                "service.version": "2.0.0",
            }
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(provider)
    _tracing_initialized = True


def build_observability_summary(result: dict[str, Any]) -> dict[str, Any]:
    tool_history = result.get("tool_history", [])
    llm_history = result.get("llm_history", [])
    tool_latencies = [float(item.get("duration_ms", 0.0)) for item in tool_history]
    tool_errors = [item for item in tool_history if item.get("status") == "error"]

    prompt_tokens = sum(int(item.get("prompt_tokens") or 0) for item in llm_history)
    completion_tokens = sum(
        int(item.get("completion_tokens") or 0) for item in llm_history
    )

    return {
        "investigation_id": result.get("investigation_id"),
        "planner_duration_ms": float(result.get("planner_duration_ms", 0.0)),
        "answer_duration_ms": float(result.get("answer_duration_ms", 0.0)),
        "investigation_duration_ms": float(
            result.get("investigation_duration_ms", 0.0)
        ),
        "tool_execution_count": len(tool_history),
        "tool_error_count": len(tool_errors),
        "tool_retry_count": sum(
            max(int(item.get("attempts", 1)) - 1, 0) for item in tool_history
        ),
        "average_tool_duration_ms": round(mean(tool_latencies), 2)
        if tool_latencies
        else 0.0,
        "max_tool_duration_ms": round(max(tool_latencies), 2)
        if tool_latencies
        else 0.0,
        "llm_call_count": len(llm_history),
        "llm_prompt_tokens": prompt_tokens,
        "llm_completion_tokens": completion_tokens,
        "llm_total_tokens": prompt_tokens + completion_tokens,
        "models": sorted({item.get("model") for item in llm_history if item.get("model")}),
        "prompt_versions": sorted(
            {
                item.get("prompt_version")
                for item in llm_history
                if item.get("prompt_version")
            }
        ),
        "answer_valid": bool(result.get("answer_valid")),
        "requires_human_review": bool(result.get("requires_human_review")),
        "recovery_attempted": bool(result.get("recovery_attempted")),
    }


def record_investigation_metrics(result: dict) -> None:
    INVESTIGATIONS.labels(
        answer_valid=str(bool(result.get("answer_valid"))).lower(),
        human_review=str(bool(result.get("requires_human_review"))).lower(),
    ).inc()

    INVESTIGATION_LATENCY.observe(
        float(result.get("investigation_duration_ms", 0.0)) / 1000.0
    )
    PLANNER_LATENCY.observe(float(result.get("planner_duration_ms", 0.0)) / 1000.0)
    ANSWER_LATENCY.observe(float(result.get("answer_duration_ms", 0.0)) / 1000.0)

    for item in result.get("tool_history", []):
        tool = item.get("tool", "unknown")
        status = item.get("status", "unknown")
        TOOL_LATENCY.labels(tool=tool, status=status).observe(
            float(item.get("duration_ms", 0.0)) / 1000.0
        )
        TOOL_EXECUTIONS.labels(tool=tool, status=status).inc()

    ANSWER_CHECKS.labels(valid=str(bool(result.get("answer_valid"))).lower()).inc()

    for item in result.get("llm_history", []):
        purpose = item.get("purpose", "unknown")
        model = item.get("model", "unknown")
        LLM_CALL_LATENCY.labels(purpose=purpose, model=model).observe(
            float(item.get("elapsed_ms", 0.0)) / 1000.0
        )
        prompt_tokens = int(item.get("prompt_tokens") or 0)
        completion_tokens = int(item.get("completion_tokens") or 0)
        if prompt_tokens:
            LLM_TOKENS.labels(purpose=purpose, model=model, kind="prompt").inc(
                prompt_tokens
            )
        if completion_tokens:
            LLM_TOKENS.labels(purpose=purpose, model=model, kind="completion").inc(
                completion_tokens
            )
