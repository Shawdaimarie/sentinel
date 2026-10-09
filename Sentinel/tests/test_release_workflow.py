"""Keep the release pipeline's supply-chain guarantees from silently eroding.

RELEASING.md makes specific claims: only reviewed refs are signed, nothing is
published before it passes the vulnerability gate, attestations bind the pushed
digest, and base images and workflow actions are pinned. Each claim here is a failing test if a
later edit weakens it. Guard scripts are executed, not pattern-matched.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
RELEASE = WORKFLOWS / "release.yml"
SHA_PINNED = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
DIGEST_PINNED = re.compile(r"@sha256:[0-9a-f]{64}$")


def _load(path: Path) -> dict[str, Any]:
    # BaseLoader keeps `on`, booleans, and versions as strings (YAML 1.2 semantics).
    workflow: dict[str, Any] = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
    return workflow


def _steps(job: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = _load(RELEASE)["jobs"][job]["steps"]
    return steps


def _step(job: str, name: str) -> dict[str, Any]:
    matches = [s for s in _steps(job) if s.get("name") == name or s.get("id") == name]
    assert len(matches) == 1, f"Expected exactly one step {name!r} in {job}"
    return matches[0]


def _index(job: str, name: str) -> int:
    return _steps(job).index(_step(job, name))


def _run_guard(step: str, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess[str]:
    script = _step("release-guard", step)["run"]
    return subprocess.run(
        ["bash", "-eo", "pipefail", "-c", script],
        cwd=cwd,
        env={"PATH": os.environ["PATH"], **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_triggers_exclude_untrusted_events() -> None:
    """Pull requests must never reach a job that can sign and publish."""
    events = _load(RELEASE)["on"]
    assert set(events) == {"push", "workflow_dispatch"}
    assert events["push"]["branches"] == ["main"]
    assert events["push"]["tags"] == ["v*.*.*"]


def test_signing_permissions_are_confined_to_publish() -> None:
    workflow = _load(RELEASE)
    assert workflow["permissions"] == {"contents": "read"}
    assert "permissions" not in workflow["jobs"]["release-guard"]
    assert workflow["jobs"]["publish"]["permissions"] == {
        "contents": "read",
        "packages": "write",
        "id-token": "write",
        "attestations": "write",
    }
    assert workflow["jobs"]["publish"]["needs"] == "release-guard"


@pytest.mark.parametrize(
    ("ref", "allowed"),
    [
        ("refs/heads/main", True),
        ("refs/tags/v0.7.0", True),
        ("refs/heads/feat/unreviewed", False),
        ("refs/heads/main-copy", False),
        ("refs/pull/41/merge", False),
        ("refs/tags/release-0.7.0", False),
    ],
)
def test_ref_guard_signs_only_reviewed_refs(ref: str, allowed: bool, tmp_path: Path) -> None:
    result = _run_guard("Ref is main or a version tag", {"GITHUB_REF": ref}, tmp_path)
    assert (result.returncode == 0) is allowed, result.stdout + result.stderr


@pytest.mark.parametrize(("tag", "allowed"), [("v1.4.2", True), ("v1.4.3", False), ("v1.4", False)])
def test_version_guard_requires_declared_version(tag: str, allowed: bool, tmp_path: Path) -> None:
    (tmp_path / "Sentinel").mkdir()
    (tmp_path / "Sentinel/pyproject.toml").write_text('[project]\nname = "x"\nversion = "1.4.2"\n')
    result = _run_guard("Tag matches declared package version", {"GITHUB_REF_NAME": tag}, tmp_path)
    assert (result.returncode == 0) is allowed, result.stdout + result.stderr


def test_ancestry_guard_rejects_tags_outside_main(tmp_path: Path) -> None:
    git_env = {
        "PATH": os.environ["PATH"],
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=tmp_path, env=git_env, check=True, capture_output=True, text=True
        ).stdout.strip()

    git("init", "-q", "-b", "main")
    git("commit", "-q", "--allow-empty", "-m", "reviewed")
    reviewed = git("rev-parse", "HEAD")
    git("checkout", "-q", "-b", "side")
    git("commit", "-q", "--allow-empty", "-m", "unreviewed")
    unreviewed = git("rev-parse", "HEAD")
    git("remote", "add", "origin", str(tmp_path))

    guard_env = {k: v for k, v in git_env.items() if k != "PATH"}
    for sha, allowed in ((reviewed, True), (unreviewed, False)):
        env = {**guard_env, "GITHUB_SHA": sha, "GITHUB_REF_NAME": "v0.0.1"}
        result = _run_guard("Tagged commit is on main", env, tmp_path)
        assert (result.returncode == 0) is allowed, result.stdout + result.stderr


def test_nothing_is_published_before_the_vulnerability_gate() -> None:
    build = _step("publish", "build")
    assert build["with"]["push"] == "false"
    assert build["with"]["load"] == "true"
    assert build["with"]["provenance"] == "false", "BuildKit provenance is unsigned"
    assert build["with"]["sbom"] == "false", "BuildKit SBOM is unsigned"

    order = [
        "build",
        "Check packaged behavior before publication",
        "Generate SBOM (SPDX)",
        "Vulnerability gate",
        "Publish scanned image",
        "Attest build provenance",
        "Attest SBOM",
        "Verify attestations as a consumer",
        "Pull and smoke-test the verified digest",
        "Record release evidence",
    ]
    positions = [_index("publish", name) for name in order]
    assert positions == sorted(positions), "Release steps are out of order"

    pushers = [s for s in _steps("publish") if "docker push" in s.get("run", "")]
    assert pushers == [_step("publish", "Publish scanned image")]


def test_release_smoke_checks_cover_the_published_digest() -> None:
    before = _step("publish", "Check packaged behavior before publication")
    after = _step("publish", "Pull and smoke-test the verified digest")
    assert before["env"]["IMAGE"].endswith(":sha-${{ github.sha }}")
    assert after["env"]["IMAGE"].endswith("@${{ steps.push.outputs.digest }}")
    assert 'docker pull "$IMAGE"' in after["run"]
    for step in (before, after):
        assert 'timeout 60s bash scripts/smoke-image.sh "$COMPONENT" "$IMAGE"' in step["run"]
        assert "continue-on-error" not in step and "if" not in step


def test_vulnerability_gate_blocks_and_scans_the_attested_sbom() -> None:
    scan = _step("publish", "Vulnerability gate")
    sbom = _step("publish", "Generate SBOM (SPDX)")
    assert scan["with"]["fail-build"] == "true"
    assert scan["with"]["severity-cutoff"] in {"high", "medium", "low", "negligible"}
    assert scan["with"]["sbom"] == sbom["with"]["output-file"]
    assert _step("publish", "Attest SBOM")["with"]["sbom-path"] == sbom["with"]["output-file"]
    assert "continue-on-error" not in scan
    assert "if" not in scan


def test_attestations_bind_the_pushed_digest() -> None:
    pushed = "${{ steps.push.outputs.digest }}"
    for name in ("Attest build provenance", "Attest SBOM"):
        step = _step("publish", name)
        assert step["with"]["subject-digest"] == pushed, name
        assert step["with"]["push-to-registry"] == "true", name


def test_preflight_scans_release_candidates_without_publish_permissions() -> None:
    preflight = _load(WORKFLOWS / "container-preflight.yml")
    assert set(preflight["on"]) == {"pull_request", "workflow_dispatch"}
    assert preflight["permissions"] == {"contents": "read"}
    assert set(preflight["jobs"]) == {"scan"}
    job = preflight["jobs"]["scan"]
    assert "permissions" not in job
    assert job["strategy"] == _load(RELEASE)["jobs"]["publish"]["strategy"]
    assert job["strategy"]["fail-fast"] == "false"
    steps = {step.get("name"): step for step in job["steps"]}
    scan = steps["Vulnerability gate"]
    release_scan = _step("publish", "Vulnerability gate")
    assert scan["uses"] == release_scan["uses"]
    assert scan["with"] == release_scan["with"]
    assert "continue-on-error" not in scan and "if" not in scan
    build = steps["Build candidate image"]
    assert build["with"]["push"] == "false"
    assert build["with"]["load"] == "true"
    for key in ("context", "file", "provenance", "sbom"):
        assert build["with"][key] == _step("publish", "build")["with"][key]
    assert not any("login-action" in step.get("uses", "") for step in job["steps"])
    assert not any("attest-" in step.get("uses", "") for step in job["steps"])
    assert steps["Upload scan evidence"]["if"] == "always()"


def test_failed_release_preserves_inventory_and_report() -> None:
    upload = _step("publish", "Upload vulnerability report")
    assert upload["if"] == "always()"
    assert "${{ matrix.name }}.vulnerabilities.json" in upload["with"]["path"]
    assert "${{ matrix.name }}.spdx.json" in upload["with"]["path"]
    assert _index("publish", "Upload vulnerability report") < _index(
        "publish", "Publish scanned image"
    )


def test_summary_exposes_active_fixable_findings_only(tmp_path: Path) -> None:
    def finding(severity: str, state: str, identifier: str) -> dict[str, Any]:
        return {
            "vulnerability": {
                "id": identifier,
                "severity": severity,
                "fix": {"state": state, "versions": ["2.0"]},
            },
            "artifact": {"name": "package|name", "version": "1.0"},
        }

    active = finding("High", "fixed", "CVE-active")
    report = {
        "matches": [
            active,
            active,
            finding("Low", "fixed", "CVE-low"),
            finding("Critical", "not-fixed", "CVE-unfixed"),
        ],
        "ignoredMatches": [{"match": finding("High", "fixed", "CVE-ignored")}],
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report))
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/summarize-vulnerabilities.py"), str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "**1**" in result.stdout
    assert "CVE-active" in result.stdout and "package\\|name" in result.stdout
    assert all(value not in result.stdout for value in ("CVE-low", "CVE-unfixed", "CVE-ignored"))


def test_missing_scan_report_never_claims_clean_result(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/summarize-vulnerabilities.py"),
            str(tmp_path / "missing"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Report unavailable" in result.stdout
    assert "**0**" not in result.stdout


def test_release_verifies_like_a_consumer() -> None:
    verify = _step("publish", "Verify attestations as a consumer")
    assert verify["env"]["SIGNER"] == "${{ github.repository }}/.github/workflows/release.yml"
    assert verify["env"]["IMAGE"].endswith("@${{ steps.push.outputs.digest }}")
    commands = verify["run"].split("gh attestation verify")[1:]
    assert len(commands) == 2, "Provenance and SBOM must both be verified"
    for command in commands:
        assert '--signer-workflow "$SIGNER"' in command
        assert '--source-ref "$GITHUB_REF"' in command
    assert "--predicate-type https://spdx.dev/Document/v2.3" in commands[1]


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_commit(path: Path) -> None:
    for job_id, job in _load(path)["jobs"].items():
        for step in job.get("steps", []):
            uses = step.get("uses")
            if uses is None or uses.startswith("./"):
                continue
            if uses.startswith("docker://"):
                assert DIGEST_PINNED.search(uses), f"{path.name}:{job_id} {uses}"
            else:
                assert SHA_PINNED.match(uses), f"{path.name}:{job_id} {uses} is not SHA-pinned"
        for service in job.get("services", {}).values():
            assert DIGEST_PINNED.search(service["image"]), f"{path.name}:{job_id} service image"


@pytest.mark.parametrize("dockerfile", ["Sentinel/Dockerfile", "Aegis/Dockerfile"])
def test_base_images_are_pinned_by_digest(dockerfile: str) -> None:
    images = [
        line.split()[1]
        for line in (ROOT / dockerfile).read_text().splitlines()
        if line.upper().startswith("FROM ")
    ]
    assert images
    for image in images:
        assert image == "scratch" or DIGEST_PINNED.search(image), f"{dockerfile}: {image}"


def test_compose_images_are_pinned_by_digest() -> None:
    compose = yaml.safe_load((ROOT / "Sentinel/compose.history.yml").read_text())
    for name, service in compose["services"].items():
        if "image" in service:
            assert DIGEST_PINNED.search(service["image"]), name
