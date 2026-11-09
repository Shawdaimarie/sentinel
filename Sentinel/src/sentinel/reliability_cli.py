"""Assess captured repeated trials without running models or external actions."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from sentinel.reliability import MAX_INPUT_BYTES, assess_reliability, render_reliability


def _read(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(MAX_INPUT_BYTES + 1)


def main(argv: Sequence[str] | None = None) -> int:
    """Return 0 pass, 1 fail, 2 invalid input, or 3 inconclusive evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--runs", required=True, type=Path)
    parser.add_argument("--baseline-runs", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = assess_reliability(
            _read(args.manifest),
            _read(args.cases),
            _read(args.runs),
            _read(args.baseline_runs) if args.baseline_runs else None,
        )
        markdown = render_reliability(report)
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "reliability.json").write_text(
            report.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        (args.output_dir / "reliability.md").write_text(markdown, encoding="utf-8")
    except (OSError, ValueError, RecursionError) as exc:
        print(f"sentinel-reliability: {exc}", file=sys.stderr)
        return 2
    print(f"Reliability: {report.status}; evidence: {args.output_dir}")
    return {"pass": 0, "fail": 1, "inconclusive": 3}[report.status]


if __name__ == "__main__":
    raise SystemExit(main())
