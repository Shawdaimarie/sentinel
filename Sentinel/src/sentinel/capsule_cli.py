"""Command-line interface for Sentinel deployment capsule manifests."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from sentinel.capsule import (
    ASSET_TYPES,
    VISIBILITIES,
    CapsuleAsset,
    CapsuleAssetType,
    CapsuleVisibility,
    DeploymentCapsule,
    capsule_manifest_payload,
    build_capsule_manifests,
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


def _optional_text(value: object, context: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string when provided")
    return value.strip()


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


def _visibility(value: str) -> CapsuleVisibility:
    if value not in VISIBILITIES:
        expected = ", ".join(VISIBILITIES)
        raise ValueError(f"unknown visibility {value!r}; expected one of: {expected}")
    return value


def _asset_type(value: str) -> CapsuleAssetType:
    if value not in ASSET_TYPES:
        expected = ", ".join(ASSET_TYPES)
        raise ValueError(f"unknown asset type {value!r}; expected one of: {expected}")
    return value


def _asset_from_mapping(raw: Mapping[str, object], context: str) -> CapsuleAsset:
    return CapsuleAsset(
        path=_require_text(raw.get("path"), f"{context}.path"),
        asset_type=_asset_type(_require_text(raw.get("asset_type"), f"{context}.asset_type")),
        required=_require_bool(raw.get("required", True), f"{context}.required"),
        description=_optional_text(raw.get("description"), f"{context}.description"),
    )


def _assets_from_value(value: object, context: str) -> tuple[CapsuleAsset, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return tuple(
        _asset_from_mapping(_require_mapping(item, f"{context}[{index}]"), f"{context}[{index}]")
        for index, item in enumerate(value, 1)
    )


def capsule_from_mapping(raw: Mapping[str, object]) -> DeploymentCapsule:
    """Convert a JSON object into a validated deployment capsule."""

    capsule_id = _require_text(raw.get("id"), "id")
    return DeploymentCapsule(
        id=capsule_id,
        title=_require_text(raw.get("title"), f"{capsule_id}.title"),
        owner=_require_text(raw.get("owner"), f"{capsule_id}.owner"),
        visibility=_visibility(_require_text(raw.get("visibility"), f"{capsule_id}.visibility")),
        license_expression=_require_text(
            raw.get("license_expression"), f"{capsule_id}.license_expression"
        ),
        summary=_require_text(raw.get("summary"), f"{capsule_id}.summary"),
        assets=_assets_from_value(raw.get("assets", []), f"{capsule_id}.assets"),
        value_score=_require_score(raw.get("value_score"), f"{capsule_id}.value_score"),
        evidence_score=_require_score(raw.get("evidence_score"), f"{capsule_id}.evidence_score"),
        security_score=_require_score(raw.get("security_score"), f"{capsule_id}.security_score"),
        deployability_score=_require_score(
            raw.get("deployability_score"), f"{capsule_id}.deployability_score"
        ),
        rights_score=_require_score(raw.get("rights_score"), f"{capsule_id}.rights_score"),
        public_distribution=_require_bool(
            raw.get("public_distribution", False), f"{capsule_id}.public_distribution"
        ),
        includes_sensitive_data=_require_bool(
            raw.get("includes_sensitive_data", False), f"{capsule_id}.includes_sensitive_data"
        ),
        requires_client_terms=_require_bool(
            raw.get("requires_client_terms", False), f"{capsule_id}.requires_client_terms"
        ),
    )


def load_capsules(path: Path) -> list[DeploymentCapsule]:
    """Load a JSON array of deployment capsules."""

    data: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("capsule input must be a JSON array")
    return [
        capsule_from_mapping(_require_mapping(item, f"capsule {index}"))
        for index, item in enumerate(data, 1)
    ]


def result_payload(
    manifests: Sequence[object],
    *,
    min_score: float,
) -> dict[str, object]:
    """Build a report payload for capsule manifests."""

    manifest_payloads = [capsule_manifest_payload(manifest) for manifest in manifests]
    blocked = [str(item["id"]) for item in manifest_payloads if item["status"] == "blocked"]
    below_threshold = [
        str(item["id"])
        for item in manifest_payloads
        if isinstance(item["score"], (int, float)) and float(item["score"]) < min_score
    ]
    return {
        "schema_version": "sentinel.deployment_capsule_report.v1",
        "min_score": min_score,
        "passed": not blocked and not below_threshold,
        "blocked": blocked,
        "below_threshold": below_threshold,
        "manifests": manifest_payloads,
    }


def markdown_report(manifests: Sequence[object], *, min_score: float) -> str:
    """Render deployment capsule manifests as Markdown."""

    rows = [capsule_manifest_payload(manifest) for manifest in manifests]
    lines = [
        "# Sentinel Deployment Capsule Report",
        "",
        f"Minimum score: `{min_score:.2f}`",
        "",
        "| Capsule | Visibility | Score | Status | External signal | Manifest SHA-256 |",
        "|---|---|---:|---|---:|---|",
    ]
    for item in rows:
        external_signal = "yes" if item["status"] == "ready" and item["visibility"] == "public_proof" else "no"
        lines.append(
            "| {title} | {visibility} | {score:.4f} | {status} | {signal} | `{sha}` |".format(
                title=item["title"],
                visibility=item["visibility"],
                score=float(item["score"]),
                status=item["status"],
                signal=external_signal,
                sha=item["manifest_sha256"],
            )
        )
    lines.append("")
    for item in rows:
        lines.append(f"## {item['id']}")
        lines.append("")
        blockers = item["blockers"]
        if isinstance(blockers, list) and blockers:
            lines.append("Blockers:")
            for blocker in blockers:
                lines.append(f"- {blocker}")
            lines.append("")
        next_actions = item["next_actions"]
        lines.append("Next actions:")
        if isinstance(next_actions, list):
            for action in next_actions:
                lines.append(f"- {action}")
        lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build protected deployment capsule manifests for Sentinel proof assets."
    )
    parser.add_argument("--capsules", required=True, type=Path, help="Path to capsule JSON.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Root used for asset hashing.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON report path.")
    parser.add_argument("--markdown-out", type=Path, help="Optional Markdown report path.")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Fail when any capsule score falls below this threshold.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.min_score < 0.0 or args.min_score > 1.0:
            raise ValueError("--min-score must be in [0.0, 1.0]")
        capsules = load_capsules(args.capsules)
        manifests = build_capsule_manifests(capsules, root=args.root)
    except ValueError as exc:
        parser.error(str(exc))

    payload = result_payload(manifests, min_score=args.min_score)
    json_text = json.dumps(payload, indent=2, sort_keys=True)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)

    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown_report(manifests, min_score=args.min_score), encoding="utf-8")

    return 0 if payload["passed"] is True else 1


if __name__ == "__main__":
    sys.exit(main())
