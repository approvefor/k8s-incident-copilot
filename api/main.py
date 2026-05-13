from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from opentelemetry import trace
from prometheus_client import Counter, Histogram, generate_latest
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from starlette.responses import Response

from .actions import ActionExecutionResult, execute_action
from .audit import AuditEvent, AuditPersistenceError, audit_log
from .embeddings import embed_text, embedding_dimensions
from .incident import (
    IncidentAnalyzeRequest,
    IncidentAnalyzeResponse,
    LogEvidence,
    analyze_incident,
)
from .policy import ActionRequest, PolicyDecision, evaluate_action
from .runbooks import RunbookMatch, search_runbooks

APP_NAME = "ai-sre-copilot-api"
COLLECTION = os.getenv("QDRANT_COLLECTION", "devops_logs")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
VECTOR_SIZE = embedding_dimensions()

REQUESTS = Counter("api_requests_total", "Total API requests", ["endpoint"])
LATENCY = Histogram("api_request_latency_seconds", "API request latency", ["endpoint"])
LOGS_INGESTED = Counter("logs_ingested_total", "Total ingested logs", ["service", "level"])

qdrant = QdrantClient(url=QDRANT_URL)


def configure_tracing() -> None:
    if not OTEL_EXPORTER_OTLP_ENDPOINT:
        return

    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": APP_NAME}))
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT))
    )
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)


class LogEvent(BaseModel):
    service: str = Field(min_length=2, max_length=80)
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str = Field(min_length=3, max_length=2000)
    trace_id: str | None = None
    timestamp: datetime | None = None


class SearchResult(BaseModel):
    id: str
    score: float
    service: str
    level: str
    message: str
    trace_id: str | None = None
    timestamp: datetime


def embed(text: str) -> list[float]:
    return embed_text(text)


def ensure_collection() -> None:
    collections = qdrant.get_collections().collections
    if not any(collection.name == COLLECTION for collection in collections):
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        return

    collection = qdrant.get_collection(COLLECTION)
    vector_config = collection.config.params.vectors
    actual_size = getattr(vector_config, "size", None)
    if actual_size is None and isinstance(vector_config, dict):
        first_vector = next(iter(vector_config.values()))
        actual_size = getattr(first_vector, "size", None)
    if actual_size != VECTOR_SIZE:
        raise RuntimeError(
            f"Qdrant collection '{COLLECTION}' has vector size {actual_size}, expected {VECTOR_SIZE}."
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Keep startup independent from external services. Kubernetes readiness
    # reports Qdrant/audit availability via /readyz, and write/search paths
    # initialize the collection before using it.
    yield


app = FastAPI(title="AI SRE Copilot", version="0.1.0", lifespan=lifespan)
configure_tracing()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    REQUESTS.labels("/healthz").inc()
    return {"status": "ok", "service": APP_NAME}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    REQUESTS.labels("/readyz").inc()
    try:
        ensure_collection()
    except Exception as exc:  # pragma: no cover - defensive health endpoint
        raise HTTPException(status_code=503, detail="qdrant collection unavailable") from exc
    if audit_log.requires_persistence() and not audit_log.is_persistent:
        raise HTTPException(status_code=503, detail="audit persistence unavailable")
    return {"status": "ready"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type="text/plain; version=0.0.4")


@app.post("/logs", status_code=202)
def ingest_log(event: LogEvent) -> dict[str, str]:
    start = time.perf_counter()
    REQUESTS.labels("/logs").inc()
    ensure_collection()
    event_id = str(uuid4())
    timestamp = event.timestamp or datetime.now(timezone.utc)
    payload = {
        "service": event.service,
        "level": event.level,
        "message": event.message,
        "trace_id": event.trace_id,
        "timestamp": timestamp.isoformat(),
    }
    with trace.get_tracer(APP_NAME).start_as_current_span("qdrant.upsert_log"):
        qdrant.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(id=event_id, vector=embed(event.message), payload=payload)],
        )
    LOGS_INGESTED.labels(event.service, event.level).inc()
    LATENCY.labels("/logs").observe(time.perf_counter() - start)
    return {"id": event_id, "status": "indexed"}


