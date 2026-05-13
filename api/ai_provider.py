from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field

from .runbooks import RunbookMatch


class RemediationStep(BaseModel):
    action: str
    target: str
    namespace: str = "ai-platform"
    reason: str
    requires_approval: bool = True


class IncidentReport(BaseModel):
    provider: str
    summary: str
    probable_cause: str
    affected_services: list[str]
    severity: str
    evidence: list[str]
    runbook_citations: list[RunbookMatch]
    remediation_plan: list[RemediationStep]
    guardrails: list[str] = Field(default_factory=list)


class SREAIProvider:
    name = "rule-based-local"

    def analyze(self, context: dict[str, Any], runbooks: list[RunbookMatch]) -> IncidentReport:
        logs = context.get("logs", [])
        query = str(context.get("query") or "")
        service = str(context.get("service") or "unknown")
        affected = sorted({str(log.get("service", service)) for log in logs}) or [service]
        levels = {str(log.get("level", "INFO")) for log in logs}
        severity = "critical" if "CRITICAL" in levels else "high" if "ERROR" in levels else "medium"
        evidence = [
            f"{log.get('level')} {log.get('service')}: {log.get('message')}"
            for log in logs[:5]
        ]
        if not evidence:
            evidence = [f"No indexed logs matched query '{query}'. Falling back to runbooks and Kubernetes context."]

        probable_cause = infer_cause(query, evidence)
        remediation_plan = build_plan(query=query, service=affected[0], evidence=evidence)
        return IncidentReport(
            provider=self.name,
            summary=f"{severity.title()} incident triage for {', '.join(affected)}.",
            probable_cause=probable_cause,
            affected_services=affected,
            severity=severity,
            evidence=evidence,
            runbook_citations=runbooks,
            remediation_plan=remediation_plan,
            guardrails=[
                "Read-only diagnosis is always allowed.",
                "Cluster-changing actions require explicit approval.",
                "Arbitrary shell, secret access, and namespace deletion are denied by policy.",
            ],
        )


def get_ai_provider() -> SREAIProvider:
    provider = os.getenv("AI_PROVIDER", "local").lower()
    if provider not in {"local", "rule-based"}:
        return SREAIProvider()
    return SREAIProvider()


def infer_cause(query: str, evidence: list[str]) -> str:
    text = " ".join([query, *evidence]).lower()
    if "timeout" in text or "latency" in text:
        return "The incident likely involves a slow or unavailable dependency causing request timeouts."
    if "crash" in text or "restart" in text or "oom" in text:
        return "The incident likely involves an unstable workload, resource pressure, or a bad rollout."
    if "503" in text or "provider" in text or "upstream" in text:
        return "The incident likely comes from an upstream dependency returning errors."
    if "redis" in text or "pool" in text:
        return "The incident likely involves exhausted connection pools or cache dependency pressure."
    return "The incident needs more correlated logs, metrics, Kubernetes events, and recent deploy context."


def build_plan(query: str, service: str, evidence: list[str]) -> list[RemediationStep]:
    text = " ".join([query, *evidence]).lower()
    target = deployment_target(service)
    plan = [
        RemediationStep(
            action="rollout_status",
            target=target,
            reason="Confirm whether the current deployment is healthy before changing state.",
            requires_approval=False,
        )
    ]
    if "timeout" in text or "latency" in text:
        plan.append(
            RemediationStep(
                action="scale_deployment",
                target=target,
                reason="Add temporary capacity while checking dependency latency and saturation.",
            )
        )
    if "crash" in text or "bad rollout" in text or "restart" in text:
        plan.append(
            RemediationStep(
                action="rollback_deployment",
                target=target,
                reason="Rollback can restore service if symptoms started after the latest rollout.",
            )
        )
    plan.append(
        RemediationStep(
            action="restart_deployment",
            target=target,
            reason="Restart is a last-resort recovery action after checking rollout and dependencies.",
        )
    )
    return plan


def deployment_target(service: str) -> str:
    release = os.getenv("K8S_RELEASE_FULLNAME", "ai-platform-ai-platform")
    if service in {"api", "worker"}:
        return f"{release}-{service}"
    return service
