# Observability

AgentOps exposes observability at three levels:

- **Application state:** planner/answer latency, attempts, per-tool duration/status, retries, recovery actions, validation issues, investigation ID, and LLM metadata.
- **Prometheus:** investigation counts/latency, tool execution/error counts, tool latency, answer validation outcomes, LLM latency, and token counts when Ollama reports them.
- **OpenTelemetry:** FastAPI requests plus custom investigation, planner, LLM, tool, and recovery spans. The Docker observability profile exports to local Jaeger.

Grafana is automatically provisioned with `AgentOps Local Overview` using the bundled Prometheus datasource and dashboard JSON.

Prompt versions are recorded with every LLM call through `PLANNER_PROMPT_VERSION` and `ANSWER_PROMPT_VERSION`.


## Docker Compose tracing

The normal Docker profile keeps OTLP export disabled so the backend does not depend on Jaeger.
To enable the observability profile and trace export together in PowerShell:

```powershell
$env:OTEL_EXPORTER_OTLP_ENDPOINT="http://jaeger:4317"
docker compose --profile observability up --build
```

Prometheus/Grafana remain available through the same profile, while Jaeger receives OTLP spans.
