"""Deployment capsule manifests for protected AI engineering proof.

A deployment capsule is a small, reproducible package description that connects
public proof, private delivery boundaries, security posture, ownership terms,
and evidence hashes. It helps a reviewer understand what is ready to show,
what must remain private, and what still needs review before reuse.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

CapsuleVisibility: TypeAlias = Literal["public_proof", "private_delivery", "internal"]
CapsuleAssetType: TypeAlias = Literal[
    "source_code",
    "documentation",
    "workflow",
    "evaluation_report",
    "data_fixture",
    "delivery_template",
]
CapsuleStatus: TypeAlias = Literal["ready", "review", "blocked"]

VISIBILITIES: tuple[CapsuleVisibility, ...] = ("public_proof", "private_delivery", "internal")
ASSET_TYPES: tuple[CapsuleAssetType, ...] = (
    "source_code",
    "documentation",
    "workflow",
    "evaluation_report",
    "data_fixture",
    "delivery_template",
)
WEIGHTS: Mapping[str, float] = {
    "value": 0.24,
    "evidence": 0.21,
    "security": 0.24,
    "deployability": 0.16,
    "rights": 0.15,
}
HARD_SECURITY_GATE = 0.50
HARD_RIGHTS_GATE = 0.60
READY_SCORE = 0.86
REVIEW_SCORE = 0.68

BASE_TERMS: tuple[str, ...] = (
    "Authorship and portfolio attribution remain with Shawdai Marie.",
    "Public proof must not contain client secrets, private account data, or assessment answers.",
    "Private delivery details require written commercial terms before external reuse.",
    "Security, identity, legal, financial, and hiring actions remain human-approved.",
)


@dataclass(frozen=True)
class CapsuleAsset:
    """One file that supports a deployment capsule."""

    path: str
    asset_type: CapsuleAssetType
    required: bool
    description: str = ""


@dataclass(frozen=True)
class CapsuleAssetEvidence:
    """Evidence captured for a capsule asset at manifest-build time."""

    path: str
    asset_type: CapsuleAssetType
    required: bool
    exists: bool
    sha256: str
    byte_size: int
    description: str


@dataclass(frozen=True)
class DeploymentCapsule:
    """A bounded package of work being prepared for proof, pilot, or delivery."""

    id: str
    title: str
    owner: str
    visibility: CapsuleVisibility
    license_expression: str
    summary: str
    assets: tuple[CapsuleAsset, ...]
    value_score: float
    evidence_score: float
    security_score: float
    deployability_score: float
    rights_score: float
    public_distribution: bool = False
    includes_sensitive_data: bool = False
    requires_client_terms: bool = False


@dataclass(frozen=True)
class CapsuleManifest:
    """Decision and evidence output for one deployment capsule."""

    capsule: DeploymentCapsule
    score: float
    status: CapsuleStatus
    blockers: tuple[str, ...]
    required_terms: tuple[str, ...]
    next_actions: tuple[str, ...]
    assets: tuple[CapsuleAssetEvidence, ...]
    manifest_sha256: str

    @property
    def ready_for_external_signal(self) -> bool:
        """Whether the capsule is ready to show as professional proof."""

        return self.status == "ready" and self.capsule.visibility == "public_proof"

    @property
    def ready_for_client_handoff(self) -> bool:
        """Whether the capsule is ready for a bounded private delivery conversation."""

        return self.status in {"ready", "review"} and self.capsule.visibility != "public_proof"


def _validate_score(score: float, field: str) -> None:
    if score < 0.0 or score > 1.0:
        raise ValueError(f"{field} must be in [0.0, 1.0]; got {score!r}")


def _validate_capsule(capsule: DeploymentCapsule) -> None:
    if not capsule.id.strip():
        raise ValueError("capsule id must not be blank")
    if not capsule.title.strip():
        raise ValueError(f"{capsule.id}: title must not be blank")
    if not capsule.owner.strip():
        raise ValueError(f"{capsule.id}: owner must not be blank")
    if not capsule.license_expression.strip():
        raise ValueError(f"{capsule.id}: license expression must not be blank")
    if not capsule.summary.strip():
        raise ValueError(f"{capsule.id}: summary must not be blank")
    _validate_score(capsule.value_score, f"{capsule.id}.value_score")
    _validate_score(capsule.evidence_score, f"{capsule.id}.evidence_score")
    _validate_score(capsule.security_score, f"{capsule.id}.security_score")
    _validate_score(capsule.deployability_score, f"{capsule.id}.deployability_score")
    _validate_score(capsule.rights_score, f"{capsule.id}.rights_score")
    paths = [asset.path for asset in capsule.assets]
    duplicates = sorted({path for path in paths if paths.count(path) > 1})
    if duplicates:
        raise ValueError(f"{capsule.id}: duplicate asset paths: {', '.join(duplicates)}")


def _safe_asset_path(root: Path, asset: CapsuleAsset) -> Path:
    relative = Path(asset.path)
    if not asset.path.strip():
        raise ValueError("asset path must not be blank")
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe capsule asset path: {asset.path!r}")
    return root / relative


def _asset_evidence(root: Path, asset: CapsuleAsset) -> CapsuleAssetEvidence:
    path = _safe_asset_path(root, asset)
    if not path.exists() or not path.is_file():
        return CapsuleAssetEvidence(
            path=asset.path,
            asset_type=asset.asset_type,
            required=asset.required,
            exists=False,
            sha256="",
            byte_size=0,
            description=asset.description,
        )
    payload = path.read_bytes()
    return CapsuleAssetEvidence(
        path=asset.path,
        asset_type=asset.asset_type,
        required=asset.required,
        exists=True,
        sha256=hashlib.sha256(payload).hexdigest(),
        byte_size=len(payload),
        description=asset.description,
    )


def capsule_score(capsule: DeploymentCapsule) -> float:
    """Return the weighted readiness score for a deployment capsule."""

    _validate_capsule(capsule)
    weighted = (
        capsule.value_score * WEIGHTS["value"]
        + capsule.evidence_score * WEIGHTS["evidence"]
        + capsule.security_score * WEIGHTS["security"]
        + capsule.deployability_score * WEIGHTS["deployability"]
        + capsule.rights_score * WEIGHTS["rights"]
    )
    return round(weighted, 4)


def _blockers(
    capsule: DeploymentCapsule,
    assets: Sequence[CapsuleAssetEvidence],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if not assets:
        blockers.append("capsule must declare at least one evidence asset")
    if capsule.security_score < HARD_SECURITY_GATE:
        blockers.append("security score is below the hard capsule gate")
    if capsule.rights_score < HARD_RIGHTS_GATE:
        blockers.append("ownership, license, or reuse clarity is below the hard gate")
    if capsule.public_distribution and capsule.visibility != "public_proof":
        blockers.append("non-public capsules cannot be marked for public distribution")
    if capsule.public_distribution and capsule.includes_sensitive_data:
        blockers.append("sensitive data cannot be included in a public capsule")
    if capsule.public_distribution and capsule.requires_client_terms:
        blockers.append("client delivery terms must be written before public distribution")
    missing_required = [asset.path for asset in assets if asset.required and not asset.exists]
    if missing_required:
        blockers.append(f"required assets missing: {', '.join(sorted(missing_required))}")
    return tuple(blockers)


def _status(score: float, blockers: Sequence[str]) -> CapsuleStatus:
    if blockers:
        return "blocked"
    if score >= READY_SCORE:
        return "ready"
    if score >= REVIEW_SCORE:
        return "review"
    return "blocked"


def _next_actions(status: CapsuleStatus, capsule: DeploymentCapsule) -> tuple[str, ...]:
    if status == "ready" and capsule.visibility == "public_proof":
        return (
            "Use as public professional proof with README, tests, limits, and attribution visible.",
            "Keep private delivery details, credentials, and client-specific material out of the capsule.",
        )
    if status == "ready":
        return (
            "Use as a private delivery reference after written scope and commercial terms are agreed.",
            "Preserve hashes, owner attribution, and handoff notes before implementation work starts.",
        )
    if status == "review":
        return (
            "Improve evidence, deployment notes, or rights clarity before external distribution.",
            "Keep the capsule bounded to a pilot until the review items are resolved.",
        )
    return (
        "Do not publish, reuse, or hand off this capsule until blockers are resolved.",
        "Create a remediation issue with owner, blocker, acceptance criteria, and target evidence.",
    )


def _asset_payload(asset: CapsuleAssetEvidence) -> dict[str, object]:
    return {
        "path": asset.path,
        "asset_type": asset.asset_type,
        "required": asset.required,
        "exists": asset.exists,
        "sha256": asset.sha256,
        "byte_size": asset.byte_size,
        "description": asset.description,
    }


def _manifest_payload(
    capsule: DeploymentCapsule,
    *,
    score: float,
    status: CapsuleStatus,
    blockers: Sequence[str],
    assets: Sequence[CapsuleAssetEvidence],
    manifest_sha256: str | None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "sentinel.deployment_capsule.v1",
        "id": capsule.id,
        "title": capsule.title,
        "owner": capsule.owner,
        "visibility": capsule.visibility,
        "license_expression": capsule.license_expression,
        "summary": capsule.summary,
        "score": score,
        "status": status,
        "public_distribution": capsule.public_distribution,
        "includes_sensitive_data": capsule.includes_sensitive_data,
        "requires_client_terms": capsule.requires_client_terms,
        "blockers": list(blockers),
        "required_terms": list(BASE_TERMS),
        "next_actions": list(_next_actions(status, capsule)),
        "assets": [_asset_payload(asset) for asset in assets],
    }
    if manifest_sha256 is not None:
        payload["manifest_sha256"] = manifest_sha256
    return payload


def _canonical_sha256(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_capsule_manifest(capsule: DeploymentCapsule, *, root: Path) -> CapsuleManifest:
    """Build a verifiable manifest for one deployment capsule."""

    score = capsule_score(capsule)
    assets = tuple(_asset_evidence(root, asset) for asset in capsule.assets)
    blockers = _blockers(capsule, assets)
    status = _status(score, blockers)
    unsigned = _manifest_payload(
        capsule,
        score=score,
        status=status,
        blockers=blockers,
        assets=assets,
        manifest_sha256=None,
    )
    manifest_sha256 = _canonical_sha256(unsigned)
    return CapsuleManifest(
        capsule=capsule,
        score=score,
        status=status,
        blockers=blockers,
        required_terms=BASE_TERMS,
        next_actions=_next_actions(status, capsule),
        assets=assets,
        manifest_sha256=manifest_sha256,
    )


def capsule_manifest_payload(manifest: CapsuleManifest) -> dict[str, object]:
    """Return a JSON-serializable capsule manifest payload."""

    return _manifest_payload(
        manifest.capsule,
        score=manifest.score,
        status=manifest.status,
        blockers=manifest.blockers,
        assets=manifest.assets,
        manifest_sha256=manifest.manifest_sha256,
    )


def build_capsule_manifests(
    capsules: Sequence[DeploymentCapsule],
    *,
    root: Path,
) -> list[CapsuleManifest]:
    """Build manifests for a sequence of capsules in declared order."""

    ids = [capsule.id for capsule in capsules]
    duplicates = sorted({capsule_id for capsule_id in ids if ids.count(capsule_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate capsule ids: {', '.join(duplicates)}")
    return [build_capsule_manifest(capsule, root=root) for capsule in capsules]
