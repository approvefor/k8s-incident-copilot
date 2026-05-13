from __future__ import annotations

from pathlib import Path
import sys

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from api.ai_provider import get_ai_provider
from api.policy import ActionRequest, evaluate_action
from api.runbooks import search_runbooks


EVAL_PATH = Path(__file__).resolve().parent.parent / "evals" / "incidents.yaml"


def main() -> None:
    suite = yaml.safe_load(EVAL_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []

    for case in suite["evals"]:
        query = case["input"]["query"]
        service = case["input"]["service"]
        expected = case["expected"]

        runbooks = search_runbooks(query, limit=3)
        if not any(match.id == expected["runbook"] for match in runbooks):
            failures.append(f"{case['id']}: expected runbook {expected['runbook']}")

        report = get_ai_provider().analyze(
            {"query": query, "service": service, "logs": []},
            runbooks,
        )
        cause = report.probable_cause.lower()
        for phrase in expected.get("probable_cause_contains", []):
            if phrase.lower() not in cause:
                failures.append(f"{case['id']}: probable cause missing '{phrase}'")

        for action in expected.get("forbidden_actions", []):
            decision = evaluate_action(
                ActionRequest(action=action, target=service, namespace="ai-platform", approved=True)
            )
            if decision.allowed:
                failures.append(f"{case['id']}: forbidden action allowed: {action}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)

    print(f"PASS {len(suite['evals'])} incident evals")


if __name__ == "__main__":
    main()
