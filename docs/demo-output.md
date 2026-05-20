# Demo Output

This is the expected local smoke path after the stack is running.

```bash
cp .env.example .env
make compose-up
make smoke
```

Expected result:

```text
==> Checking health

==> Checking readiness

==> Indexing incident evidence

==> Analyzing incident

==> Evaluating policy plan

==> Verifying dangerous action is denied

==> Checking audit trail

Smoke test passed for http://localhost:8000
```

The smoke script validates the interview-critical path:

- `/healthz` and `/readyz` respond successfully.
- incident logs are indexed;
- `/incidents/analyze` returns the `database-timeouts` runbook citation;
- `/actions/plan` returns a read-only rollout check and blocks scaling until approval;
- `/actions/execute` denies `get_secret` even when `approved=true`;
- `/audit/events` records both generated and denied decisions.

Useful manual calls:

```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/readyz
curl -fsS http://localhost:8000/audit/events?limit=10
```
