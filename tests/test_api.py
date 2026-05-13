from api.main import embed, healthz
from api.policy import ActionRequest, evaluate_action
from api.runbooks import search_runbooks


def test_embed_is_stable() -> None:
    assert embed("database timeout") == embed("database timeout")
    assert len(embed("database timeout")) == 64


def test_healthz() -> None:
    assert healthz()["status"] == "ok"


def test_runbook_search_finds_database_timeout() -> None:
    matches = search_runbooks("database timeout connection pool", limit=3)
    assert matches
    assert matches[0].id == "database-timeouts"


def test_policy_denies_secret_access() -> None:
    decision = evaluate_action(
        ActionRequest(action="get_secret", target="api", namespace="ai-platform", approved=True)
    )
    assert not decision.allowed


def test_policy_requires_approval_for_scale() -> None:
    decision = evaluate_action(
        ActionRequest(action="scale_deployment", target="api", namespace="ai-platform")
    )
    assert not decision.allowed
    assert decision.requires_approval


def test_policy_allows_approved_dry_run_scale() -> None:
    decision = evaluate_action(
        ActionRequest(
            action="scale_deployment",
            target="ai-platform-ai-platform-api",
            namespace="ai-platform",
            approved=True,
            dry_run=True,
        )
    )
    assert decision.allowed
    assert decision.command[:3] == ["kubectl", "scale", "deployment/ai-platform-ai-platform-api"]
