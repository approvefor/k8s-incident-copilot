# Database Timeout Runbook

## Symptoms

- API p95 latency rises above the SLO.
- Logs include `database timeout`, `connection refused`, or `pool exhausted`.
- Error rate increases after traffic spikes or a deployment.

## Triage

1. Check API request rate and p95 latency in Grafana.
2. Check Postgres CPU, active connections, locks, and slow queries.
3. Compare the incident window with the latest deployment.
4. Verify whether connection pools are exhausted.

## Remediation

- Scale API replicas only as a temporary mitigation.
- Reduce worker concurrency if database saturation is confirmed.
- Roll back the latest deployment if the issue started immediately after release.
- Add an index or tune query timeout only after root cause confirmation.

## Guardrails

- Do not restart the database before checking active connections and replication state.
- Do not delete persistent volumes.
- Production rollbacks require approval.
