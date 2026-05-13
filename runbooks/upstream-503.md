# Upstream 503 Runbook

## Symptoms

- API logs show `503`, `upstream unavailable`, or provider errors.
- Error budget burn rate increases.
- Retries may amplify traffic against the failing dependency.

## Triage

1. Check upstream status page or dependency health endpoint.
2. Compare retry volume and request rate.
3. Inspect circuit breaker and timeout settings.
4. Check whether only one service or region is affected.

## Remediation

- Enable degraded mode if supported.
- Reduce retry pressure.
- Temporarily scale workers down if they are amplifying dependency failures.
- Escalate to the upstream owner with trace IDs and error samples.

## Guardrails

- Scaling is a mitigation, not root-cause resolution.
- Do not rotate credentials unless authentication failures are confirmed.
