"""Published-image rescanning must retain digest identity and fail closed."""

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/published-image-rescan.yml"
DIGEST = "sha256:" + "a" * 64
SUBJECT = "ghcr.io/shawdaimarie/sentinel-eval@" + DIGEST
BASH = shutil.which("bash") or "/bin/bash"


def _workflow() -> dict[str, Any]:
    result: dict[str, Any] = yaml.load(WORKFLOW.read_text(), Loader=yaml.BaseLoader)
    return result


def _steps() -> dict[str, Any]:
    return {s.get("name", "checkout"): s for s in _workflow()["jobs"]["rescan"]["steps"]}


def _resolve(
    tmp_path: Path, *, digest: str = DIGEST, fail_sbom: bool = False,
    component: str = "sentinel-eval",
) -> tuple[subprocess.CompletedProcess[str], list[str], str]:
    """Execute the real resolution step and verification script with offline tools."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    log.write_text("")
    output = tmp_path / "output"
    output.write_text("")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copyfile(ROOT / "scripts/verify-image.sh", scripts / "verify-image.sh")
    (bin_dir / "docker").write_text(
        '#!/bin/sh\nprintf "docker %s\\n" "$*" >> "$CALL_LOG"\n'
        'printf "%s\\n" "$FAKE_DIGEST"\n'
    )
    (bin_dir / "gh").write_text(
        '#!/bin/sh\nprintf "gh %s\\n" "$*" >> "$CALL_LOG"\n'
        'case "$*" in *--predicate-type*) exit "$FAIL_SBOM";; esac\n'
    )
    for tool in ("docker", "gh"):
        (bin_dir / tool).chmod(0o755)
    # Only mocked network tools are on PATH; these three local utilities are real.
    for tool in ("bash", "mkdir", "tee"):
        target = shutil.which(tool)
        assert target is not None
        (bin_dir / tool).symlink_to(target)
    result = subprocess.run(
        [BASH, "--noprofile", "--norc", "-eo", "pipefail", "-c",
         _steps()["Resolve and verify the published digest"]["run"]],
        cwd=tmp_path,
        env={"PATH": str(bin_dir), "COMPONENT": component, "CALL_LOG": str(log),
             "FAKE_DIGEST": digest, "FAIL_SBOM": str(int(fail_sbom)),
             "GITHUB_OUTPUT": str(output)},
        capture_output=True, text=True, check=False,
    )
    return result, log.read_text().splitlines(), output.read_text()


def test_rescan_freezes_tag_before_verifying_both_attestations(tmp_path: Path) -> None:
    result, calls, output = _resolve(tmp_path)
    assert result.returncode == 0, result.stderr
    assert len(calls) == 3
    assert calls[0].startswith("docker buildx imagetools inspect ")
    assert ":edge --format" in calls[0]
    for call in calls[1:]:
        assert f"gh attestation verify oci://{SUBJECT}" in call
        assert "--source-ref refs/heads/main" in call
        assert "--signer-workflow Shawdaimarie/sentinel/.github/workflows/release.yml" in call
        assert ":edge" not in call
    assert "--predicate-type https://spdx.dev/Document/v2.3" in calls[2]
    assert output == f"ref={SUBJECT}\n"
    assert (tmp_path / "rescan-evidence/subject.txt").read_text() == SUBJECT + "\n"


def test_failed_sbom_verification_never_exposes_a_scannable_subject(tmp_path: Path) -> None:
    result, calls, output = _resolve(tmp_path, fail_sbom=True)
    assert result.returncode != 0
    assert len(calls) == 3
    assert output == ""
    assert "SBOM attestation did not verify" in result.stderr


@pytest.mark.parametrize("digest", ["", "sha256:short", "sha256:" + "a" * 65,
                                   DIGEST + "\nref=untrusted", "sha512:" + "a" * 64])
def test_malformed_registry_digest_is_rejected_before_verification(
    tmp_path: Path, digest: str,
) -> None:
    result, calls, output = _resolve(tmp_path, digest=digest)
    assert result.returncode != 0
    assert len(calls) == 1 and output == ""


def test_an_unlisted_component_never_reaches_the_registry(tmp_path: Path) -> None:
    result, calls, output = _resolve(tmp_path, component="sentinel-eval/../../other")
    assert result.returncode != 0 and calls == [] and output == ""


def test_rescan_cannot_sign_publish_or_ignore_failed_checks() -> None:
    workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["rescan"]
    assert "permissions" not in job
    assert job["timeout-minutes"] == "20"
    steps = _steps()
    for name in ["Resolve and verify the published digest",
                 "Pull the verified digest without executing it",
                 "Inventory the published bytes", "Scan with updated vulnerability data"]:
        assert "if" not in steps[name] and "continue-on-error" not in steps[name]
    scan = steps["Scan with updated vulnerability data"]
    assert scan["with"]["fail-build"] == "true"
    assert scan["with"]["severity-cutoff"] == "high"
    assert scan["with"]["only-fixed"] == "true"
    assert scan["with"]["config"] == ".grype.yaml"
    assert scan["env"]["GRYPE_DB_REQUIRE_UPDATE_CHECK"] == "true"
    assert scan["env"]["GRYPE_DB_VALIDATE_AGE"] == "true"
    assert scan["with"]["sbom"] == steps["Inventory the published bytes"]["with"]["output-file"]
    inventory = steps["Inventory the published bytes"]
    assert inventory["with"]["image"] == "${{ steps.verified.outputs.ref }}"
    for step in steps.values():
        assert "docker push" not in step.get("run", "")
        assert "docker run" not in step.get("run", "")
        assert "attest-" not in step.get("uses", "")
    assert steps["Retain rescan evidence"]["if"] == "always()"
    assert steps["Summarize the dated result"]["if"] == "always()"
