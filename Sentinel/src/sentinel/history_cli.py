"""Bounded, role-separated CLI for persistent evaluation history."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

from sentinel.history import (
    MAX_REPORT_BYTES,
    HistoryError,
    compare_history,
    get_report,
    import_comparison,
    import_suite,
    migrate,
    query_history,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel-history")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="apply forward migrations using the owner connection")
    ingest = commands.add_parser("import-suite", help="import a minimized SuiteReport")
    ingest.add_argument("--input", required=True, type=Path)
    ingest.add_argument("--suite", required=True)
    ingest.add_argument("--release", required=True)
    comparison = commands.add_parser("import-comparison", help="validate and store a comparison")
    comparison.add_argument("--input", required=True, type=Path)
    comparison.add_argument("--baseline", required=True)
    comparison.add_argument("--candidate", required=True)
    get = commands.add_parser("get", help="read a minimized suite snapshot")
    get.add_argument("--id", required=True)
    compare = commands.add_parser("compare", help="replay a release comparison without writing")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--max-regression", type=float, default=0.02)
    query = commands.add_parser("query", help="read a bounded page of history")
    query.add_argument("--suite", required=True)
    query.add_argument(
        "--view", choices=["suites", "runs", "slices", "comparisons"], default="suites"
    )
    query.add_argument("--case-id")
    query.add_argument("--tag")
    query.add_argument("--safety-only", action="store_true")
    query.add_argument("--limit", type=int, default=50)
    query.add_argument("--offset", type=int, default=0)
    return parser


def _read(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(MAX_REPORT_BYTES + 1)


def _json_value(value: object) -> str | float:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError("unsupported history output value")


def main(argv: Sequence[str] | None = None) -> int:
    """Run one command without exposing connection strings or driver diagnostics."""
    args = _parser().parse_args(argv)
    role = (
        "OWNER"
        if args.command == "migrate"
        else ("WRITER" if args.command.startswith("import-") else "READER")
    )
    variable = f"SENTINEL_HISTORY_{role}_DSN"
    dsn = os.environ.get(variable)
    if not dsn:
        print(f"sentinel-history: set {variable}", file=sys.stderr)
        return 2
    try:
        result: dict[str, Any]
        if args.command == "migrate":
            result = {"schema_version": migrate(dsn)}
        elif args.command == "import-suite":
            result = import_suite(dsn, _read(args.input), suite=args.suite, release=args.release)
        elif args.command == "import-comparison":
            result = import_comparison(
                dsn,
                _read(args.input),
                baseline_id=args.baseline,
                candidate_id=args.candidate,
            )
        elif args.command == "get":
            result = get_report(dsn, args.id)
        elif args.command == "compare":
            result = compare_history(
                dsn,
                args.baseline,
                args.candidate,
                max_regression=args.max_regression,
            )
        else:
            result = query_history(
                dsn,
                suite=args.suite,
                view=args.view,
                case_id=args.case_id,
                tag=args.tag,
                safety_only=args.safety_only,
                limit=args.limit,
                offset=args.offset,
            )
        print(json.dumps(result, default=_json_value, allow_nan=False, sort_keys=True))
        return 0
    except HistoryError as exc:
        print(f"sentinel-history: {exc}", file=sys.stderr)
    except psycopg.Error:
        print(
            "sentinel-history: database operation failed; check access and schema", file=sys.stderr
        )
    except (OSError, ValueError, RecursionError):
        print("sentinel-history: invalid input or unavailable report file", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
