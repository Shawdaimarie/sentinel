"""Consumer verification script: exact checks, no guessed trust inputs.

`gh` and `docker` are replaced by stubs that record their arguments, so these
tests run offline and assert what the script would ask the real tools to prove.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/verify-image.sh"
IMAGE = "ghcr.io/shawdaimarie/sentinel-eval"
DIGEST = "sha256:" + "a" * 64
SIGNER = "Shawdaimarie/sentinel/.github/workflows/release.yml"
BASH = shutil.which("bash") or "/bin/bash"


def _run(
    tmp_path: Path, *args: str, gh_exit: int = 0, with_tools: bool = True
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    log = tmp_path / "calls.log"
    log.write_text("")
    if with_tools:
        (bin_dir / "gh").write_text(f'#!/bin/sh\necho "gh $*" >> "{log}"\nexit {gh_exit}\n')
        docker = f'#!/bin/sh\necho "docker $*" >> "{log}"\necho "{DIGEST}"\n'
        (bin_dir / "docker").write_text(docker)
        for tool in ("gh", "docker"):
            (bin_dir / tool).chmod(0o755)
    result = subprocess.run(
        [BASH, str(SCRIPT), *args],
        # Only the stubs are reachable, so a real gh or docker is never called.
        env={"PATH": str(bin_dir)},
        capture_output=True,
        text=True,
        check=False,
    )
    return result, log.read_text().splitlines()


def test_version_tag_is_resolved_and_both_attestations_are_verified(tmp_path: Path) -> None:
    result, calls = _run(tmp_path, f"{IMAGE}:v0.7.0")
    assert result.returncode == 0, result.stderr
    inspect = f"docker buildx imagetools inspect {IMAGE}:v0.7.0 --format {{{{.Manifest.Digest}}}}"
    assert calls[0] == inspect
    expected = (
        f"gh attestation verify oci://{IMAGE}@{DIGEST} --repo Shawdaimarie/sentinel "
        f"--signer-workflow {SIGNER} --source-ref refs/tags/v0.7.0"
    )
    assert calls[1] == expected
    assert calls[2] == expected + " --predicate-type https://spdx.dev/Document/v2.3"
    assert result.stdout.rstrip().endswith(f"{IMAGE}@{DIGEST}")


@pytest.mark.parametrize(
    ("reference", "source_ref"),
    [("0.7.0", "refs/tags/v0.7.0"), ("edge", "refs/heads/main")],
)
def test_unambiguous_tags_infer_their_source_ref(
    reference: str, source_ref: str, tmp_path: Path
) -> None:
    result, calls = _run(tmp_path, f"{IMAGE}:{reference}")
    assert result.returncode == 0, result.stderr
    assert calls[1].endswith(f"--source-ref {source_ref}")


@pytest.mark.parametrize("reference", [":latest", ":0.7", ":sha-" + "b" * 40, "@" + DIGEST])
def test_ambiguous_references_require_an_explicit_source_ref(
    reference: str, tmp_path: Path
) -> None:
    result, calls = _run(tmp_path, IMAGE + reference)
    assert result.returncode != 0
    assert "--source-ref" in result.stderr
    assert not [c for c in calls if c.startswith("gh ")], "Nothing may be verified on a guess"

    result, calls = _run(tmp_path, IMAGE + reference, "--source-ref", "refs/tags/v0.7.0")
    assert result.returncode == 0, result.stderr


def test_digest_reference_is_verified_without_resolution(tmp_path: Path) -> None:
    result, calls = _run(tmp_path, f"{IMAGE}@{DIGEST}", "--source-ref", "refs/heads/main")
    assert result.returncode == 0, result.stderr
    assert not [c for c in calls if c.startswith("docker ")]


@pytest.mark.parametrize(
    "args",
    [
        ("ghcr.io/someone-else/sentinel-eval:v0.7.0",),
        ("docker.io/library/python:3.12",),
        (f"{IMAGE}:v0.7.0", "--source-ref", "refs/heads/feature"),
        (f"{IMAGE}:v0.7.0", "--source-ref", "refs/pull/1/merge"),
    ],
)
def test_untrusted_images_and_refs_are_refused(args: tuple[str, ...], tmp_path: Path) -> None:
    result, calls = _run(tmp_path, *args)
    assert result.returncode != 0
    assert not [c for c in calls if c.startswith("gh ")]


def test_failed_verification_fails_closed(tmp_path: Path) -> None:
    result, _ = _run(tmp_path, f"{IMAGE}:v0.7.0", gh_exit=1)
    assert result.returncode != 0
    assert "did not verify" in result.stderr
    assert "Deploy by digest" not in result.stdout


def test_missing_gh_is_reported(tmp_path: Path) -> None:
    result, _ = _run(tmp_path, f"{IMAGE}:v0.7.0", with_tools=False)
    assert result.returncode != 0
    assert "gh is required" in result.stderr


def test_script_is_executable() -> None:
    assert os.access(SCRIPT, os.X_OK)
