from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from backend.agent.graph import run_investigation
from backend.observability import init_tracing, record_investigation_metrics
from backend.persistence import (
    init_db,
    load_session,
    recent_evaluations,
    recent_investigations,
    save_investigation,
    save_session,
)
from backend.tools.public_status_tool import (
    get_public_incident_metrics,
    get_public_status_summary,
    online_source_health,
    search_public_incidents,
)


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    session_id: str | None = Field(default=None, max_length=64)
    approved_tools: list[str] = Field(default_factory=list)


class InvestigationResponse(BaseModel):
    investigation_id: str
    persistence_id: int | None = None
    question: str
    plan: list[dict[str, str]]
    current_step: int
    answer: str
    answer_valid: bool
    answer_validation_issues: list[str]
    requires_human_review: bool
    planner_duration_ms: float
    answer_duration_ms: float
    investigation_duration_ms: float
    tool_history: list[dict[str, Any]]
    llm_history: list[dict[str, Any]]
    observability_summary: dict[str, Any]
    recovery_attempted: bool
    recovery_actions: list[dict[str, Any]]
    status_result: dict[str, Any]
    incident_result: list[dict[str, Any]]
    incident_metrics: dict[str, Any]
    metrics: dict[str, Any]
    sql_result: dict[str, Any]
    log_result: list[str]
    knowledge_result: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


init_tracing()
app = FastAPI(
    title="AgentOps Local",
    version="2.0.0",
    description=(
        "Local multi-tool AI incident investigation agent with live public "
        "Statuspage evidence, persistence, tracing, validation, and MCP integration."
    ),
    lifespan=lifespan,
)
app.mount("/metrics", make_asgi_app())
FastAPIInstrumentor.instrument_app(app)


@app.get("/")
def root() -> dict:
    return {
        "name": "AgentOps Local",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "online_source_health": "/source-health",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/source-health")
def source_health() -> dict:
    try:
        return online_source_health()
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/public-status")
def public_status() -> dict:
    try:
        return get_public_status_summary()
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/public-incidents")
def public_incidents(
    q: str = Query(default="latest", max_length=500),
    limit: int = Query(default=3, ge=1, le=10),
) -> list[dict]:
    try:
        return search_public_incidents(q, limit=limit)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.get("/public-incident-metrics")
def public_incident_metrics() -> dict:
    try:
        return get_public_incident_metrics()
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@app.post("/investigate", response_model=InvestigationResponse)
def investigate(request: InvestigationRequest) -> dict:
    try:
        result = run_investigation(
            request.question,
            approved_tools=request.approved_tools,
        )
        persistence_id = save_investigation(request.question, result)
        result["persistence_id"] = persistence_id
        if request.session_id:
            save_session(request.session_id, result)
        record_investigation_metrics(result)
        return result
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/investigations")
def investigations(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    return recent_investigations(limit)


@app.get("/sessions/{session_id}")
def session_state(session_id: str) -> dict:
    row = load_session(session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@app.get("/evaluations")
def evaluations(limit: int = Query(default=20, ge=1, le=100)) -> list[dict]:
    return recent_evaluations(limit)
