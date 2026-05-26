#!/usr/bin/env sh
set -eu

BASE_URL="${API_URL:-http://localhost:8000}"
PYTHON_BIN="${PYTHON:-}"

if [ -z "$PYTHON_BIN" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

can_reach_api() {
  API_URL="$BASE_URL" "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import os
import urllib.request

base_url = os.environ["API_URL"]
urllib.request.urlopen(f"{base_url}/healthz", timeout=3).read()
PY
}

docker_fallback() {
  if [ "${SMOKE_DOCKER_FALLBACK:-1}" != "1" ] || ! command -v docker >/dev/null 2>&1; then
    return 1
  fi

  if docker compose version >/dev/null 2>&1; then
    API_CONTAINER="$(docker compose ps -q api 2>/dev/null || true)"
  elif command -v docker-compose >/dev/null 2>&1; then
    API_CONTAINER="$(docker-compose ps -q api 2>/dev/null || true)"
  else
    API_CONTAINER=""
  fi

  if [ -z "$API_CONTAINER" ]; then
    return 1
  fi

  docker exec -i -e API_URL=http://127.0.0.1:8000 "$API_CONTAINER" python - < scripts/smoke.py
}

if can_reach_api; then
  API_URL="$BASE_URL" "$PYTHON_BIN" scripts/smoke.py
elif docker_fallback; then
  exit 0
else
  echo "Smoke test could not reach $BASE_URL."
  echo "Start the stack with 'make compose-up' or reset stale local state with 'make compose-reset'."
  exit 1
fi
