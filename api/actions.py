from __future__ import annotations

from pydantic import BaseModel

from .audit import audit_log
from .policy import ActionRequest, PolicyDecision, evaluate_action


class ActionExecutionResult(BaseModel):
    decision: PolicyDecision
    executed: bool
    output: str


def execute_action(request: ActionRequest) -> ActionExecutionResult:
    request.dry_run = True
    decision = evaluate_action(request)
    audit_log.record(
        actor=request.actor,
        action=request.action,
        resource=f"{request.namespace}/{request.target}",
        decision="allowed" if decision.allowed else "denied",
        details={
            "reason": decision.reason,
            "dry_run": request.dry_run,
            "approved": request.approved,
            "command": decision.command,
        },
    )

    if not decision.allowed:
        return ActionExecutionResult(decision=decision, executed=False, output=decision.reason)

    return ActionExecutionResult(
        decision=decision,
        executed=False,
        output=(
            "Dry-run only. This API never executes kubectl directly; production execution "
            f"should be delegated to a restricted action-runner. Command: {' '.join(decision.command)}"
        ),
    )
