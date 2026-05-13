# ADR-001: AI Must Be Policy-Constrained

## Status

Accepted

## Context

An SRE copilot can suggest useful operational actions, but AI output is not a trusted execution source. Production systems need deterministic control over what can run.

## Decision

All AI-suggested actions must pass through `policy/actions.yaml`.

The policy defines:

- allowlisted actions
- denied actions
- namespace constraints
- target patterns
- approval requirements

## Consequences

- AI can help with triage and planning.
- AI cannot run arbitrary shell commands.
- Dangerous actions such as secret access, namespace deletion, and raw manifest application are blocked.
- Policy can be reviewed like infrastructure code.
