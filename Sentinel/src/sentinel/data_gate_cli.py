"""Command-line interface for Sentinel training-data quality gates."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from sentinel.data_gate import (
    DataGateInputError,
    DatasetGateConfig,
    evaluate_file,
    report_payload,
    write_json,
    write_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-data-gate",
        description=(
            "Validate AI training and evaluation datasets for structure, source notes, "
            "privacy posture, split hygiene, and risk coverage."
        ),
    )
    parser.add_argument("--input", required=True, type=Path, help="Training dataset JSONL file.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON report path.")
    parser.add_argument("--markdown-out", type=Path, help="Optional Markdown report path.")
    parser.add_argument(
        "--allow-private",
        action="store_true",
        help="Allow examples that are not marked safe for public release.",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Return a failing status when warnings are present.",
    )
    parser.add_argument(
        "--min-examples",
        type=int,
        default=1,
        help="Minimum number of valid examples required.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = DatasetGateConfig(
            public_release_required=not args.allow_private,
            min_examples=args.min_examples,
            fail_on_warnings=args.fail_on_warnings,
        )
        report = evaluate_file(args.input, config)
    except (DataGateInputError, OSError, ValueError) as exc:
        print(f"sentinel-data-gate: {exc}", file=sys.stderr)
        return 2

    if args.json_out is not None:
        write_json(args.json_out, report)
    else:
        print(json.dumps(report_payload(report), indent=2, sort_keys=True))

    if args.markdown_out is not None:
        write_markdown(args.markdown_out, report)

    summary_stream = sys.stderr if args.json_out is None else sys.stdout
    print(
        f"rows={report.row_count} valid={report.valid_row_count} "
        f"hard_failures={len(report.hard_failures)} warnings={len(report.warnings)} "
        f"gate={'PASS' if report.passed else 'FAIL'}",
        file=summary_stream,
    )
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
