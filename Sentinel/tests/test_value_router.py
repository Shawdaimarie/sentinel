import pytest

from sentinel.value_router import ValueRouteItem, route_value_item, route_value_items


def item(**overrides: object) -> ValueRouteItem:
    values = {
        "id": "sentinel.public-proof",
        "title": "Sentinel public proof layer",
        "domain": "engineering",
        "asset_type": "source_code",
        "owner": "Shawdai Marie",
        "value_score": 0.95,
        "evidence_score": 0.94,
        "security_score": 0.96,
        "deployment_score": 0.90,
        "rights_score": 0.92,
        "contains_sensitive_data": False,
        "requires_human_approval": False,
        "external_distribution": True,
        "notes": "Public proof with tests and documented limits.",
    }
    values.update(overrides)
    return ValueRouteItem(**values)  # type: ignore[arg-type]


def test_high_value_secure_item_is_deployable_signal() -> None:
    result = route_value_item(item())

    assert result.lane == "deployable"
    assert result.ready_for_public_signal is True
    assert result.ready_for_automation is True
    assert result.blockers == ()
    assert result.score >= 0.85
    assert "Owner attribution" in result.required_terms[0]


def test_medium_value_item_routes_to_pilot() -> None:
    result = route_value_item(
        item(value_score=0.72, evidence_score=0.73, security_score=0.74, deployment_score=0.70)
    )

    assert result.lane == "pilot"
    assert result.ready_for_public_signal is True
    assert result.ready_for_automation is False


def test_unclear_reuse_terms_hold_reserved_asset() -> None:
    result = route_value_item(item(rights_score=0.40))

    assert result.lane == "reserved_hold"
    assert result.ready_for_public_signal is False
    assert "ownership and reuse terms need review" in result.blockers


def test_human_only_domain_requires_human_review() -> None:
    result = route_value_item(item(domain="legal", asset_type="legal_document"))

    assert result.lane == "human_review"
    assert result.ready_for_public_signal is False
    assert any("human approval" in blocker for blocker in result.blockers)


def test_low_security_or_sensitive_external_distribution_rejects() -> None:
    low_security = route_value_item(item(security_score=0.20))
    sensitive = route_value_item(item(contains_sensitive_data=True, external_distribution=True))

    assert low_security.lane == "reject"
    assert sensitive.lane == "reject"
    assert sensitive.ready_for_automation is False


def test_rejects_duplicate_ids_and_invalid_scores() -> None:
    with pytest.raises(ValueError, match="duplicate value route item ids"):
        route_value_items([item(), item()])

    with pytest.raises(ValueError, match="value_score must be"):
        route_value_item(item(value_score=1.10))
