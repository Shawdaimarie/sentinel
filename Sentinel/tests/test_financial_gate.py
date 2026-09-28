import pytest

from sentinel.financial_gate import DimensionScore, score_financial_content


def complete_scores(**overrides: float) -> list[DimensionScore]:
    values = {
        "grounding": 0.90,
        "advice_boundary": 0.90,
        "disclosure": 0.88,
        "data_sensitivity": 0.90,
        "recency": 0.86,
        "clarity": 0.86,
    }
    values.update(overrides)
    return [DimensionScore(dimension=key, score=value) for key, value in values.items()]


def test_routes_strong_content_to_human_release_review() -> None:
    result = score_financial_content(complete_scores())

    assert result.decision == "ready_for_human_release"
    assert result.reviewer_action == "route_to_human_release_decision"
    assert "human" in result.reviewer_action_text.lower()
    assert result.passed is True
    assert result.failing_dimensions == ()
    assert result.hard_failures == ()
    assert result.score >= 0.85


def test_weak_advice_boundary_is_a_hard_reject_even_with_strong_other_scores() -> None:
    result = score_financial_content(complete_scores(advice_boundary=0.20))

    assert result.decision == "reject"
    assert result.passed is False
    assert result.hard_failures == ("advice_boundary",)


def test_weak_data_sensitivity_is_a_hard_reject() -> None:
    result = score_financial_content(complete_scores(data_sensitivity=0.15))

    assert result.decision == "reject"
    assert result.hard_failures == ("data_sensitivity",)


def test_explicit_critical_finding_forces_reject_despite_high_score() -> None:
    result = score_financial_content(
        complete_scores(),
        critical_findings=["personalized_trade_directive"],
    )

    assert result.decision == "reject"
    assert result.reviewer_action == "do_not_publish"
    assert "critical:personalized_trade_directive" in result.decisive_failure_modes


def test_mid_quality_content_requires_human_design_when_too_weak_for_edits() -> None:
    result = score_financial_content(
        complete_scores(grounding=0.35, disclosure=0.55, clarity=0.50)
    )

    assert result.decision == "needs_human_design"
    assert "grounding" in result.failing_dimensions


def test_stale_data_alone_routes_to_release_with_edits() -> None:
    result = score_financial_content(complete_scores(recency=0.30))

    assert result.decision == "release_with_edits"
    assert result.reviewer_action == "edit_and_reverify"
    assert "recency" in result.failing_dimensions
    assert "recency" not in result.hard_failures


def test_rejects_missing_or_duplicate_dimensions() -> None:
    with pytest.raises(ValueError, match="missing financial dimensions"):
        score_financial_content(complete_scores()[:-1])

    duplicate = complete_scores() + [DimensionScore(dimension="advice_boundary", score=0.95)]
    with pytest.raises(ValueError, match="duplicate financial dimension"):
        score_financial_content(duplicate)


def test_rejects_unknown_or_duplicate_critical_findings() -> None:
    with pytest.raises(ValueError, match="unknown critical finding"):
        score_financial_content(complete_scores(), critical_findings=["market_crash"])

    with pytest.raises(ValueError, match="duplicate critical finding"):
        score_financial_content(
            complete_scores(),
            critical_findings=["guaranteed_return_claim", "guaranteed_return_claim"],
        )


def test_rejects_out_of_range_scores() -> None:
    with pytest.raises(ValueError, match="scores must be in"):
        score_financial_content(complete_scores(grounding=1.5))
