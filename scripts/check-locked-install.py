"""Verify container dependency locks with real pip and an isolated installation.

Run with Python 3.12. Downloads require network access; the package build,
runtime installation, negative checks, and assessment use local files only.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "Sentinel"


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def main() -> None:
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Use Python 3.12, matching the container runtime")
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
    env.update(PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1")
    with tempfile.TemporaryDirectory(prefix="sentinel-locked-") as directory:
        work = Path(directory)

        def run(*args: str | Path, expected_failure: str | None = None) -> str:
            result = subprocess.run(
                [str(arg) for arg in args],
                cwd=work,
                env=env,
                text=True,
                capture_output=True,
                timeout=180,
                check=False,
            )
            output = result.stdout + result.stderr
            if expected_failure is not None:
                if result.returncode == 0 or expected_failure not in output:
                    raise RuntimeError(
                        f"Expected rejection containing {expected_failure!r}:\n{output}"
                    )
            elif result.returncode != 0:
                raise RuntimeError(output)
            return result.stdout

        def venv(name: str) -> Path:
            location = work / name
            run(sys.executable, "-m", "venv", location)
            return location / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        builder = venv("builder")
        runtime = venv("runtime")
        wheels = work / "wheels"
        lock = PROJECT / "requirements-runtime.txt"
        source = work / "source"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copy2(PROJECT / name, source / name)
        shutil.copytree(
            PROJECT / "src",
            source / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"),
        )
        run(
            builder,
            "-m",
            "pip",
            "install",
            "--require-hashes",
            "--only-binary=:all:",
            "-r",
            PROJECT / "requirements-build.txt",
        )
        run(
            builder,
            "-m",
            "pip",
            "download",
            "--require-hashes",
            "--only-binary=:all:",
            "--dest",
            wheels,
            "-r",
            lock,
        )
        run(
            builder,
            "-m",
            "pip",
            "wheel",
            "--no-index",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            wheels,
            source,
        )
        run(
            runtime,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            wheels,
            "--require-hashes",
            "--only-binary=:all:",
            "-r",
            lock,
        )
        (package,) = wheels.glob("sentinel-*.whl")
        run(runtime, "-m", "pip", "install", "--no-index", "--no-deps", package)
        run(runtime, "-m", "pip", "check")
        installed = json.loads(run(runtime, "-m", "pip", "list", "--format=json"))
        expected = {
            normalize(n): v
            for n, v in re.findall(r"^([\w.-]+)==([^\s]+)", lock.read_text(), re.MULTILINE)
        }
        actual = {
            normalize(p["name"]): p["version"]
            for p in installed
            if normalize(p["name"]) not in {"pip", "sentinel"}
        }
        if actual != expected:
            raise RuntimeError(f"Installed dependency drift: {actual!r} != {expected!r}")

        # Modify actual wheel bytes; the rejection must be a checksum failure.
        corrupt = work / "corrupt"
        corrupt.mkdir()
        for wheel in wheels.glob("*.whl"):
            if wheel != package:
                (corrupt / wheel.name).write_bytes(wheel.read_bytes() + b"changed")
        run(
            builder,
            "-m",
            "pip",
            "download",
            "--no-index",
            "--find-links",
            corrupt,
            "--require-hashes",
            "--only-binary=:all:",
            "--dest",
            work / "rejected",
            "-r",
            lock,
            expected_failure="DO NOT MATCH THE HASHES",
        )

        # Dropping a transitive pin must not allow it to resolve unchecked.
        incomplete = work / "incomplete.txt"
        incomplete.write_text(
            re.sub(r"(?m)^anyio==.*?(?=^[a-zA-Z]|\Z)", "", lock.read_text(), flags=re.DOTALL)
        )
        run(
            builder,
            "-m",
            "pip",
            "download",
            "--no-index",
            "--find-links",
            wheels,
            "--require-hashes",
            "--only-binary=:all:",
            "--dest",
            work / "incomplete",
            "-r",
            incomplete,
            expected_failure="must have their versions pinned",
        )

        print(
            run(
                runtime,
                "-m",
                "sentinel.assessment_cli",
                "--suite",
                PROJECT / "examples/reliability_assessment/suite.json",
                "--output-dir",
                work / "reports",
            ).strip()
        )
        print(
            f"PASS: {len(actual)} locked runtime dependencies; pip check; modified-wheel and "
            "missing-pin rejection; installed assessment conformance"
        )
        print(json.dumps(actual, sort_keys=True))


if __name__ == "__main__":
    main()
