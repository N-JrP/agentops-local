import time
from typing import Any

from ollama import Client
from opentelemetry import trace

from backend.config import settings

client = Client(host=settings.ollama_host)
tracer = trace.get_tracer("agentops.llm")


def _duration_ms(value: Any) -> float | None:
    if value is None:
        return None
    try:
        # Ollama duration fields are nanoseconds.
        return round(float(value) / 1_000_000.0, 2)
    except (TypeError, ValueError):
        return None


def ask_llm_with_metadata(
    prompt: str,
    *,
    purpose: str,
    prompt_version: str,
    investigation_id: str = "",
) -> dict:
    start = time.perf_counter()

    with tracer.start_as_current_span("ollama.chat") as span:
        span.set_attribute("agentops.llm.purpose", purpose)
        span.set_attribute("agentops.prompt.version", prompt_version)
        span.set_attribute("agentops.model", settings.ollama_model)
        if investigation_id:
            span.set_attribute("agentops.investigation_id", investigation_id)

        response = client.chat(
            model=settings.ollama_model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        prompt_tokens = getattr(response, "prompt_eval_count", None)
        completion_tokens = getattr(response, "eval_count", None)

        if prompt_tokens is not None:
            span.set_attribute("agentops.tokens.prompt", int(prompt_tokens))
        if completion_tokens is not None:
            span.set_attribute("agentops.tokens.completion", int(completion_tokens))
        span.set_attribute("agentops.llm.elapsed_ms", elapsed_ms)

        return {
            "content": response.message.content or "",
            "purpose": purpose,
            "prompt_version": prompt_version,
            "model": settings.ollama_model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": (
                int(prompt_tokens or 0) + int(completion_tokens or 0)
                if prompt_tokens is not None or completion_tokens is not None
                else None
            ),
            "elapsed_ms": elapsed_ms,
            "ollama_total_duration_ms": _duration_ms(
                getattr(response, "total_duration", None)
            ),
            "ollama_load_duration_ms": _duration_ms(
                getattr(response, "load_duration", None)
            ),
        }


def ask_llm(prompt: str) -> str:
    """Compatibility wrapper for simple callers."""
    return ask_llm_with_metadata(
        prompt,
        purpose="generic",
        prompt_version="generic-v1",
    )["content"]
