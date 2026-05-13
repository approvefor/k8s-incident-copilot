# AI SRE Copilot Design

This project demonstrates a DevOps engineer using AI as an operational copilot, not as an uncontrolled automation bot.

## Workflow

1. An operator opens an incident with a service and symptom query.
2. The API collects relevant log evidence from Qdrant.
3. The runbook retriever finds matching operational docs.
4. The AI provider generates a triage report with probable cause, evidence, citations, and remediation steps.
5. The policy engine evaluates every proposed action.
6. Only allowlisted actions can produce dry-run commands, and state-changing actions require explicit approval.
7. Every analysis and action decision is written to the audit trail.

## AI Boundaries

- AI can summarize logs, metrics, Kubernetes state, and runbooks.
- AI can propose remediation steps.
- AI cannot access Kubernetes Secrets.
- AI cannot run arbitrary shell commands.
- AI cannot delete namespaces, persistent volumes, or raw manifests.
- Production-changing actions require approval and policy validation.

## Endpoints

- `POST /incidents/analyze` creates an AI triage report.
- `GET /runbooks/search` searches runbooks with lightweight RAG.
- `POST /actions/plan` evaluates proposed remediation steps against policy.
- `POST /actions/execute` returns a dry-run command for an allowlisted action only after approval.
- `GET /audit/events` returns the audit trail.

## Kubernetes Modes

- Default mode uses local deterministic embeddings and bundled PostgreSQL audit persistence.
- OpenAI embedding mode requires `api.openai.enabled=true`, an `OPENAI_API_KEY` secret, and HTTPS egress enabled in NetworkPolicy.

## What This Shows

- AI integration design for SRE workflows.
- Guardrails around AI-generated operational actions.
- Human-in-the-loop approval.
- Policy-as-code for allowed and forbidden actions.
- Eval scenarios for AI behavior and safety expectations.
