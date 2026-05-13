# CrashLoopBackOff Runbook

## Symptoms

- Pods repeatedly restart.
- Kubernetes reports `CrashLoopBackOff`.
- Logs include startup failures, missing config, OOMKilled, or failed migrations.

## Triage

1. Check `kubectl rollout status`.
2. Inspect pod events and last container logs.
3. Compare image tag and config with the last successful deployment.
4. Check memory limits and OOMKilled status.

## Remediation

- Roll back the deployment if the new image or config caused the crash.
- Increase memory limits only if metrics prove memory pressure.
- Restart the deployment after config recovery.

## Guardrails

- Do not delete namespaces.
- Do not expose Kubernetes Secrets to the AI context.
- Do not run arbitrary shell commands from AI output.
