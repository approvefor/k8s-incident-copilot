#!/usr/bin/env sh
set -eu

BASE_URL="${API_URL:-http://localhost:8000}"

step() {
  printf "\n==> %s\n" "$1"
}

detect_compose() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
    return 0
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return 0
  fi

  echo "Docker Compose was not found." >&2
  echo "WSL fix: enable Docker Desktop WSL integration or run: sudo apt install -y docker-compose-plugin" >&2
  exit 1
}

step "Starting local stack"
COMPOSE="$(detect_compose)"
$COMPOSE up --build -d

step "Waiting for API readiness"
i=0
until curl -fsS "$BASE_URL/readyz" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -gt 30 ]; then
    echo "API did not become ready" >&2
    exit 1
  fi
  sleep 2
done

step "Injecting incident logs"
curl -fsS -X POST "$BASE_URL/logs" -H "Content-Type: application/json" \
  -d '{"service":"api","level":"ERROR","message":"database timeout while processing checkout request","trace_id":"demo-timeout-1"}' >/dev/null
curl -fsS -X POST "$BASE_URL/logs" -H "Content-Type: application/json" \
  -d '{"service":"api","level":"ERROR","message":"connection pool exhausted after recent deploy","trace_id":"demo-timeout-2"}' >/dev/null
curl -fsS -X POST "$BASE_URL/logs" -H "Content-Type: application/json" \
  -d '{"service":"gateway","level":"WARNING","message":"upstream latency above SLO threshold","trace_id":"demo-timeout-3"}' >/dev/null

INCIDENT='{"service":"api","query":"database timeout and high latency after deploy","mode":"suggest","actor":"demo-user"}'

step "AI SRE triage report"
curl -fsS -X POST "$BASE_URL/incidents/analyze" -H "Content-Type: application/json" -d "$INCIDENT"

step "Policy-checked action plan"
curl -fsS -X POST "$BASE_URL/actions/plan" -H "Content-Type: application/json" -d "$INCIDENT"

step "Denied dangerous action demo"
curl -fsS -X POST "$BASE_URL/actions/execute" -H "Content-Type: application/json" \
  -d '{"action":"get_secret","target":"api","namespace":"ai-platform","approved":true,"dry_run":true,"actor":"demo-user","reason":"AI should never access secrets"}'

step "Audit trail"
curl -fsS "$BASE_URL/audit/events?limit=10"

printf "\nDemo complete: %s/docs\n" "$BASE_URL"
