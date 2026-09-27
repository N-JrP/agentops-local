# Tracker completion matrix

This file maps the original AgentOps tracker to the final implementation. **Done** means the project artifact/code for the task is present. Machine-specific runtime checks are consolidated in `scripts/finalize.ps1` rather than requiring step-by-step manual work.

| Phase | Workstream | Final implementation |
|---:|---|---|
| 1 | Core project setup | Python package, FastAPI, Ollama, LangGraph, Pydantic, Git-ready structure |
| 2 | Agent state & LangGraph | Shared typed state, routing, loops, IDs, recovery state |
| 3 | Agent tools | Live public tools + safe dynamic SQL + logs/metrics/knowledge fixtures |
| 4 | Structured planning | Pydantic plan, deterministic required-tool policy, LLM JSON inputs, fallback |
| 5 | Multi-tool loop | Minimal execution loop, evidence combination, synthesis |
| 6 | Grounding | numeric/source/identifier grounding, coverage checks, retry, deterministic fallback |
| 7 | Reliability | exception handling, online retries, deterministic failed-tool recovery/replan |
| 8 | Execution trace | ordered tool history, inputs, results, attempts, retry errors, recovery markers |
| 9 | Basic observability | aggregate summary, investigation IDs, model/token/prompt metadata |
| 10 | Observability platform | OpenTelemetry + Jaeger, Prometheus + provisioned Grafana dashboard |
| 11 | Evaluation | offline policy set, regression tests, live-source verification, persisted reports |
| 12 | Tool/function calling | Pydantic JSON input schemas, structured registry, native Ollama comparison |
| 13 | MCP | MCP v2 server/client, discovery, live tools, full investigation trace demo |
| 14 | Persistence | SQLite/PostgreSQL, investigations, tool traces, evaluations, sessions |
| 15 | Safety | read-only policy, input guard, abuse guard, future-write approval branch |
| 16 | FastAPI | structured `/investigate`, live-source endpoints, persistence/session/evaluation APIs |
| 17 | Streamlit | answer, plan, trace, status, evidence, retries, validation, observability views |
| 18 | Docker | backend/UI/PostgreSQL, optional MCP, optional Prometheus/Grafana/Jaeger profiles |
| 19 | Testing | tools, routing, validator, security, SQL, recovery, observability, API, assets |
| 20 | CI/CD | GitHub Actions lint/tests/offline evaluation + backend/UI Docker build checks |
| 21 | Kubernetes | namespace, ConfigMap, Secret, Deployments, Services, probes, kind demo script |
| 22 | Portfolio polish | README, diagrams, screenshots, demos, failure recovery, evaluation, limitations, future work, resume bullets |

## Conditional items resolved deliberately

- **pgvector:** reviewed and intentionally excluded. Current runbook/public-status workflow does not require vector retrieval.
- **Redis:** reviewed and intentionally excluded. There is no measured cache/concurrency need and caching could make live/evaluation behavior less transparent.
- **Write-action approval:** the approval branch is implemented, but no write-capable tool is enabled. This preserves a genuinely read-only portfolio demo.
- **Self-hosted Langfuse:** the tracker allowed “Langfuse or equivalent”; the final project uses the fully local OpenTelemetry + Jaeger path, with Prometheus/Grafana for metrics.
