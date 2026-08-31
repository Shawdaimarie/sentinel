from __future__ import annotations

from sentinel.policy import Policy


def test_default_is_deny_for_undeclared_agent(policy: Policy) -> None:
    decision = policy.evaluate("intruder", "http.get", "https://essentialdigitalsolution.com")
    assert not decision.allowed
    assert "not declared" in decision.reason


def test_action_outside_allowed_set_is_denied(policy: Policy) -> None:
    decision = policy.evaluate("crawler", "fs.write", "reports/x.md")
    assert not decision.allowed


def test_domain_boundary_is_enforced(policy: Policy) -> None:
    allowed = policy.evaluate("crawler", "http.get", "https://essentialdigitalsolution.com/about")
    subdomain = policy.evaluate("crawler", "http.get", "https://www.essentialdigitalsolution.com/")
    foreign = policy.evaluate("crawler", "http.get", "https://example.com/")
    lookalike = policy.evaluate(
        "crawler", "http.get", "https://essentialdigitalsolution.com.evil.io/"
    )
    assert allowed.allowed and subdomain.allowed
    assert not foreign.allowed and not lookalike.allowed


def test_per_run_budget_is_enforced(policy: Policy) -> None:
    target = "https://essentialdigitalsolution.com/"
    for _ in range(20):
        decision = policy.evaluate("prober", "http.head", target)
        assert decision.allowed
        policy.record(decision)
    assert not policy.evaluate("prober", "http.head", target).allowed


def test_denied_actions_do_not_consume_budget(policy: Policy) -> None:
    denied = policy.evaluate("prober", "http.head", "https://example.com/")
    policy.record(denied)
    assert policy.evaluate("prober", "http.head", "https://essentialdigitalsolution.com/").allowed


def test_path_traversal_is_denied(policy: Policy) -> None:
    assert policy.evaluate("reporter", "fs.write", "reports/ok.md").allowed
    assert not policy.evaluate("reporter", "fs.write", "reports/../policy.yaml").allowed
    assert not policy.evaluate("reporter", "fs.write", "/etc/passwd").allowed
