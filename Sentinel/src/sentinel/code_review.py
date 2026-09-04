"""Deterministic review scoring for AI-generated code and coding agents.

The scorer is intentionally small and model-independent. It converts a human
reviewer's dimension scores into a reproducible decision label that can be used
in evaluation notes, calibration tasks, or future CI fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping, Sequence, TypeAlias

ReviewDimension: TypeAlias = Literal[
    "requirement_fit",
    "correctness",
    "security",
    "maintainability",
    "verification",
    "communication",
]
DecisionLabel: TypeAlias = Literal[
    "accept",
    "accept_with_edits",
    "needs_human_design",
    "reject",
]
PreferenceLabel: TypeAlias = Literal["a", "b", "tie"]

DIMENSIONS: tuple[ReviewDimension, ...] = (
    "requirement_fit",
    "correctness",
    "security",
    "maintainability",
    "verification",
    "communication",
)

WEIGHTS: Mapping[ReviewDimension, float] = {
    "requirement_fit": 0.25,
    "correctness": 0.25,
    "security": 0.20,
    "maintainability": 0.15,
    "verification": 0.10,
    "communication": 0.05,
}

MIN_DIMENSION_PASS_SCORE = 0.60
HARD_REJECT_SCORE = 0.25
HARD_REJECT_DIMENSIONS: tuple[ReviewDimension, ...] = ("security",)


@dataclass(frozen=True)
class DimensionScore:
    """One reviewer-assigned score for a rubric dimension."""

    dimension: ReviewDimension
    score: float
    detail: str = ""

    @property
    def passed(self) -> bool:
        """Whether the dimension is acceptable without escalation."""

        return self.score >= MIN_DIMENSION_PASS_SCORE


@dataclass(frozen=True)
class CodeReviewScore:
    """Aggregate score and decision for one code-agent response."""

    score: float
    decision: DecisionLabel
    failing_dimensions: tuple[ReviewDimension, ...]
    hard_failures: tuple[ReviewDimension, ...]
    dimension_scores: tuple[DimensionScore, ...]

    @property
    def passed(self) -> bool:
        """Whether the review result may proceed without redesign."""

        return self.decision in {"accept", "accept_with_edits"}


@dataclass(frozen=True)
class CodeReviewComparison:
    """Deterministic comparison between two code-agent review results."""

    preferred: PreferenceLabel
    reason: str
    a: CodeReviewScore
    b: CodeReviewScore


def _clamp_score(score: float) -> float:
    if score < 0.0 or score > 1.0:
        raise ValueError(f"scores must be in [0.0, 1.0]; got {score:.3f}")
    return score


def _ordered_scores(scores: Sequence[DimensionScore]) -> tuple[DimensionScore, ...]:
    by_dimension: dict[ReviewDimension, DimensionScore] = {}
    for item in scores:
        _clamp_score(item.score)
        if item.dimension in by_dimension:
            raise ValueError(f"duplicate review dimension: {item.dimension}")
        by_dimension[item.dimension] = item

    missing = [dimension for dimension in DIMENSIONS if dimension not in by_dimension]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing review dimensions: {joined}")

    return tuple(by_dimension[dimension] for dimension in DIMENSIONS)


def _decision_label(
    score: float,
    failing_dimensions: Sequence[ReviewDimension],
    hard_failures: Sequence[ReviewDimension],
) -> DecisionLabel:
    if hard_failures:
        return "reject"
    if score >= 0.85 and not failing_dimensions:
        return "accept"
    if score >= 0.72:
        return "accept_with_edits"
    if score >= 0.55:
        return "needs_human_design"
    return "reject"


def score_code_review(scores: Sequence[DimensionScore]) -> CodeReviewScore:
    """Score one code-agent response from normalized rubric dimensions."""

    ordered = _ordered_scores(scores)
    weighted = sum(item.score * WEIGHTS[item.dimension] for item in ordered)
    failing_dimensions = tuple(item.dimension for item in ordered if not item.passed)
    hard_failures = tuple(
        item.dimension
        for item in ordered
        if item.dimension in HARD_REJECT_DIMENSIONS or item.score < HARD_REJECT_SCORE
        if not item.passed
    )
    decision = _decision_label(weighted, failing_dimensions, hard_failures)
    return CodeReviewScore(
        score=round(weighted, 4),
        decision=decision,
        failing_dimensions=failing_dimensions,
        hard_failures=hard_failures,
        dimension_scores=ordered,
    )


def compare_code_reviews(
    a_scores: Sequence[DimensionScore],
    b_scores: Sequence[DimensionScore],
    *,
    margin: float = 0.03,
) -> CodeReviewComparison:
    """Compare two reviewed code-agent responses with safety-aware tie handling."""

    if margin < 0.0 or margin > 1.0:
        raise ValueError("comparison margin must be in [0.0, 1.0]")

    a = score_code_review(a_scores)
    b = score_code_review(b_scores)

    if a.decision == "reject" and b.decision != "reject":
        return CodeReviewComparison("b", "A is rejected while B remains usable.", a, b)
    if b.decision == "reject" and a.decision != "reject":
        return CodeReviewComparison("a", "B is rejected while A remains usable.", a, b)

    delta = a.score - b.score
    if abs(delta) <= margin:
        return CodeReviewComparison("tie", "Scores are within the declared comparison margin.", a, b)
    if delta > 0:
        return CodeReviewComparison("a", "A has the stronger weighted review score.", a, b)
    return CodeReviewComparison("b", "B has the stronger weighted review score.", a, b)
