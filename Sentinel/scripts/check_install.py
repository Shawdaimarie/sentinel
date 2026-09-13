"""Exercise a non-editable installation using offline fixtures and temporary output."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    args = parser.parse_args()
    fixtures = args.fixtures.resolve()
    dist = importlib.metadata.distribution("sentinel")
    direct = json.loads(dist.read_text("direct_url.json") or "{}")
    if direct.get("dir_info", {}).get("editable"):
        raise SystemExit("Install a wheel, not an editable checkout, before this check")
    bindir = Path(sys.executable).parent
    suffix = ".exe" if os.name == "nt" else ""
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
    with tempfile.TemporaryDirectory(prefix="sentinel-install-") as directory:
        work = Path(directory)

        def run(command, *arguments, expected=0):
            result = subprocess.run(
                [str(bindir / (command + suffix)), *map(str, arguments)],
                cwd=work, env=env, text=True, capture_output=True, timeout=60,
            )
            if result.returncode != expected:
                raise RuntimeError(
                    f"{command}: expected exit {expected}, got {result.returncode}\n"
                    f"{result.stdout}\n{result.stderr}"
                )

        run("sentinel-import-otel", "--input", fixtures / "agent_trace.json",
            "--output", work / "runs.jsonl", "--manifest", work / "manifest.json")
        run("sentinel-eval", "--cases", fixtures / "eval_case.jsonl",
            "--runs", work / "runs.jsonl", "--json-out", work / "valid.json",
            "--report", work / "valid.md", "--min-score", "0.90")
        runs = [json.loads(line) for line in (work / "runs.jsonl").read_text().splitlines()]
        if len(runs) != 1:
            raise RuntimeError("Expected exactly one run in the installation fixture")
        runs[0]["actions"].append({"name": "secrets.read", "target": "synthetic",
                                   "status": "executed", "latency_ms": 0, "cost_usd": 0})
        (work / "unsafe.jsonl").write_text(json.dumps(runs[0]) + "\n")
        run("sentinel-eval", "--cases", fixtures / "eval_case.jsonl",
            "--runs", work / "unsafe.jsonl", "--json-out", work / "unsafe.json",
            "--report", work / "unsafe.md", expected=1)
        (work / "invalid.json").write_text("{invalid")
        run("sentinel-import-otel", "--input", work / "invalid.json",
            "--output", work / "invalid-runs.jsonl",
            "--manifest", work / "invalid-manifest.json", expected=2)
        if (work / "invalid-runs.jsonl").exists():
            raise RuntimeError("Invalid input created run output")
    print(f"PASS: Sentinel {dist.version} installed commands; valid, unsafe, malformed cases")
    print("Offline synthetic checks only; not production or provider verification")


if __name__ == "__main__":
    main()
