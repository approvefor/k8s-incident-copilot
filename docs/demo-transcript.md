# Demo Transcript

This is the short story to show in an interview or README walkthrough when the full
Docker stack is not running.

## Scenario

An SRE receives a checkout incident after a deploy:

```text
checkout database timeout and high latency
```

The worker has indexed related logs:

```text
ERROR api: database timeout while processing checkout request
ERROR api: connection pool exhausted after recent deploy
WARNING gateway: upstream latency above SLO threshold
```

## 1. AI Triage

`POST /incidents/analyze`

```json
{
  "service": "api",
  "query": "database timeout and high latency after deploy",
  "mode": "suggest",
  "actor": "demo-user"
}
```

Key response fields:

```json
{
  "executive_summary": "High incident affecting api. The incident likely involves a slow or unavailable dependency causing request timeouts.",
  "confidence": 0.9,
  "timeline": [
    {
      "time": "T-05m",
      "source": "metrics",
      "event": "p95 latency 1200ms, error rate 8.5%"
    },
    {
      "time": "T-01m",
      "source": "runbook",
      "event": "Database Timeouts"
    },
    {
      "time": "T+00m",
      "source": "ai-policy",
      "event": "AI remediation plan evaluated by policy engine"
    }
  ],
  "report": {
    "provider": "rule-based-local",
    "severity": "high",
    "probable_cause": "The incident likely involves a slow or unavailable dependency causing request timeouts.",
    "runbook_citations": [
      {
        "id": "database-timeouts",
        "path": "runbooks/database-timeouts.md"
      }
    ],
    "remediation_plan": [
      {
        "action": "rollout_status",
        "requires_approval": false
      },
      {
        "action": "scale_deployment",
        "requires_approval": true
      },
      {
        "action": "restart_deployment",
        "requires_approval": true
      }
    ]
  }
}
```

What this demonstrates:

- The AI report is grounded in logs, metrics-style context, and runbook citations.
- The model proposes operational actions, but does not execute them directly.
- State-changing steps are marked for human approval.

## 2. Policy-Checked Action Plan

`POST /actions/plan`

Representative output:

```json
[
  {
    "allowed": true,
    "reason": "Action is allowed by policy.",
    "requires_approval": false,
    "command": [
      "kubectl",
      "rollout",
      "status",
      "deployment/ai-platform-ai-platform-api",
      "-n",
      "ai-platform"
    ]
  },
  {
    "allowed": false,
    "reason": "Action 'scale_deployment' requires human approval.",
    "requires_approval": true,
    "command": [
      "kubectl",
      "scale",
      "deployment/ai-platform-ai-platform-api",
      "-n",
      "ai-platform",
      "--replicas=3"
    ]
  }
]
```

What this demonstrates:

- Read-only checks can proceed.
- Scaling is allowlisted, but blocked until a human approves it.
- The API returns a command preview for review.

## 3. Dangerous Action Blocked

`POST /actions/execute`

```json
{
  "action": "get_secret",
  "target": "api",
  "namespace": "ai-platform",
  "approved": true,
  "dry_run": true,
  "actor": "demo-user",
  "reason": "AI should never access secrets"
}
```

Response:

```json
{
  "decision": {
    "allowed": false,
    "reason": "Action 'get_secret' is explicitly denied.",
    "requires_approval": true,
    "command": []
  },
  "executed": false,
  "output": "Action 'get_secret' is explicitly denied."
}
```

What this demonstrates:

- Human approval does not override explicit deny rules.
- Secret access is blocked by policy.
- The endpoint is dry-run-only even for allowed actions.

## 4. Audit Trail

`GET /audit/events?limit=10`

Representative events:

```json
[
  {
    "actor": "demo-user",
    "action": "get_secret",
    "resource": "ai-platform/api",
    "decision": "denied",
    "details": {
      "reason": "Action 'get_secret' is explicitly denied.",
      "dry_run": true,
      "approved": true,
      "command": []
    }
  },
  {
    "actor": "demo-user",
    "action": "incident.analyze",
    "resource": "ai-platform/api",
    "decision": "generated",
    "details": {
      "runbook_citations": [
        "database-timeouts"
      ]
    }
  }
]
```

Interview summary:

```text
This project is not an AI chatbot. It is a controlled SRE workflow:
logs and runbooks provide context, the AI produces a triage report, policy checks
every proposed action, dangerous actions are denied, state changes require human
approval, and all decisions are auditable.
```
