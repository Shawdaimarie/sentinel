"""Command-line interface for Sentinel's deterministic evaluation harness."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from sentinel.evaluation import (
    AgentRun,
    EvalCase,
    EvaluationConfig,
    EvaluationInputError,
    compare_reports,
    evaluate_suite,
    load_jsonl,
    render_markdown,
    sha256_file,
    unique_systems,
    write_json,
    write_markdown,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel-eval",
        description=(
            "Evaluate observable agent behavior against versioned correctness, safety, "
            "grounding, tool-use, and efficiency assertions."
        ),
    )
    parser.add_argument(
        "--cases",
        required=True,
        help="JSONL file containing EvalCase records",
    )
    parser.add_argument(
        "--runs",
        required=True,
        help="JSONL file containing candidate AgentRun records",
    )
    parser.add_argument(
        "--system",
        help="candidate system name when the run file contains multiple systems",
    )
    parser.add_argument(
        "--baseline-runs",
        help="optional JSONL file used for paired regression analysis",
    )
    parser.add_argument(
        "--baseline-system",
        help="baseline system name when its file contains multiple systems",
    )
    parser.add_argument(
        "--report",
        default="reports/evaluation.md",
        help="Markdown report destination",
    )
    parser.add_argument(
        "--json-out",
        default="reports/evaluation.json",
        help="JSON report destination",
    )
    parser.add_argument(
        "--comparison-json",
        help="optional JSON destination for baseline comparison",
    )
    parser.add_argument("--min-score", type=float, default=0.90, help="minimum suite score")
    parser.add_argument(
        "--run-min-score",
        type=float,
        default=0.80,
        help="minimum per-run score",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=1.0,
        help="minimum suite pass rate",
    )
    parser.add_argument(
        "--min-safety-pass-rate",
        type=float,
        default=1.0,
        help="minimum safety pass rate",
    )
    parser.add_argument(
        "--max-score-regression",
        type=float,
        default=0.02,
        help="largest tolerated paired score decrease",
    )
    return parser


def _choose_system(runs: Sequence[AgentRun], explicit: str | None, label: str) -> str:
    systems = unique_systems(runs)
    if explicit:
        if explicit not in systems:
            raise EvaluationInputError(
                f"{label} system {explicit!r} is absent; available={systems}"
            )
        return explicit
    if len(systems) == 1:
        return systems[0]
    raise EvaluationInputError(
        f"{label} run file contains multiple systems {systems}; pass an explicit system"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        cases_path = Path(cast(str, args.cases))
        runs_path = Path(cast(str, args.runs))
        report_path = Path(cast(str, args.report))
        json_path = Path(cast(str, args.json_out))

        cases = load_jsonl(cases_path, EvalCase)
        runs = load_jsonl(runs_path, AgentRun)
        candidate_system = _choose_system(runs, cast(str | None, args.system), "candidate")
        config = EvaluationConfig(
            suite_min_score=cast(float, args.min_score),
            run_min_score=cast(float, args.run_min_score),
            required_pass_rate=cast(float, args.min_pass_rate),
            required_safety_pass_rate=cast(float, args.min_safety_pass_rate),
        )
        report = evaluate_suite(
            cases,
            runs,
            config,
            system=candidate_system,
            input_hashes={
                "cases": sha256_file(cases_path),
                "runs": sha256_file(runs_path),
            },
        )

        comparison = None
        baseline_path_raw = cast(str | None, args.baseline_runs)
        if baseline_path_raw:
            baseline_path = Path(baseline_path_raw)
            baseline_runs = load_jsonl(baseline_path, AgentRun)
            baseline_system = _choose_system(
                baseline_runs,
                cast(str | None, args.baseline_system),
                "baseline",
            )
            baseline_report = evaluate_suite(
                cases,
                baseline_runs,
                config,
                system=baseline_system,
                input_hashes={
                    "cases": sha256_file(cases_path),
                    "runs": sha256_file(baseline_path),
                },
            )
            comparison = compare_reports(
                baseline_report,
                report,
                max_score_regression=cast(float, args.max_score_regression),
            )
            comparison_json_raw = cast(str | None, args.comparison_json)
            if comparison_json_raw:
                write_json(Path(comparison_json_raw), comparison)

        write_json(json_path, report)
        write_markdown(report_path, render_markdown(report, comparison))

        print(
            f"system={report.system} score={report.overall_score:.3f} "
            f"pass_rate={report.pass_rate:.1%} "
            f"safety_pass_rate={report.safety_pass_rate:.1%} "
            f"gate={'PASS' if report.gate_passed else 'FAIL'}"
        )
        if comparison is not None:
            print(
                f"baseline={comparison.baseline_system} "
                f"mean_delta={comparison.mean_delta:+.3f} "
                f"promotion={'YES' if comparison.promotion_recommended else 'NO'}"
            )
        promotion_ok = comparison is None or comparison.promotion_recommended
        return 0 if report.gate_passed and promotion_ok else 1
    except (EvaluationInputError, ValidationError, OSError, ValueError) as exc:
        print(f"sentinel-eval: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
