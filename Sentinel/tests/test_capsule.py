from pathlib import Path

import pytest

from sentinel.capsule import (
    CapsuleAsset,
    DeploymentCapsule,
    build_capsule_manifest,
    build_capsule_manifests,
    capsule_manifest_payload,
)


def _write(path: Path, text: str = "evidence") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _ready_capsule() -> DeploymentCapsule:
    return DeploymentCapsule(
        id="sentinel-public-proof",
        title="Sentinel public proof capsule",
        owner="Shawdai Marie",
        visibility="public_proof",
        license_expression="Apache-2.0 for repository code; reserved materials excluded",
        summary="Verifiable public proof for governed AI-agent engineering.",
        assets=(
            CapsuleAsset(
                path="README.md",
                asset_type="documentation",
                required=True,
                description="Primary reviewer-facing project surface.",
            ),
        ),
        value_score=0.95,
        evidence_score=0.94,
        security_score=0.93,
        deployability_score=0.90,
        rights_score=0.89,
        public_distribution=True,
    )


def test_ready_public_capsule_records_hash_and_external_signal(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# Sentinel\n")

    manifest = build_capsule_manifest(_ready_capsule(), root=tmp_path)
    payload = capsule_manifest_payload(manifest)

    assert manifest.status == "ready"
    assert manifest.ready_for_external_signal is True
    assert manifest.assets[0].exists is True
    assert len(manifest.assets[0].sha256) == 64
    assert payload["manifest_sha256"] == manifest.manifest_sha256


def test_sensitive_public_capsule_is_blocked(tmp_path: Path) -> None:
    _write(tmp_path / "README.md")
    capsule = DeploymentCapsule(
        id="sensitive-public",
        title="Sensitive public capsule",
        owner="Shawdai Marie",
        visibility="public_proof",
        license_expression="Reserved",
        summary="This intentionally violates public proof boundaries.",
        assets=(CapsuleAsset("README.md", "documentation", True),),
        value_score=0.90,
        evidence_score=0.90,
        security_score=0.90,
        deployability_score=0.90,
        rights_score=0.90,
        public_distribution=True,
        includes_sensitive_data=True,
    )

    manifest = build_capsule_manifest(capsule, root=tmp_path)

    assert manifest.status == "blocked"
    assert "sensitive data cannot be included" in manifest.blockers[0]
    assert manifest.ready_for_external_signal is False


def test_private_delivery_cannot_be_marked_public(tmp_path: Path) -> None:
    _write(tmp_path / "handoff.md")
    capsule = DeploymentCapsule(
        id="private-handoff",
        title="Private delivery handoff",
        owner="Shawdai Marie",
        visibility="private_delivery",
        license_expression="Private commercial terms required",
        summary="A private delivery template that should not be public proof.",
        assets=(CapsuleAsset("handoff.md", "delivery_template", True),),
        value_score=0.88,
        evidence_score=0.87,
        security_score=0.91,
        deployability_score=0.80,
        rights_score=0.85,
        public_distribution=True,
    )

    manifest = build_capsule_manifest(capsule, root=tmp_path)

    assert manifest.status == "blocked"
    assert any("non-public capsules" in blocker for blocker in manifest.blockers)


def test_missing_required_asset_blocks_capsule(tmp_path: Path) -> None:
    manifest = build_capsule_manifest(_ready_capsule(), root=tmp_path)

    assert manifest.status == "blocked"
    assert any("required assets missing" in blocker for blocker in manifest.blockers)


def test_duplicate_capsule_ids_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "README.md")
    capsule = _ready_capsule()

    with pytest.raises(ValueError, match="duplicate capsule ids"):
        build_capsule_manifests([capsule, capsule], root=tmp_path)


def test_parent_directory_asset_paths_are_rejected(tmp_path: Path) -> None:
    capsule = DeploymentCapsule(
        id="unsafe-path",
        title="Unsafe path capsule",
        owner="Shawdai Marie",
        visibility="public_proof",
        license_expression="Apache-2.0",
        summary="Path traversal should never be accepted as evidence.",
        assets=(CapsuleAsset("../secret.txt", "documentation", True),),
        value_score=0.90,
        evidence_score=0.90,
        security_score=0.90,
        deployability_score=0.90,
        rights_score=0.90,
        public_distribution=True,
    )

    with pytest.raises(ValueError, match="unsafe capsule asset path"):
        build_capsule_manifest(capsule, root=tmp_path)
