from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field


POLICY_PATH = Path(__file__).resolve().parent.parent / "policy" / "actions.yaml"


class ActionRequest(BaseModel):
    action: str
    namespace: str = "ai-platform"
    target: str
    approved: bool = False
    dry_run: bool = Field(default=True, description="Always forced to true by the API execution endpoint.")
    actor: str = "local-user"
    reason: str = Field(default="", max_length=500)


class PolicyDecision(BaseModel):
    allowed: bool
    reason: str
    requires_approval: bool = True
    command: list[str] = Field(default_factory=list)


def load_policy() -> dict[str, Any]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def evaluate_action(request: ActionRequest) -> PolicyDecision:
    policy = load_policy()
    denied = policy.get("denied_actions", [])
    if any(fnmatch.fnmatch(request.action, pattern) for pattern in denied):
        return PolicyDecision(allowed=False, reason=f"Action '{request.action}' is explicitly denied.")

    allowed_actions = policy.get("allowed_actions", {})
    config = allowed_actions.get(request.action)
    if not config:
        return PolicyDecision(allowed=False, reason=f"Action '{request.action}' is not allowlisted.")

    namespace_policy = config.get("namespaces", [])
    if namespace_policy and request.namespace not in namespace_policy:
        return PolicyDecision(
            allowed=False,
            reason=f"Namespace '{request.namespace}' is not allowed for '{request.action}'.",
        )

    target_patterns = config.get("target_patterns", ["*"])
    if not any(fnmatch.fnmatch(request.target, pattern) for pattern in target_patterns):
        return PolicyDecision(
            allowed=False,
            reason=f"Target '{request.target}' does not match policy for '{request.action}'.",
        )

    requires_approval = bool(config.get("requires_approval", True))
    if requires_approval and not request.approved:
        return PolicyDecision(
            allowed=False,
            reason=f"Action '{request.action}' requires human approval.",
            requires_approval=True,
            command=render_command(request),
        )

    return PolicyDecision(
        allowed=True,
        reason="Action is allowed by policy.",
        requires_approval=requires_approval,
        command=render_command(request),
    )


def render_command(request: ActionRequest) -> list[str]:
    commands: dict[str, list[str]] = {
        "rollout_status": ["kubectl", "rollout", "status", f"deployment/{request.target}", "-n", request.namespace],
        "scale_deployment": ["kubectl", "scale", f"deployment/{request.target}", "-n", request.namespace, "--replicas=3"],
        "rollback_deployment": ["kubectl", "rollout", "undo", f"deployment/{request.target}", "-n", request.namespace],
        "restart_deployment": ["kubectl", "rollout", "restart", f"deployment/{request.target}", "-n", request.namespace],
    }
    return commands.get(request.action, [])


ActionMode = Literal["read_only", "suggest", "approved_action"]
