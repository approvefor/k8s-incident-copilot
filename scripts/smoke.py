#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.request


BASE_URL = os.getenv("API_URL", "http://localhost:8000")


def step(name: str) -> None:
    print(f"\n==> {name}", flush=True)


def request(
    method: str,
    path: str,
    body: dict | None = None,
    *,
    attempts: int = 1,
    delay_seconds: float = 1.0,
):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(delay_seconds)

    raise RuntimeError(
        f"{method} {path} failed after {attempts} attempt(s): {last_error}"
    )


step("Checking health")
request("GET", "/healthz", attempts=15)

step("Checking readiness")
request("GET", "/readyz", attempts=30)

step("Indexing incident evidence")
request(
    "POST",
    "/logs",
    {
        "service": "api",
        "level": "ERROR",
        "message": "database timeout while processing checkout request",
        "trace_id": "smoke-timeout-1",
    },
)
request(
    "POST",
    "/logs",
    {
        "service": "api",
        "level": "ERROR",
        "message": "connection pool exhausted after recent deploy",
        "trace_id": "smoke-timeout-2",
    },
)

incident = {
    "service": "api",
    "query": "database timeout and high latency after deploy",
    "mode": "suggest",
    "actor": "smoke-test",
}

step("Analyzing incident")
analyze_response = request("POST", "/incidents/analyze", incident)
assert "database-timeouts" in json.dumps(analyze_response)
assert "remediation_plan" in analyze_response["report"]

step("Evaluating policy plan")
plan_response = request("POST", "/actions/plan", incident)
plan_text = json.dumps(plan_response)
assert "kubectl" in plan_text
assert "rollout" in plan_text
assert '"requires_approval": true' in plan_text
assert '"allowed": false' in plan_text

step("Verifying dangerous action is denied")
denied_response = request(
    "POST",
    "/actions/execute",
    {
        "action": "get_secret",
        "target": "api",
        "namespace": "ai-platform",
        "approved": True,
        "dry_run": True,
        "actor": "smoke-test",
        "reason": "verify secret access is denied",
    },
)
denied_text = json.dumps(denied_response)
assert denied_response["decision"]["allowed"] is False
assert denied_response["executed"] is False
assert "explicitly denied" in denied_text

step("Checking audit trail")
audit_response = request("GET", "/audit/events?limit=10")
assert any(
    event["action"] == "get_secret" and event["decision"] == "denied"
    for event in audit_response
)
assert any(
    event["action"] == "incident.analyze" and event["decision"] == "generated"
    for event in audit_response
)

print(f"\nSmoke test passed for {BASE_URL}", flush=True)
