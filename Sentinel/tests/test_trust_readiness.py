import pytest

from sentinel.trust_readiness import TrustAssessment, score_decision_readiness


def complete_assessments(**overrides: float) -> list[TrustAssessment]:
    values = {
        "evidence": 0.93,
        "clarity": 0.92,
        "risk_disclosure": 0.91,
        "security_boundary": 0.94,
        "stakeholder_empathy": 0.90,
        "value_case": 0.91,
        "reversibility": 0.87,
        "accountability": 0.90,
    }
    values.update(overrides)
    return [TrustAssessment(dimension=key, score=value) for key, value in values.items()]


def test_strong_proposal_is_safe_to_say_yes_to() -> None:
    result = score_decision_readiness(complete_assessments())

    assert result.label == "yes_ready"
    assert result.safe_to_say_yes is True
    assert result.failing_dimensions == ()
    assert result.hard_blockers == ()
    assert result.score >= 0.88
    assert "Evidence must remain inspectable" in result.acceptance_terms[0]


def test_soft_gap_can_proceed_only_with_terms() -> None:
    result = score_decision_readiness(complete_assessments(stakeholder_empathy=0.50))

    assert result.label == "yes_with_terms"
    assert result.safe_to_say_yes is True
    assert result.failing_dimensions == ("stakeholder_empathy",)
    assert any("stakeholder empathy" in term for term in result.acceptance_terms)


def test_security_boundary_hard_block_prevents_yes() -> None:
    result = score_decision_readiness(complete_assessments(security_boundary=0.20))

    assert result.label == "not_ready"
    assert result.safe_to_say_yes is False
    assert result.hard_blockers == ("security_boundary",)
    assert any("Hard blocker" in term for term in result.acceptance_terms)


def test_weak_but_not_blocked_proposal_needs_alignment() -> None:
    result = score_decision_readiness(
        complete_assessments(
            evidence=0.60,
            clarity=0.62,
            stakeholder_empathy=0.55,
            value_case=0.58,
            reversibility=0.57,
        )
    )

    assert result.label == "needs_alignment"
    assert result.safe_to_say_yes is False
    assert "evidence" in result.failing_dimensions


def test_rejects_missing_duplicate_and_out_of_range_scores() -> None:
    with pytest.raises(ValueError, match="missing trust dimensions"):
        score_decision_readiness(complete_assessments()[:-1])

    duplicate = complete_assessments() + [TrustAssessment(dimension="clarity", score=0.80)]
    with pytest.raises(ValueError, match="duplicate trust dimension"):
        score_decision_readiness(duplicate)

    with pytest.raises(ValueError, match="scores must be"):
        score_decision_readiness(complete_assessments(evidence=1.20))
