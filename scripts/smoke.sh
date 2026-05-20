#!/usr/bin/env sh
set -eu

BASE_URL="${API_URL:-http://localhost:8000}"

step() {
  printf "\n==> %s\n" "$1"
}

post_json() {
  path="$1"
  body="$2"
  curl -fsS -X POST "$BASE_URL$path" \
    -H "Content-Type: application/json" \
    -d "$body"
}

step "Checking health"
curl -fsS "$BASE_URL/healthz" >/dev/null

step "Checking readiness"
curl -fsS "$BASE_URL/readyz" >/dev/null

step "Indexing incident evidence"
post_json "/logs" '{"service":"api","level":"ERROR","message":"database timeout while processing checkout request","trace_id":"smoke-timeout-1"}' >/dev/null
post_json "/logs" '{"service":"api","level":"ERROR","message":"connection pool exhausted after recent deploy","trace_id":"smoke-timeout-2"}' >/dev/null

INCIDENT='{"service":"api","query":"database timeout and high latency after deploy","mode":"suggest","actor":"smoke-test"}'

step "Analyzing incident"
ANALYZE_RESPONSE="$(post_json "/incidents/analyze" "$INCIDENT")"
printf "%s" "$ANALYZE_RESPONSE" | grep -q '"database-timeouts"'
printf "%s" "$ANALYZE_RESPONSE" | grep -q '"remediation_plan"'

step "Evaluating policy plan"
PLAN_RESPONSE="$(post_json "/actions/plan" "$INCIDENT")"
printf "%s" "$PLAN_RESPONSE" | grep -q '"kubectl"'
printf "%s" "$PLAN_RESPONSE" | grep -q '"rollout"'
printf "%s" "$PLAN_RESPONSE" | grep -q "requires human approval"

step "Verifying dangerous action is denied"
DENIED_RESPONSE="$(post_json "/actions/execute" '{"action":"get_secret","target":"api","namespace":"ai-platform","approved":true,"dry_run":true,"actor":"smoke-test","reason":"verify secret access is denied"}')"
printf "%s" "$DENIED_RESPONSE" | grep -q '"allowed":false'
printf "%s" "$DENIED_RESPONSE" | grep -q "explicitly denied"

step "Checking audit trail"
AUDIT_RESPONSE="$(curl -fsS "$BASE_URL/audit/events?limit=10")"
printf "%s" "$AUDIT_RESPONSE" | grep -q '"decision":"denied"'
printf "%s" "$AUDIT_RESPONSE" | grep -q '"incident.analyze"'

printf "\nSmoke test passed for %s\n" "$BASE_URL"
