# ADR-003: Runbooks As Citations

## Status

Accepted

## Context

AI incident diagnosis is more credible when it is grounded in operational knowledge. Hidden prompt context makes answers hard to verify.

## Decision

Runbooks are stored as markdown in `runbooks/` and returned as citations in incident reports.

The report includes:

- matching runbook id
- title
- path
- relevance score
- excerpt

## Consequences

- Operators can verify why the AI suggested a diagnosis.
- Runbooks evolve through normal pull requests.
- The project demonstrates RAG in an SRE-specific workflow without overcomplicating the MVP.
