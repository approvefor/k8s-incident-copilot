# ADR-002: Human Approval For State-Changing Actions

## Status

Accepted

## Context

Some remediation actions are safe to inspect, while others change cluster state. The system should support AI-assisted operations without removing operator accountability.

## Decision

Read-only actions can be planned without approval. State-changing actions require `approved: true`, but the API itself remains dry-run-only.

Real execution should be delegated to a separate restricted action-runner with scoped Kubernetes RBAC, timeouts, audit logging, and network policy.

Examples:

- `rollout_status`: no approval required
- `scale_deployment`: approval required
- `rollback_deployment`: approval required
- `restart_deployment`: approval required

## Consequences

- The copilot can be used during real incident response planning.
- Operators keep final control over cluster changes.
- The audit trail records who approved or denied each action.
