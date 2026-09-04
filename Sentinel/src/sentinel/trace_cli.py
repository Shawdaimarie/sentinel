"""CLI for deterministic OpenTelemetry-to-AgentRun normalization."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from sentinel.trace_import import (
    TraceImportConfig,
    TraceImportError,
    import_otel_path,
    write_manifest,
    write_runs_jsonl,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-import-otel",
        description=(
            "Normalize an offline OTLP JSON trace export into Sentinel AgentRun JSONL "
            "without executing trace content or contacting provider endpoints."
        ),
    )
    parser.add_argument("--input", required=True, help="OTLP JSON export")
    parser.add_argument("--output", required=True, help="AgentRun JSONL destination")
    parser.add_argument(
        "--manifest",
        default="reports/otel-import-manifest.json",
        help="reproducibility and redaction manifest destination",
    )
    parser.add_argument(
        "--system",
        default="candidate",
        help="fallback system name when the trace omits sentinel.system/service.name",
    )
    parser.add_argument(
        "--case-id",
        help="override case id for all imported traces",
    )
    parser.add_argument(
        "--redact",
        action="append",
        default=[],
        metavar="ATTRIBUTE",
        help="additional attribute key to redact; repeat as needed",
    )
    parser.add_argument(
        "--metadata-limit",
        type=int,
        default=32,
        help="maximum unknown attributes retained per run or action",
    )
    parser.add_argument(
        "--metadata-value-limit",
        type=int,
        default=256,
        help="maximum retained metadata string length",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = TraceImportConfig(
            system=cast(str, args.system),
            case_id=cast(str | None, args.case_id),
            additional_redactions=frozenset(cast(list[str], args.redact)),
            max_metadata_entries=cast(int, args.metadata_limit),
            max_metadata_value_length=cast(int, args.metadata_value_limit),
        )
        result = import_otel_path(Path(cast(str, args.input)), config)
        write_runs_jsonl(Path(cast(str, args.output)), result.runs)
        write_manifest(Path(cast(str, args.manifest)), result.manifest)
        print(
            f"traces={result.manifest.trace_count} runs={result.manifest.run_count} "
            f"partial={result.manifest.partial_runs} "
            f"redactions={result.manifest.redacted_attribute_count} "
            f"source_sha256={result.manifest.source_sha256}"
        )
        return 0
    except (TraceImportError, ValidationError, OSError, ValueError) as exc:
        print(f"sentinel-import-otel: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
