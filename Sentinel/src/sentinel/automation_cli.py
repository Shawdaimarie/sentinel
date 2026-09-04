"""Command-line entry point for Sentinel stability automation."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from sentinel.automation import (
    load_catalog,
    markdown_report,
    required_failures,
    result_payload,
    run_catalog,
)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description="Run allowlisted, benefit-gated Sentinel automation tasks."
    )
    parser.add_argument("--catalog", required=True, type=Path, help="JSON automation catalog.")
    parser.add_argument("--cwd", type=Path, default=Path("."), help="Working directory for tasks.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON report path.")
    parser.add_argument("--markdown-out", type=Path, help="Optional Markdown report path.")
    parser.add_argument(
        "--min-benefit-score",
        type=float,
        default=0.85,
        help="Skip tasks below this declared leverage/benefit threshold.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run eligible automated tasks instead of only planning them.",
    )
    return parser


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the automation catalog and return a process exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        tasks = load_catalog(args.catalog)
        results = run_catalog(
            tasks,
            cwd=args.cwd,
            execute=args.execute,
            min_benefit_score=args.min_benefit_score,
        )
    except ValueError as exc:
        parser.error(str(exc))

    payload = result_payload(results, min_benefit_score=args.min_benefit_score)
    json_text = json.dumps(payload, indent=2, sort_keys=True)
    markdown_text = markdown_report(results, min_benefit_score=args.min_benefit_score)

    if args.json_out is not None:
        _write_text(args.json_out, json_text + "\n")
    else:
        print(json_text)

    if args.markdown_out is not None:
        _write_text(args.markdown_out, markdown_text)

    failures = required_failures(results) if args.execute else []
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
