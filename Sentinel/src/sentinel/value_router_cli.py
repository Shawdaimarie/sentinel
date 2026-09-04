"""Command-line reports for the Sentinel value route gateway."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from sentinel.value_router import (
    ASSET_TYPES,
    DOMAINS,
    AssetType,
    RouteLane,
    ValueDomain,
    ValueRouteDecision,
    ValueRouteItem,
    route_value_items,
)

LANES: tuple[RouteLane, ...] = (
    "deployable",
    "pilot",
    "human_review",
    "reserved_hold",
    "reject",
)


def _require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return cast(Mapping[str, object], value)


def _require_text(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{context} must not be blank")
    return normalized


def _require_bool(value: object, context: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{context} must be a boolean")
    return value


def _require_score(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be a number in [0.0, 1.0]")
    score = float(value)
    if score < 0.0 or score > 1.0:
        raise ValueError(f"{context} must be in [0.0, 1.0]")
    return score


def _optional_text(value: object, context: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string when provided")
    return value.strip()


def _domain(value: str) -> ValueDomain:
    if value not in DOMAINS:
        raise ValueError(f"unknown domain {value!r}; expected one of: {', '.join(DOMAINS)}")
    return value


def _asset_type(value: str) -> AssetType:
    if value not in ASSET_TYPES:
        expected = ", ".join(ASSET_TYPES)
        raise ValueError(f"unknown asset type {value!r}; expected one of: {expected}")
    return value


def item_from_mapping(raw: Mapping[str, object]) -> ValueRouteItem:
    """Convert a JSON object into a validated value route item."""

    item_id = _require_text(raw.get("id"), "id")
    return ValueRouteItem(
        id=item_id,
        title=_require_text(raw.get("title"), f"{item_id}.title"),
        domain=_domain(_require_text(raw.get("domain"), f"{item_id}.domain")),
        asset_type=_asset_type(_require_text(raw.get("asset_type"), f"{item_id}.asset_type")),
        owner=_require_text(raw.get("owner"), f"{item_id}.owner"),
        value_score=_require_score(raw.get("value_score"), f"{item_id}.value_score"),
        evidence_score=_require_score(raw.get("evidence_score"), f"{item_id}.evidence_score"),
        security_score=_require_score(raw.get("security_score"), f"{item_id}.security_score"),
        deployment_score=_require_score(raw.get("deployment_score"), f"{item_id}.deployment_score"),
        rights_score=_require_score(raw.get("rights_score"), f"{item_id}.rights_score"),
        contains_sensitive_data=_require_bool(
            raw.get("contains_sensitive_data", False), f"{item_id}.contains_sensitive_data"
        ),
        requires_human_approval=_require_bool(
            raw.get("requires_human_approval", False), f"{item_id}.requires_human_approval"
        ),
        external_distribution=_require_bool(
            raw.get("external_distribution", False), f"{item_id}.external_distribution"
        ),
        notes=_optional_text(raw.get("notes"), f"{item_id}.notes"),
    )


def load_items(path: Path) -> list[ValueRouteItem]:
    """Load a JSON array of value route items."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("value route input must be a JSON array")
    return [
        item_from_mapping(_require_mapping(item, f"item {index}"))
        for index, item in enumerate(data, 1)
    ]


def decision_record(decision: ValueRouteDecision) -> dict[str, object]:
    """Return a JSON-serializable record for one route decision."""

    return {
        "id": decision.item.id,
        "title": decision.item.title,
        "owner": decision.item.owner,
        "domain": decision.item.domain,
        "asset_type": decision.item.asset_type,
        "score": decision.score,
        "lane": decision.lane,
        "ready_for_public_signal": decision.ready_for_public_signal,
        "ready_for_automation": decision.ready_for_automation,
        "blockers": list(decision.blockers),
        "required_terms": list(decision.required_terms),
        "next_actions": list(decision.next_actions),
        "notes": decision.item.notes,
    }


def result_payload(
    decisions: Sequence[ValueRouteDecision],
    *,
    min_score: float,
) -> dict[str, object]:
    """Build a deterministic report payload for route decisions."""

    rejected = [decision.item.id for decision in decisions if decision.lane == "reject"]
    below_threshold = [decision.item.id for decision in decisions if decision.score < min_score]
    return {
        "schema_version": "sentinel.value_route.v1",
        "min_score": min_score,
        "passed": not rejected and not below_threshold,
        "rejected": rejected,
        "below_threshold": below_threshold,
        "results": [decision_record(decision) for decision in decisions],
    }


def markdown_report(decisions: Sequence[ValueRouteDecision], *, min_score: float) -> str:
    """Render route decisions as a compact Markdown report."""

    lines = [
        "# Sentinel Value Route Gateway Report",
        "",
        f"Minimum score: `{min_score:.2f}`",
        "",
        "| Item | Domain | Asset | Score | Lane | Public signal | Automation |",
        "|---|---|---|---:|---|---:|---:|",
    ]
    for decision in decisions:
        lines.append(
            "| {title} | {domain} | {asset} | {score:.4f} | {lane} | {public} | {auto} |".format(
                title=decision.item.title,
                domain=decision.item.domain,
                asset=decision.item.asset_type,
                score=decision.score,
                lane=decision.lane,
                public="yes" if decision.ready_for_public_signal else "no",
                auto="yes" if decision.ready_for_automation else "no",
            )
        )
    lines.append("")
    for decision in decisions:
        lines.append(f"## {decision.item.id}")
        lines.append("")
        lines.append(f"Lane: `{decision.lane}`")
        lines.append("")
        if decision.blockers:
            lines.append("Blockers:")
            for blocker in decision.blockers:
                lines.append(f"- {blocker}")
            lines.append("")
        lines.append("Next actions:")
        for action in decision.next_actions:
            lines.append(f"- {action}")
        lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Route value-bearing AI engineering work through security and ownership gates."
    )
    parser.add_argument("--items", required=True, type=Path, help="Path to a JSON item array.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON report path.")
    parser.add_argument("--markdown-out", type=Path, help="Optional Markdown report path.")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Fail when any item score falls below this threshold.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.min_score < 0.0 or args.min_score > 1.0:
            raise ValueError("--min-score must be in [0.0, 1.0]")
        decisions = route_value_items(load_items(args.items))
    except ValueError as exc:
        parser.error(str(exc))

    payload = result_payload(decisions, min_score=args.min_score)
    json_text = json.dumps(payload, indent=2, sort_keys=True)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)

    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        report = markdown_report(decisions, min_score=args.min_score)
        args.markdown_out.write_text(report, encoding="utf-8")

    return 0 if payload["passed"] is True else 1


if __name__ == "__main__":
    sys.exit(main())
