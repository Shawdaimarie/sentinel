"""Value routing for deployable AI engineering work.

This module connects Sentinel's governed-execution work to a practical delivery
question: which work is ready to publish, pilot, review, hold, or reject? It is
intentionally conservative and keeps human-only decisions outside automation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, TypeAlias

ValueDomain: TypeAlias = Literal[
    "engineering",
    "ai_evaluation",
    "portfolio",
    "client_delivery",
    "operations",
    "finance",
    "identity",
    "legal",
    "assessment",
]
AssetType: TypeAlias = Literal[
    "source_code",
    "documentation",
    "client_workflow",
    "brand",
    "data",
    "assessment_response",
    "legal_document",
]
RouteLane: TypeAlias = Literal[
    "deployable",
    "pilot",
    "human_review",
    "reserved_hold",
    "reject",
]

DOMAINS: tuple[ValueDomain, ...] = (
    "engineering",
    "ai_evaluation",
    "portfolio",
    "client_delivery",
    "operations",
    "finance",
    "identity",
    "legal",
    "assessment",
)
ASSET_TYPES: tuple[AssetType, ...] = (
    "source_code",
    "documentation",
    "client_workflow",
    "brand",
    "data",
    "assessment_response",
    "legal_document",
)
WEIGHTS: Mapping[str, float] = {
    "value": 0.26,
    "evidence": 0.20,
    "security": 0.24,
    "deployment": 0.15,
    "rights": 0.15,
}
HUMAN_ONLY_DOMAINS: frozenset[ValueDomain] = frozenset(
    {"finance", "identity", "legal", "assessment"}
)
HUMAN_ONLY_ASSETS: frozenset[AssetType] = frozenset(
    {"assessment_response", "legal_document"}
)
HARD_SECURITY_GATE = 0.45
HARD_RIGHTS_GATE = 0.55
SOFT_PASS_SCORE = 0.70
DEPLOYABLE_SCORE = 0.85

BASE_TERMS: tuple[str, ...] = (
    "Owner attribution remains Shawdai Marie unless another written agreement applies.",
    "Public proof, private client work, and personal account actions stay separated.",
    "Security, financial, legal, hiring, and identity-sensitive actions remain human-approved.",
)


@dataclass(frozen=True)
class ValueRouteItem:
    """One work item being considered for scaling or external use."""

    id: str
    title: str
    domain: ValueDomain
    asset_type: AssetType
    owner: str
    value_score: float
    evidence_score: float
    security_score: float
    deployment_score: float
    rights_score: float
    contains_sensitive_data: bool = False
    requires_human_approval: bool = False
    external_distribution: bool = False
    notes: str = ""


@dataclass(frozen=True)
class ValueRouteDecision:
    """A scored routing decision and the terms that keep value bounded."""

    item: ValueRouteItem
    score: float
    lane: RouteLane
    blockers: tuple[str, ...]
    required_terms: tuple[str, ...]
    next_actions: tuple[str, ...]

    @property
    def ready_for_public_signal(self) -> bool:
        """Whether the item can be used as external professional proof."""

        return self.lane in {"deployable", "pilot"} and not self.blockers

    @property
    def ready_for_automation(self) -> bool:
        """Whether the item can be advanced without human-only approval."""

        return self.lane == "deployable" and not self.blockers


def _clamp_score(score: float, field: str) -> None:
    if score < 0.0 or score > 1.0:
        raise ValueError(f"{field} must be in [0.0, 1.0]; got {score:.3f}")


def validate_item(item: ValueRouteItem) -> None:
    """Validate value-routing inputs before scoring."""

    if not item.id.strip():
        raise ValueError("item id must not be blank")
    if not item.title.strip():
        raise ValueError(f"{item.id}: title must not be blank")
    if not item.owner.strip():
        raise ValueError(f"{item.id}: owner must not be blank")
    _clamp_score(item.value_score, f"{item.id}.value_score")
    _clamp_score(item.evidence_score, f"{item.id}.evidence_score")
    _clamp_score(item.security_score, f"{item.id}.security_score")
    _clamp_score(item.deployment_score, f"{item.id}.deployment_score")
    _clamp_score(item.rights_score, f"{item.id}.rights_score")


def value_score(item: ValueRouteItem) -> float:
    """Return the weighted value-readiness score for a work item."""

    validate_item(item)
    weighted = (
        item.value_score * WEIGHTS["value"]
        + item.evidence_score * WEIGHTS["evidence"]
        + item.security_score * WEIGHTS["security"]
        + item.deployment_score * WEIGHTS["deployment"]
        + item.rights_score * WEIGHTS["rights"]
    )
    return round(weighted, 4)


def _blockers(item: ValueRouteItem) -> tuple[str, ...]:
    blockers: list[str] = []
    if item.security_score < HARD_SECURITY_GATE:
        blockers.append("security score is below the hard deployment gate")
    if item.rights_score < HARD_RIGHTS_GATE:
        blockers.append("ownership and reuse terms need review")
    if item.contains_sensitive_data and item.external_distribution:
        blockers.append("sensitive data cannot be externally distributed")
    if item.domain in HUMAN_ONLY_DOMAINS:
        blockers.append(f"{item.domain.replace('_', ' ')} requires human approval")
    if item.asset_type in HUMAN_ONLY_ASSETS:
        blockers.append(f"{item.asset_type.replace('_', ' ')} remains human-only")
    if item.requires_human_approval:
        blockers.append("explicit human approval is required before execution")
    return tuple(blockers)


def _lane(item: ValueRouteItem, score: float, blockers: Sequence[str]) -> RouteLane:
    if item.security_score < HARD_SECURITY_GATE:
        return "reject"
    if item.contains_sensitive_data and item.external_distribution:
        return "reject"
    if item.rights_score < HARD_RIGHTS_GATE:
        return "reserved_hold"
    if blockers:
        return "human_review"
    if score >= DEPLOYABLE_SCORE and item.deployment_score >= 0.75:
        return "deployable"
    if score >= SOFT_PASS_SCORE:
        return "pilot"
    if score >= 0.55:
        return "human_review"
    return "reject"


def _next_actions(lane: RouteLane, blockers: Sequence[str]) -> tuple[str, ...]:
    if lane == "deployable":
        return (
            "Publish or reuse as professional proof with source, tests, and limits visible.",
            "Preserve attribution, review evidence, and deployment notes.",
        )
    if lane == "pilot":
        return (
            "Run as a bounded pilot before presenting as a durable delivery pattern.",
            "Add missing tests, metrics, or review notes before broad reuse.",
        )
    if lane == "human_review":
        return tuple(blockers) + (
            "Resolve review items in writing before execution or external distribution.",
        )
    if lane == "reserved_hold":
        return (
            "Keep the asset reserved until ownership and reuse terms are explicit.",
            "Separate public proof from private implementation details.",
        )
    return (
        "Do not deploy, distribute, or reuse this item until the hard blocker is resolved.",
        "Create a remediation issue with owner, risk, and acceptance criteria.",
    )


def route_value_item(item: ValueRouteItem) -> ValueRouteDecision:
    """Score and route one work item through value, security, and ownership gates."""

    score = value_score(item)
    blockers = _blockers(item)
    lane = _lane(item, score, blockers)
    return ValueRouteDecision(
        item=item,
        score=score,
        lane=lane,
        blockers=blockers,
        required_terms=BASE_TERMS,
        next_actions=_next_actions(lane, blockers),
    )


def route_value_items(items: Sequence[ValueRouteItem]) -> list[ValueRouteDecision]:
    """Route a sequence of work items in declared order."""

    ids = [item.id for item in items]
    duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate value route item ids: {', '.join(duplicates)}")
    return [route_value_item(item) for item in items]
