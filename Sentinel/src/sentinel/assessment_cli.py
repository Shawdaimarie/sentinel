"""Run a synthetic reliability demonstration without network or model calls."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from sentinel.assessment import assess_suite, render_assessment


def main(argv: Sequence[str] | None = None) -> int:
    """Write reviewable evidence; return 0 for agreement, 1 for mismatch, 2 for bad input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", required=True, type=Path, help="Labeled synthetic suite JSON")
    parser.add_argument("--output-dir", required=True, type=Path, help="New evidence directory")
    args = parser.parse_args(argv)
    try:
        with args.suite.open("rb") as handle:
            source = handle.read(10 * 1024 * 1024 + 1)
        report = assess_suite(source)
        markdown = render_assessment(report)
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / "assessment.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8"
        )
        (args.output_dir / "assessment.md").write_text(markdown, encoding="utf-8")
    except (OSError, ValueError, RecursionError) as exc:
        print(f"sentinel-assess: {exc}", file=sys.stderr)
        return 2
    print(f"Synthetic fixture conformance: {report['matched_count']}/{report['scenario_count']}")
    print(f"Evidence: {args.output_dir / 'assessment.md'}")
    return 0 if report["conformance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
