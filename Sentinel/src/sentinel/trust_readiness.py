"""Decision-readiness scoring for trust-centered AI engineering communication.

This module turns the question "Is this safe and clear enough to say yes to?"
into an explicit, reproducible review artifact. It does not replace human
judgment; it makes the required evidence, boundaries, values, and stakeholder
care visible before a decision is accepted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

TrustDimension: TypeAlias = Literal[
    "evidence",
    "clarity",
    "risk_disclosure",
    "security_boundary",
    "stakeholder_empathy",
    "value_case",
    "reversibility",
    "accountability",
]
ReadinessLabel: TypeAlias = Literal[
    "yes_ready",
    "yes_with_terms",
    "needs_alignment",
    "not_ready",
]

DIMENSIONS: tuple[TrustDimension, ...] = (
    "evidence",
    "clarity",
    "risk_disclosure",
    "security_boundary",
    "stakeholder_empathy",
    "value_case",
    "reversibility",
    "accountability",
)

WEIGHTS: Mapping[TrustDimension, float] = {
    "evidence": 0.18,
    "clarity": 0.14,
    "risk_disclosure": 0.15,
    "security_boundary": 0.16,
    "stakeholder_empathy": 0.12,
    "value_case": 0.12,
    "reversibility": 0.06,
    "accountability": 0.07,
}

MIN_DIMENSION_PASS_SCORE = 0.65
HARD_BLOCK_SCORE = 0.35
HARD_BLOCK_DIMENSIONS: tuple[TrustDimension, ...] = (
    "risk_disclosure",
    "security_boundary",
    "accountability",
)

BASE_ACCEPTANCE_TERMS: tuple[str, ...] = (
    "Evidence must remain inspectable and connected to the claim being made.",
    "Security, privacy, legal, financial, and identity-sensitive actions remain human-approved.",
    "Success metrics, ownership, and escalation paths must be explicit before execution.",
)


@dataclass(frozen=True)
class TrustAssessment:
    """One reviewer-assigned score for a decision-readiness dimension."""

    dimension: TrustDimension
    score: float
    note: str = ""

    @property
    def passed(self) -> bool:
        """Whether the dimension clears the minimum confidence threshold."""

        return self.score >= MIN_DIMENSION_PASS_SCORE


@dataclass(frozen=True)
class DecisionReadiness:
    """Aggregate decision-readiness result and acceptance terms."""

    score: float
    label: ReadinessLabel
    failing_dimensions: tuple[TrustDimension, ...]
    hard_blockers: tuple[TrustDimension, ...]
    assessments: tuple[TrustAssessment, ...]
    acceptance_terms: tuple[str, ...]

    @property
    def safe_to_say_yes(self) -> bool:
        """Whether a decision can proceed without violating the trust standard."""

        return self.label in {"yes_ready", "yes_with_terms"}


def _clamp_score(score: float) -> float:
    if score < 0.0 or score > 1.0:
        raise ValueError(f"scores must be in [0.0, 1.0]; got {score:.3f}")
    return score


def _ordered_assessments(
    assessments: Sequence[TrustAssessment],
) -> tuple[TrustAssessment, ...]:
    by_dimension: dict[TrustDimension, TrustAssessment] = {}
    for item in assessments:
        _clamp_score(item.score)
        if item.dimension in by_dimension:
            raise ValueError(f"duplicate trust dimension: {item.dimension}")
        by_dimension[item.dimension] = item

    missing = [dimension for dimension in DIMENSIONS if dimension not in by_dimension]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing trust dimensions: {joined}")

    return tuple(by_dimension[dimension] for dimension in DIMENSIONS)


def _readiness_label(
    score: float,
    failing_dimensions: Sequence[TrustDimension],
    hard_blockers: Sequence[TrustDimension],
) -> ReadinessLabel:
    if hard_blockers:
        return "not_ready"
    if score >= 0.88 and not failing_dimensions:
        return "yes_ready"
    if score >= 0.78:
        return "yes_with_terms"
    if score >= 0.58:
        return "needs_alignment"
    return "not_ready"


def _acceptance_terms(
    label: ReadinessLabel,
    failing_dimensions: Sequence[TrustDimension],
    hard_blockers: Sequence[TrustDimension],
) -> tuple[str, ...]:
    terms = list(BASE_ACCEPTANCE_TERMS)
    if label == "yes_ready":
        terms.append("Proceed while preserving evidence, auditability, and stakeholder visibility.")
    if label == "yes_with_terms":
        for dimension in failing_dimensions:
            terms.append(f"Improve {dimension.replace('_', ' ')} before expanding scope.")
    if label in {"needs_alignment", "not_ready"}:
        terms.append("Do not ask for acceptance until the open concerns are resolved in writing.")
    for dimension in hard_blockers:
        terms.append(f"Hard blocker: {dimension.replace('_', ' ')} is below the trust threshold.")
    return tuple(terms)


def score_decision_readiness(
    assessments: Sequence[TrustAssessment],
) -> DecisionReadiness:
    """Score whether a proposal is safe, clear, and principled enough to accept."""

    ordered = _ordered_assessments(assessments)
    weighted = sum(item.score * WEIGHTS[item.dimension] for item in ordered)
    failing_dimensions = tuple(item.dimension for item in ordered if not item.passed)
    hard_blockers = tuple(
        item.dimension
        for item in ordered
        if item.dimension in HARD_BLOCK_DIMENSIONS and item.score < HARD_BLOCK_SCORE
    )
    label = _readiness_label(weighted, failing_dimensions, hard_blockers)
    return DecisionReadiness(
        score=round(weighted, 4),
        label=label,
        failing_dimensions=failing_dimensions,
        hard_blockers=hard_blockers,
        assessments=ordered,
        acceptance_terms=_acceptance_terms(label, failing_dimensions, hard_blockers),
    )
