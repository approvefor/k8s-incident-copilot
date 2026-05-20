# Production Checklist

Use this before publishing the project or demoing a production-style deployment.

## Local / WSL

- `python -m pytest -q`
- `python scripts/run-evals.py`
- `docker compose up --build`
- `./scripts/demo.sh`

## Helm

- `helm dependency update deploy/helm/ai-platform`
- `helm lint deploy/helm/ai-platform`
- `helm template ai-platform deploy/helm/ai-platform > /tmp/rendered.yaml`
- `helm lint deploy/helm/ai-platform -f deploy/helm/ai-platform/values-production.yaml`
- `helm template ai-platform deploy/helm/ai-platform -f deploy/helm/ai-platform/values-production.yaml > /tmp/rendered-prod.yaml`

## Security

- API and worker run as non-root.
- Service account token is not mounted into the API pod.
- Actions are dry-run-only in the API.
- Real action execution requires a separate restricted action-runner.
- `OPENAI_API_KEY` is loaded only from Kubernetes Secret / ExternalSecret.
- External HTTPS egress is disabled by default and enabled only for OpenAI mode.
- Production audit uses a persistent database URL from a secret.
- Production MinIO credentials come from `ai-platform-secrets`.
- CI publishes SBOM artifacts for pushed images.
- CI signs pushed container images with keyless Cosign.
- Kyverno examples document admission checks for non-root pods, read-only
  filesystems, resource limits, and digest-pinned images.
- Production clusters should add Cosign signature verification at admission time.

## AI Safety

- Evals cover expected runbook retrieval.
- Evals cover denied dangerous actions.
- Runbook citations are returned in incident reports.
- Policy denies secret access, namespace deletion, raw manifest apply, and arbitrary shell.

## Demo Readiness

- `make smoke` passes against a running local stack.
- `docs/demo-output.md` shows the expected smoke-test output.
- `docs/demo-transcript.md` explains the incident story without requiring the stack.

## Observability

- `/metrics` is scraped by Prometheus.
- Grafana dashboard imports cleanly.
- OpenTelemetry endpoint is configured for tracing.
- `/readyz` checks Qdrant collection and audit persistence.
