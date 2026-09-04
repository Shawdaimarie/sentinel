"""Command-line reporting for deterministic coding-agent review scores."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from sentinel.code_review import (
    DIMENSIONS,
    DecisionLabel,
    DimensionScore,
    ReviewDimension,
    score_code_review,
)

DECISIONS: tuple[DecisionLabel, ...] = (
    "accept",
    "accept_with_edits",
    "needs_human_design",
    "reject",
)


def _require_mapping(value: object, context: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return cast(Mapping[str, object], value)


def _require_number(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{context} must be a number in [0.0, 1.0]")
    number = float(value)
    if number < 0.0 or number > 1.0:
        raise ValueError(f"{context} must be in [0.0, 1.0]")
    return number


def _review_dimension(value: str) -> ReviewDimension:
    if value not in DIMENSIONS:
        joined = ", ".join(DIMENSIONS)
        raise ValueError(f"unknown review dimension {value!r}; expected one of: {joined}")
    return cast(ReviewDimension, value)


def scores_from_mapping(scores: Mapping[str, object]) -> list[DimensionScore]:
    """Convert a JSON score object into ordered review dimensions."""

    converted: list[DimensionScore] = []
    for dimension in DIMENSIONS:
        if dimension not in scores:
            raise ValueError(f"missing review dimension: {dimension}")
        score = _require_number(scores[dimension], f"score for {dimension}")
        converted.append(DimensionScore(dimension=_review_dimension(dimension), score=score))
    extra = sorted(set(scores) - set(DIMENSIONS))
    if extra:
        joined = ", ".join(extra)
        raise ValueError(f"unknown review dimensions: {joined}")
    return converted


def load_cases(path: Path) -> list[Mapping[str, object]]:
    """Load a JSON array of code-review scoring cases."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("case file must contain a JSON array")

    cases: list[Mapping[str, object]] = []
    for index, item in enumerate(data, start=1):
        cases.append(_require_mapping(item, f"case {index}"))
    return cases


def evaluate_cases(cases: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Evaluate review cases and return JSON-serializable result records."""

    results: list[dict[str, object]] = []
    for index, case in enumerate(cases, start=1):
        case_id = str(case.get("id", f"case-{index}"))
        scores = scores_from_mapping(_require_mapping(case.get("scores"), f"{case_id}.scores"))
        review = score_code_review(scores)

        expected_raw = case.get("expected_decision")
        expected = str(expected_raw) if expected_raw is not None else None
        if expected is not None and expected not in DECISIONS:
            joined = ", ".join(DECISIONS)
            raise ValueError(f"{case_id}.expected_decision must be one of: {joined}")

        result: dict[str, object] = {
            "id": case_id,
            "score": review.score,
            "decision": review.decision,
            "passed": review.passed,
            "failing_dimensions": list(review.failing_dimensions),
            "hard_failures": list(review.hard_failures),
        }
        if expected is not None:
            result["expected_decision"] = expected
            result["expected_matched"] = expected == review.decision
        results.append(result)
    return results


def markdown_report(results: Sequence[Mapping[str, object]]) -> str:
    """Render evaluated cases as a compact Markdown report."""

    lines = [
        "# Coding Agent Review Scorecard Report",
        "",
        "| Case | Score | Decision | Failing dimensions | Hard failures |",
        "|---|---:|---|---|---|",
    ]
    for result in results:
        failures = ", ".join(cast(list[str], result.get("failing_dimensions", []))) or "none"
        hard_failures = ", ".join(cast(list[str], result.get("hard_failures", []))) or "none"
        lines.append(
            "| {case} | {score:.4f} | {decision} | {failures} | {hard_failures} |".format(
                case=result["id"],
                score=float(result["score"]),
                decision=result["decision"],
                failures=failures,
                hard_failures=hard_failures,
            )
        )
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Score coding-agent review cases with deterministic decision labels."
    )
    parser.add_argument("--cases", required=True, type=Path, help="Path to JSON case array.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON report path.")
    parser.add_argument("--markdown-out", type=Path, help="Optional Markdown report path.")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.0,
        help="Fail when any case score is below this threshold.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.min_score < 0.0 or args.min_score > 1.0:
            raise ValueError("--min-score must be in [0.0, 1.0]")
        results = evaluate_cases(load_cases(args.cases))
    except ValueError as exc:
        parser.error(str(exc))

    payload = {"schema_version": "sentinel.code_review.v1", "results": results}
    json_text = json.dumps(payload, indent=2, sort_keys=True)
    if args.json_out is not None:
        args.json_out.write_text(json_text + "\n", encoding="utf-8")
    else:
        print(json_text)

    if args.markdown_out is not None:
        args.markdown_out.write_text(markdown_report(results), encoding="utf-8")

    expected_mismatches = [
        result["id"] for result in results if result.get("expected_matched") is False
    ]
    threshold_failures = [
        result["id"] for result in results if float(result["score"]) < args.min_score
    ]
    if expected_mismatches or threshold_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
