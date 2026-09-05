"""Command-line reporting for deterministic coding-agent review scores."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from sentinel.code_review import (
    CRITICAL_FINDINGS,
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
CASE_CLASSES: tuple[str, ...] = (
    "safe",
    "unsafe",
    "incomplete",
    "over_engineered",
    "unverifiable",
    "unspecified",
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


def _require_text(value: object, context: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context} must be text")
    text = value.strip()
    if not allow_empty and not text:
        raise ValueError(f"{context} must not be empty")
    return text


def _result_text(result: Mapping[str, object], key: str) -> str:
    return _require_text(result.get(key), f"result field {key!r}", allow_empty=True)


def _result_score(result: Mapping[str, object]) -> float:
    return _require_number(result.get("score"), "result score")


def _result_string_list(result: Mapping[str, object], key: str) -> list[str]:
    value = result.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"result field {key!r} must be a list of text values")
    return cast(list[str], value)


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


def critical_findings_from_case(case: Mapping[str, object], case_id: str) -> list[str]:
    """Validate optional explicit hard-gate findings."""

    raw = case.get("critical_findings", [])
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"{case_id}.critical_findings must be a list of text values")
    findings = cast(list[str], raw)
    unknown = sorted(set(findings) - set(CRITICAL_FINDINGS))
    if unknown:
        joined = ", ".join(unknown)
        raise ValueError(f"{case_id}.critical_findings contains unknown values: {joined}")
    if len(findings) != len(set(findings)):
        raise ValueError(f"{case_id}.critical_findings must not contain duplicates")
    return findings


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
    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        case_id = _require_text(case.get("id", f"case-{index}"), f"case {index}.id")
        if case_id in seen_ids:
            raise ValueError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)

        summary = _require_text(
            case.get("summary", ""),
            f"{case_id}.summary",
            allow_empty=True,
        )
        case_class = _require_text(
            case.get("case_class", "unspecified"),
            f"{case_id}.case_class",
        )
        if case_class not in CASE_CLASSES:
            joined = ", ".join(CASE_CLASSES)
            raise ValueError(f"{case_id}.case_class must be one of: {joined}")

        scores = scores_from_mapping(_require_mapping(case.get("scores"), f"{case_id}.scores"))
        critical_findings = critical_findings_from_case(case, case_id)
        review = score_code_review(scores, critical_findings=critical_findings)

        expected_raw = case.get("expected_decision")
        expected = (
            _require_text(expected_raw, f"{case_id}.expected_decision")
            if expected_raw is not None
            else None
        )
        if expected is not None and expected not in DECISIONS:
            joined = ", ".join(DECISIONS)
            raise ValueError(f"{case_id}.expected_decision must be one of: {joined}")

        result: dict[str, object] = {
            "id": case_id,
            "case_class": case_class,
            "summary": summary,
            "score": review.score,
            "decision": review.decision,
            "reviewer_action": review.reviewer_action,
            "reviewer_action_text": review.reviewer_action_text,
            "passed": review.passed,
            "dimension_scores": {
                item.dimension: round(item.score, 4) for item in review.dimension_scores
            },
            "failing_dimensions": list(review.failing_dimensions),
            "hard_failures": list(review.hard_failures),
            "critical_findings": list(review.critical_findings),
            "decisive_failure_modes": list(review.decisive_failure_modes),
        }
        if expected is not None:
            result["expected_decision"] = expected
            result["expected_matched"] = expected == review.decision
        results.append(result)
    return results


def report_payload(
    results: Sequence[Mapping[str, object]],
    *,
    source_sha256: str,
) -> dict[str, object]:
    """Build the machine-readable scorecard report."""

    decision_counts: dict[str, int] = {decision: 0 for decision in DECISIONS}
    critical_finding_counts: dict[str, int] = {finding: 0 for finding in CRITICAL_FINDINGS}
    all_expected_matched = True
    for result in results:
        decision = _result_text(result, "decision")
        decision_counts[decision] += 1
        for finding in _result_string_list(result, "critical_findings"):
            critical_finding_counts[finding] += 1
        if result.get("expected_matched") is False:
            all_expected_matched = False

    return {
        "schema_version": "sentinel.code_review_report.v2",
        "source_sha256": source_sha256,
        "case_count": len(results),
        "decision_counts": decision_counts,
        "critical_finding_counts": {
            key: value for key, value in critical_finding_counts.items() if value > 0
        },
        "all_expected_matched": all_expected_matched,
        "results": list(results),
    }


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def markdown_report(results: Sequence[Mapping[str, object]]) -> str:
    """Render evaluated cases as a reviewer-oriented Markdown report."""

    decision_counts = {decision: 0 for decision in DECISIONS}
    for result in results:
        decision_counts[_result_text(result, "decision")] += 1

    lines = [
        "# Coding Agent Review Scorecard Report",
        "",
        f"- Cases evaluated: **{len(results)}**",
        "- Decisions: "
        + ", ".join(f"{decision}={count}" for decision, count in decision_counts.items()),
        "",
        "| Case | Class | Score | Decision | Reviewer action | Decisive failure modes |",
        "|---|---|---:|---|---|---|",
    ]
    for result in results:
        decisive = ", ".join(_result_string_list(result, "decisive_failure_modes")) or "none"
        lines.append(
            "| {case} | {case_class} | {score:.4f} | {decision} | {action} | {decisive} |".format(
                case=_markdown_cell(_result_text(result, "id")),
                case_class=_markdown_cell(_result_text(result, "case_class")),
                score=_result_score(result),
                decision=_markdown_cell(_result_text(result, "decision")),
                action=_markdown_cell(_result_text(result, "reviewer_action")),
                decisive=_markdown_cell(decisive),
            )
        )

    lines.append("")
    for result in results:
        lines.extend(
            [
                f"## `{_result_text(result, 'id')}`",
                "",
                _result_text(result, "summary") or "No summary supplied.",
                "",
                f"- **Class:** `{_result_text(result, 'case_class')}`",
                f"- **Decision:** `{_result_text(result, 'decision')}`",
                f"- **Reviewer action:** {_result_text(result, 'reviewer_action_text')}",
                "- **Decisive failure modes:** "
                + (", ".join(_result_string_list(result, "decisive_failure_modes")) or "none"),
                "- **Critical findings:** "
                + (", ".join(_result_string_list(result, "critical_findings")) or "none"),
                "",
                "| Dimension | Score | Status |",
                "|---|---:|---|",
            ]
        )
        score_mapping = _require_mapping(result.get("dimension_scores"), "dimension_scores")
        failing = set(_result_string_list(result, "failing_dimensions"))
        for dimension in DIMENSIONS:
            dimension_score = _require_number(score_mapping.get(dimension), dimension)
            status = "needs review" if dimension in failing else "pass"
            lines.append(f"| {dimension} | {dimension_score:.4f} | {status} |")
        lines.append("")
    return "\n".join(lines)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        source_bytes = args.cases.read_bytes()
        results = evaluate_cases(load_cases(args.cases))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))

    payload = report_payload(
        results,
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
    )
    json_text = json.dumps(payload, indent=2, sort_keys=True)
    if args.json_out is not None:
        _write_text(args.json_out, json_text + "\n")
    else:
        print(json_text)

    if args.markdown_out is not None:
        _write_text(args.markdown_out, markdown_report(results))

    expected_mismatches = [
        _result_text(result, "id")
        for result in results
        if result.get("expected_matched") is False
    ]
    threshold_failures = [
        _result_text(result, "id")
        for result in results
        if _result_score(result) < args.min_score
    ]
    if expected_mismatches or threshold_failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
