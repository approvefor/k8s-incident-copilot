from __future__ import annotations

import os
import random
import time
from datetime import datetime, timezone
from uuid import uuid4

import requests

API_URL = os.getenv("API_URL", "http://api:8000")
INTERVAL_SECONDS = float(os.getenv("INTERVAL_SECONDS", "5"))

SERVICES = ["checkout", "payments", "inventory", "gateway", "auth"]
MESSAGES = [
    ("INFO", "request completed successfully"),
    ("WARNING", "upstream latency above SLO threshold"),
    ("ERROR", "database timeout while processing request"),
    ("ERROR", "redis connection pool exhausted"),
    ("CRITICAL", "payment provider returned repeated 503 responses"),
]


def build_event() -> dict[str, str]:
    level, message = random.choice(MESSAGES)
    return {
        "service": random.choice(SERVICES),
        "level": level,
        "message": message,
        "trace_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    while True:
        event = build_event()
        try:
            response = requests.post(f"{API_URL}/logs", json=event, timeout=5)
            response.raise_for_status()
            print(f"sent {event['level']} log for {event['service']}", flush=True)
        except Exception as exc:
            print(f"failed to send log: {exc}", flush=True)
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
