import pytest

from sentinel.code_review import DimensionScore, compare_code_reviews, score_code_review


def complete_scores(**overrides: float) -> list[DimensionScore]:
    values = {
        "requirement_fit": 0.90,
        "correctness": 0.90,
        "security": 0.90,
        "maintainability": 0.88,
        "verification": 0.86,
        "communication": 0.86,
    }
    values.update(overrides)
    return [DimensionScore(dimension=key, score=value) for key, value in values.items()]


def test_accepts_strong_review_with_all_dimensions_passing() -> None:
    result = score_code_review(complete_scores())

    assert result.decision == "accept"
    assert result.passed is True
    assert result.failing_dimensions == ()
    assert result.hard_failures == ()
    assert result.score >= 0.85


def test_security_failure_is_a_hard_reject_even_with_strong_other_scores() -> None:
    result = score_code_review(complete_scores(security=0.20))

    assert result.decision == "reject"
    assert result.passed is False
    assert result.hard_failures == ("security",)


def test_mid_quality_review_requires_human_design_when_too_weak_for_edits() -> None:
    result = score_code_review(
        complete_scores(requirement_fit=0.62, correctness=0.60, verification=0.40)
    )

    assert result.decision == "needs_human_design"
    assert "verification" in result.failing_dimensions


def test_rejects_missing_or_duplicate_dimensions() -> None:
    with pytest.raises(ValueError, match="missing review dimensions"):
        score_code_review(complete_scores()[:-1])

    duplicate = complete_scores() + [DimensionScore(dimension="security", score=0.95)]
    with pytest.raises(ValueError, match="duplicate review dimension"):
        score_code_review(duplicate)


def test_comparison_prefers_usable_answer_over_security_reject() -> None:
    comparison = compare_code_reviews(
        complete_scores(security=0.20),
        complete_scores(requirement_fit=0.80, correctness=0.78),
    )

    assert comparison.preferred == "b"
    assert comparison.a.decision == "reject"
    assert comparison.b.passed is True


def test_comparison_treats_small_score_gap_as_tie() -> None:
    comparison = compare_code_reviews(
        complete_scores(requirement_fit=0.86),
        complete_scores(requirement_fit=0.84),
        margin=0.03,
    )

    assert comparison.preferred == "tie"
