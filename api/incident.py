from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from .ai_provider import IncidentReport, get_ai_provider
from .audit import audit_log
from .policy import ActionMode
from .runbooks import RunbookMatch, search_runbooks


class LogEvidence(BaseModel):
    service: str
    level: str
    message: str
    trace_id: str | None = None
    score: float | None = None


class KubernetesSnapshot(BaseModel):
    namespace: str
    deployment: str
    ready_replicas: int
    desired_replicas: int
    restart_count_15m: int
    recent_rollout: str


class MetricsSnapshot(BaseModel):
    p95_latency_ms: int
    error_rate_percent: float
    cpu_utilization_percent: int
    memory_utilization_percent: int


class TimelineEvent(BaseModel):
    time: str
    source: str
    event: str
    impact: str


class IncidentAnalyzeRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    service: str = Field(default="api", min_length=2, max_length=80)
    namespace: str = "ai-platform"
    mode: ActionMode = "suggest"
    actor: str = "local-user"


class IncidentAnalyzeResponse(BaseModel):
    incident_id: str
    created_at: datetime
    mode: ActionMode
    query: str
    executive_summary: str
    confidence: float
    timeline: list[TimelineEvent]
    context: dict[str, object]
    report: IncidentReport


def analyze_incident(
    request: IncidentAnalyzeRequest,
    logs: list[LogEvidence],
) -> IncidentAnalyzeResponse:
    runbooks = search_runbooks(f"{request.query} {request.service}", limit=3)
    k8s = build_kubernetes_snapshot(request)
    metrics = build_metrics_snapshot(request, logs)
    context = {
        "query": request.query,
        "service": request.service,
        "namespace": request.namespace,
        "logs": [log.model_dump() for log in logs],
        "kubernetes": k8s.model_dump(),
        "metrics": metrics.model_dump(),
        "runbooks": [runbook.model_dump() for runbook in runbooks],
    }
    report = get_ai_provider().analyze(context, runbooks)
    timeline = build_timeline(request, logs, metrics, report.runbook_citations)
    response = IncidentAnalyzeResponse(
        incident_id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        mode=request.mode,
        query=request.query,
        executive_summary=(
            f"{report.severity.title()} incident affecting {', '.join(report.affected_services)}. "
            f"{report.probable_cause}"
        ),
        confidence=estimate_confidence(logs, runbooks),
        timeline=timeline,
        context=context,
        report=report,
    )
    audit_log.record(
        actor=request.actor,
        action="incident.analyze",
        resource=f"{request.namespace}/{request.service}",
        decision="generated",
        details={
            "incident_id": response.incident_id,
            "mode": request.mode,
            "query": request.query,
            "runbook_citations": [runbook.id for runbook in runbooks],
        },
    )
    return response


def build_kubernetes_snapshot(request: IncidentAnalyzeRequest) -> KubernetesSnapshot:
    return KubernetesSnapshot(
        namespace=request.namespace,
        deployment=request.service,
        ready_replicas=1,
        desired_replicas=2,
        restart_count_15m=2 if "crash" in request.query.lower() else 0,
        recent_rollout="unknown in local demo; integrate Argo CD/GitHub deploy metadata in production",
    )


def build_metrics_snapshot(
    request: IncidentAnalyzeRequest,
    logs: list[LogEvidence],
) -> MetricsSnapshot:
    text = " ".join([request.query, *[log.message for log in logs]]).lower()
    latency = 1200 if "timeout" in text or "latency" in text else 180
    error_rate = 8.5 if any(log.level in {"ERROR", "CRITICAL"} for log in logs) else 0.4
    return MetricsSnapshot(
        p95_latency_ms=latency,
        error_rate_percent=error_rate,
        cpu_utilization_percent=74 if latency > 1000 else 38,
        memory_utilization_percent=61,
    )


def build_timeline(
    request: IncidentAnalyzeRequest,
    logs: list[LogEvidence],
    metrics: MetricsSnapshot,
    runbooks: list[RunbookMatch],
) -> list[TimelineEvent]:
    return [
        TimelineEvent(
            time="T-10m",
            source="deploy",
            event="Recent rollout context collected",
            impact="Correlates symptoms with release activity before remediation.",
        ),
        TimelineEvent(
            time="T-05m",
            source="metrics",
            event=f"p95 latency {metrics.p95_latency_ms}ms, error rate {metrics.error_rate_percent}%",
            impact="Quantifies user-facing impact and severity.",
        ),
        TimelineEvent(
            time="T-03m",
            source="logs",
            event=logs[0].message if logs else f"No direct log match for '{request.query}'",
            impact="Provides evidence for the diagnosis.",
        ),
        TimelineEvent(
            time="T-01m",
            source="runbook",
            event=runbooks[0].title if runbooks else "No runbook citation found",
            impact="Grounds AI output in operational documentation.",
        ),
        TimelineEvent(
            time="T+00m",
            source="ai-policy",
            event="AI remediation plan evaluated by policy engine",
            impact="Only allowlisted actions can proceed, with approval for state changes.",
        ),
    ]


def estimate_confidence(logs: list[LogEvidence], runbooks: list[RunbookMatch]) -> float:
    score = 0.35
    if logs:
        score += 0.3
    if runbooks:
        score += min(runbooks[0].score, 0.25)
    return round(min(score, 0.9), 2)