@app.get("/search", response_model=list[SearchResult])
def search(q: str, limit: int = 5) -> list[SearchResult]:
    start = time.perf_counter()
    REQUESTS.labels("/search").inc()
    with trace.get_tracer(APP_NAME).start_as_current_span("qdrant.search_logs"):
        results = qdrant.search(
            collection_name=COLLECTION,
            query_vector=embed(q),
            limit=max(1, min(limit, 20)),
            with_payload=True,
        )
    LATENCY.labels("/search").observe(time.perf_counter() - start)
    return [
        SearchResult(
            id=str(item.id),
            score=item.score,
            service=str(item.payload["service"]),
            level=str(item.payload["level"]),
            message=str(item.payload["message"]),
            trace_id=item.payload.get("trace_id"),
            timestamp=datetime.fromisoformat(str(item.payload["timestamp"])),
        )
        for item in results
    ]


@app.post("/explain")
def explain(q: str) -> dict[str, object]:
    REQUESTS.labels("/explain").inc()
    matches = search(q=q, limit=3)
    if not matches:
        return {
            "summary": "No related incidents found.",
            "probable_cause": "Insufficient data.",
            "next_steps": ["Ingest more logs", "Check service health", "Review recent deploys"],
            "matches": [],
        }

    critical = [match for match in matches if match.level in {"ERROR", "CRITICAL"}]
    top = critical[0] if critical else matches[0]
    return {
        "summary": f"{top.service} reports {top.level.lower()} symptoms related to: {top.message}",
        "probable_cause": "The highest-scoring logs point to a dependency, timeout, or recent release issue.",
        "next_steps": [
            f"Inspect trace_id={top.trace_id or 'unknown'}",
            f"Check {top.service} pod restarts and latency",
            "Compare error rate before and after the latest deployment",
        ],
        "matches": [match.model_dump() for match in matches],
    }


@app.get("/runbooks/search", response_model=list[RunbookMatch])
def runbook_search(q: str, limit: int = 5) -> list[RunbookMatch]:
    REQUESTS.labels("/runbooks/search").inc()
    return search_runbooks(q, limit=max(1, min(limit, 10)))


@app.post("/incidents/analyze", response_model=IncidentAnalyzeResponse)
def incidents_analyze(request: IncidentAnalyzeRequest) -> IncidentAnalyzeResponse:
    REQUESTS.labels("/incidents/analyze").inc()
    try:
        matches = search(q=f"{request.service} {request.query}", limit=5)
    except Exception:
        matches = []
    logs = [
        LogEvidence(
            service=match.service,
            level=match.level,
            message=match.message,
            trace_id=match.trace_id,
            score=match.score,
        )
        for match in matches
    ]
    try:
        return analyze_incident(request, logs)
    except AuditPersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/actions/plan", response_model=list[PolicyDecision])
def actions_plan(request: IncidentAnalyzeRequest) -> list[PolicyDecision]:
    REQUESTS.labels("/actions/plan").inc()
    incident = incidents_analyze(request)
    decisions: list[PolicyDecision] = []
    for step in incident.report.remediation_plan:
        decisions.append(
            evaluate_action(
                ActionRequest(
                    action=step.action,
                    namespace=step.namespace,
                    target=step.target,
                    approved=not step.requires_approval,
                    dry_run=True,
                    actor=request.actor,
                    reason=step.reason,
                )
            )
        )
    return decisions


@app.post("/actions/execute", response_model=ActionExecutionResult)
def actions_execute(request: ActionRequest) -> ActionExecutionResult:
    REQUESTS.labels("/actions/execute").inc()
    try:
        return execute_action(request)
    except AuditPersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/audit/events", response_model=list[AuditEvent])
def audit_events(limit: int = 50) -> list[AuditEvent]:
    REQUESTS.labels("/audit/events").inc()
    try:
        return audit_log.list_events(limit=max(1, min(limit, 200)))
    except AuditPersistenceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
