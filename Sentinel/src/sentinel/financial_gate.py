"""Deterministic compliance gate for AI-generated financial and market content.

Financial decisions are a declared human-only boundary in Sentinel's value
router (see ``docs/VALUE_ROUTE_GATEWAY.md``). This module turns that boundary
into a testable, deterministic gate: it scores whether AI-agent-produced
financial or market commentary is grounded, disclosed, and free of
personalized advice before a human makes the release decision.

The gate does not give financial advice, predict markets, execute trades, or
authorize autonomous publication. Its strongest outcome routes content to the
required human release decision; it never replaces that decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

FinancialDimension: TypeAlias = Literal[
    "grounding",
    "advice_boundary",
    "disclosure",
    "data_sensitivity",
    "recency",
    "clarity",
]
DecisionLabel: TypeAlias = Literal[
    "ready_for_human_release",
    "release_with_edits",
    "needs_human_design",
    "reject",
]
CriticalFinding: TypeAlias = Literal[
    "personalized_trade_directive",
    "guaranteed_return_claim",
    "unlicensed_advisor_claim",
    "fabricated_financial_data",
    "sensitive_data_exposure",
    "missing_required_disclosure",
]
ReviewerAction: TypeAlias = Literal[
    "route_to_human_release_decision",
    "edit_and_reverify",
    "pause_for_human_design",
    "do_not_publish",
]

DIMENSIONS: tuple[FinancialDimension, ...] = (
    "grounding",
    "advice_boundary",
    "disclosure",
    "data_sensitivity",
    "recency",
    "clarity",
)

CRITICAL_FINDINGS: tuple[CriticalFinding, ...] = (
    "personalized_trade_directive",
    "guaranteed_return_claim",
    "unlicensed_advisor_claim",
    "fabricated_financial_data",
    "sensitive_data_exposure",
    "missing_required_disclosure",
)

WEIGHTS: Mapping[FinancialDimension, float] = {
    "grounding": 0.30,
    "advice_boundary": 0.25,
    "disclosure": 0.15,
    "data_sensitivity": 0.15,
    "recency": 0.10,
    "clarity": 0.05,
}

REVIEWER_ACTIONS: Mapping[DecisionLabel, ReviewerAction] = {
    "ready_for_human_release": "route_to_human_release_decision",
    "release_with_edits": "edit_and_reverify",
    "needs_human_design": "pause_for_human_design",
    "reject": "do_not_publish",
}

REVIEWER_ACTION_TEXT: Mapping[ReviewerAction, str] = {
    "route_to_human_release_decision": (
        "Deterministic checks passed. Route to the required human financial-"
        "release decision before publication; this gate does not authorize "
        "release on its own."
    ),
    "edit_and_reverify": (
        "Apply the required edits, rerun the gate, and route to human release "
        "review."
    ),
    "pause_for_human_design": (
        "Pause release and resolve the missing grounding, disclosure, or scope "
        "boundary before continuing."
    ),
    "do_not_publish": (
        "Do not publish the content; document the decisive failure and replace "
        "it."
    ),
}

MIN_DIMENSION_PASS_SCORE = 0.60
HARD_REJECT_SCORE = 0.25
HARD_REJECT_DIMENSIONS: tuple[FinancialDimension, ...] = (
    "advice_boundary",
    "data_sensitivity",
)


@dataclass(frozen=True)
class DimensionScore:
    """One reviewer-assigned score for a financial-content rubric dimension."""

    dimension: FinancialDimension
    score: float
    detail: str = ""

    @property
    def passed(self) -> bool:
        """Whether the dimension is acceptable without escalation."""

        return self.score >= MIN_DIMENSION_PASS_SCORE


@dataclass(frozen=True)
class FinancialContentScore:
    """Aggregate score and deterministic disposition for one content item."""

    score: float
    decision: DecisionLabel
    reviewer_action: ReviewerAction
    reviewer_action_text: str
    failing_dimensions: tuple[FinancialDimension, ...]
    hard_failures: tuple[FinancialDimension, ...]
    critical_findings: tuple[CriticalFinding, ...]
    decisive_failure_modes: tuple[str, ...]
    dimension_scores: tuple[DimensionScore, ...]

    @property
    def passed(self) -> bool:
        """Whether the content may be routed to human release review."""

        return self.decision in {"ready_for_human_release", "release_with_edits"}


def _clamp_score(score: float) -> float:
    if score < 0.0 or score > 1.0:
        raise ValueError(f"scores must be in [0.0, 1.0]; got {score:.3f}")
    return score


def _ordered_scores(scores: Sequence[DimensionScore]) -> tuple[DimensionScore, ...]:
    by_dimension: dict[FinancialDimension, DimensionScore] = {}
    for item in scores:
        _clamp_score(item.score)
        if item.dimension in by_dimension:
            raise ValueError(f"duplicate financial dimension: {item.dimension}")
        by_dimension[item.dimension] = item

    missing = [dimension for dimension in DIMENSIONS if dimension not in by_dimension]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing financial dimensions: {joined}")

    return tuple(by_dimension[dimension] for dimension in DIMENSIONS)


def _ordered_critical_findings(findings: Sequence[str]) -> tuple[CriticalFinding, ...]:
    normalized: list[CriticalFinding] = []
    seen: set[str] = set()
    for finding in findings:
        if finding not in CRITICAL_FINDINGS:
            joined = ", ".join(CRITICAL_FINDINGS)
            raise ValueError(f"unknown critical finding {finding!r}; expected one of: {joined}")
        if finding in seen:
            raise ValueError(f"duplicate critical finding: {finding}")
        seen.add(finding)
        normalized.append(finding)
    return tuple(normalized)


def _decision_label(
    score: float,
    failing_dimensions: Sequence[FinancialDimension],
    hard_failures: Sequence[FinancialDimension],
    critical_findings: Sequence[CriticalFinding],
) -> DecisionLabel:
    if hard_failures or critical_findings:
        return "reject"
    if score >= 0.85 and not failing_dimensions:
        return "ready_for_human_release"
    if score >= 0.72:
        return "release_with_edits"
    if score >= 0.55:
        return "needs_human_design"
    return "reject"


def _decisive_failure_modes(
    failing_dimensions: Sequence[FinancialDimension],
    hard_failures: Sequence[FinancialDimension],
    critical_findings: Sequence[CriticalFinding],
) -> tuple[str, ...]:
    modes = [f"critical:{finding}" for finding in critical_findings]
    modes.extend(f"dimension:{dimension}" for dimension in hard_failures)
    if not modes:
        modes.extend(f"dimension:{dimension}" for dimension in failing_dimensions)
    return tuple(dict.fromkeys(modes))


def score_financial_content(
    scores: Sequence[DimensionScore],
    *,
    critical_findings: Sequence[str] = (),
) -> FinancialContentScore:
    """Score one AI-generated financial or market content item.

    Explicit critical findings are independent hard gates. This prevents a
    polished, well-grounded item from averaging away a personalized trade
    directive, a guaranteed-return claim, or exposed account data. The
    strongest possible decision, ``ready_for_human_release``, still requires a
    human to make the actual financial-release decision; this function never
    authorizes autonomous publication.
    """

    ordered = _ordered_scores(scores)
    normalized_findings = _ordered_critical_findings(critical_findings)
    weighted = sum(item.score * WEIGHTS[item.dimension] for item in ordered)
    failing_dimensions = tuple(item.dimension for item in ordered if not item.passed)
    hard_failures = tuple(
        item.dimension
        for item in ordered
        if not item.passed
        and (item.dimension in HARD_REJECT_DIMENSIONS or item.score < HARD_REJECT_SCORE)
    )
    decision = _decision_label(
        weighted,
        failing_dimensions,
        hard_failures,
        normalized_findings,
    )
    reviewer_action = REVIEWER_ACTIONS[decision]
    return FinancialContentScore(
        score=round(weighted, 4),
        decision=decision,
        reviewer_action=reviewer_action,
        reviewer_action_text=REVIEWER_ACTION_TEXT[reviewer_action],
        failing_dimensions=failing_dimensions,
        hard_failures=hard_failures,
        critical_findings=normalized_findings,
        decisive_failure_modes=_decisive_failure_modes(
            failing_dimensions,
            hard_failures,
            normalized_findings,
        ),
        dimension_scores=ordered,
    )
