import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///data/agentops_investigations.db",
    )
    max_answer_attempts: int = int(os.getenv("MAX_ANSWER_ATTEMPTS", "2"))
    tool_max_attempts: int = int(os.getenv("TOOL_MAX_ATTEMPTS", "2"))
    tool_retry_backoff_seconds: float = float(
        os.getenv("TOOL_RETRY_BACKOFF_SECONDS", "0.25")
    )
    otel_exporter_otlp_endpoint: str = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    public_status_base_url: str = os.getenv(
        "PUBLIC_STATUS_BASE_URL",
        "https://www.githubstatus.com/api/v2",
    )
    public_status_name: str = os.getenv("PUBLIC_STATUS_NAME", "GitHub Status API")
    external_http_timeout_seconds: float = float(
        os.getenv("EXTERNAL_HTTP_TIMEOUT_SECONDS", "15")
    )
    max_question_chars: int = int(os.getenv("MAX_QUESTION_CHARS", "1000"))
    max_tool_input_chars: int = int(os.getenv("MAX_TOOL_INPUT_CHARS", "1000"))
    planner_prompt_version: str = os.getenv(
        "PLANNER_PROMPT_VERSION",
        "planner-live-v3",
    )
    answer_prompt_version: str = os.getenv(
        "ANSWER_PROMPT_VERSION",
        "answer-grounded-v3",
    )


settings = Settings()
