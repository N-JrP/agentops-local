# Architecture

```mermaid
flowchart LR
    U[User] --> UI[Streamlit]
    U --> API[FastAPI]
    UI --> API
    API --> G[LangGraph]
    G --> SG[Security guard]
    SG --> P[Deterministic policy + LLM planner]
    P --> T{Read-only tools}
    T --> ST[GitHub live status]
    T --> IN[GitHub incidents]
    T --> IM[Incident metrics]
    T --> SQL[Parameterized SQLite/Postgres fixture query]
    T --> LOG[Fixture logs]
    T --> KB[Runbook]
    ST --> GH[GitHub Status API]
    IN --> GH
    IM --> GH
    T --> E[Evidence state]
    E --> S[Grounded synthesis]
    S --> V[Grounding + completeness validation]
    V -->|retry| S
    V -->|fallback| DF[Deterministic evidence answer]
    V --> R[Result]
    DF --> R
    R --> DB[(SQLite / PostgreSQL)]
    R --> OT[OpenTelemetry / Jaeger]
    R --> PM[Prometheus / Grafana]
    R --> MCP[MCP server]
```

## Design principles

1. **Live data for the portfolio path.** GitHub Status incidents and component state are fetched at runtime.
2. **Deterministic control around the LLM.** Tool minimality, permissions, validation, retries, and fallback are deterministic.
3. **Read-only by default.** Current tools cannot mutate external systems. A human-approval gate exists for any future write tool.
4. **Traceable evidence.** Public evidence carries `source`, `source_url`, and `fetched_at` metadata.
5. **Local-first and zero paid API.** Ollama runs locally; infrastructure is open source and self-hosted.
