"""Descriptive repeated-run diagnostics; never an authorization or promotion gate."""

from __future__ import annotations

import statistics
from collections import defaultdict

from pydantic import BaseModel, ConfigDict

from sentinel.evaluation import RunEvaluation, SuiteReport


class CaseTrials(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    run_ids: list[str]
    sample_count: int
    missing_run_count: int
    mean_score: float | None
    median_score: float | None
    sample_stddev_score: float | None
    min_score: float | None
    max_score: float | None
    failed_runs: int
    safety_failed_runs: int
    failure_rate: float | None
    safety_failure_rate: float | None
    all_observed_runs_safe: bool
    warnings: list[str]


class TrialReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "sentinel.trials.v1"
    system: str
    input_hashes: dict[str, str]
    evaluation_gate_passed: bool
    cases: list[CaseTrials]
    limitations: list[str]


def summarize_trials(report: SuiteReport) -> TrialReport:
    """Summarize each case separately so unequal sample counts do not hide failures.

    Use an in-process evaluate_suite result. Run IDs identify observations, not
    independent samples; callers must keep model/configuration fixed per system.
    """
    grouped: dict[str, list[RunEvaluation]] = defaultdict(list)
    for result in report.results:
        grouped[result.case_id].append(result)
    summaries: list[CaseTrials] = []
    for case_id, results in sorted(grouped.items()):
        observed = sorted(
            (item for item in results if item.hard_failures != ["missing run"]),
            key=lambda item: item.run_id,
        )
        scores = [item.score for item in observed]
        count = len(scores)
        missing = len(results) - count
        failures = sum(not item.passed for item in observed)
        safety_failures = sum(not item.safety_passed for item in observed)
        warnings = []
        if count < 2:
            warnings.append("Fewer than two observed runs; sample dispersion is unavailable.")
        if missing:
            warnings.append("Missing-run placeholders are failures, not observed trials.")
        if safety_failures:
            warnings.append("Observed safety failures remain failures regardless of mean score.")
        summaries.append(
            CaseTrials(
                case_id=case_id,
                run_ids=[item.run_id for item in observed],
                sample_count=count,
                missing_run_count=missing,
                mean_score=statistics.fmean(scores) if scores else None,
                median_score=statistics.median(scores) if scores else None,
                sample_stddev_score=statistics.stdev(scores) if count > 1 else None,
                min_score=min(scores) if scores else None,
                max_score=max(scores) if scores else None,
                failed_runs=failures,
                safety_failed_runs=safety_failures,
                failure_rate=failures / count if count else None,
                safety_failure_rate=safety_failures / count if count else None,
                all_observed_runs_safe=bool(count) and not safety_failures and not missing,
                warnings=warnings,
            )
        )
    return TrialReport(
        system=report.system,
        input_hashes=dict(report.input_hashes),
        evaluation_gate_passed=report.gate_passed,
        cases=summaries,
        limitations=[
            "Descriptive statistics only; no confidence intervals or independence claim.",
            "Run IDs do not prove distinct executions, model versions, settings, or seeds.",
            "Keep model and configuration fixed per system; small samples can miss rare failures.",
            "This report grants no execution or release approval and changes no evaluation gates.",
        ],
    )
