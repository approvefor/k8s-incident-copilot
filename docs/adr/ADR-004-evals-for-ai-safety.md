# ADR-004: Evals For AI Safety

## Status

Accepted

## Context

AI behavior needs regression tests. A useful copilot should keep diagnosing known incident classes while continuing to deny dangerous actions.

## Decision

Incident scenarios live in `evals/incidents.yaml` and run through `scripts/run-evals.py`.

The evals check:

- expected runbook citations
- diagnosis themes
- forbidden actions

## Consequences

- AI behavior becomes testable in CI.
- Guardrails are validated continuously.
- The project shows operational AI discipline, not just prompt experimentation.
