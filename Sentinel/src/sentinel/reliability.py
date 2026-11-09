"""Offline repeated-trial assessment with conservative case-level uncertainty."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sentinel.evaluation import (
    AgentRun,
    ComparisonReport,
    EvalCase,
    EvaluationConfig,
    EvaluationInputError,
    RunEvaluation,
    SuiteReport,
    compare_reports,
    evaluate_suite,
)

Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
MAX_INPUT_BYTES = 10 * 1024 * 1024


class ReliabilityManifest(BaseModel):
    """Predeclared trial grid, provenance, and evidence requirements."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    schema_version: Literal["sentinel.reliability-manifest.v1"]
    assessment_id: Identifier
    case_ids: list[Identifier] = Field(min_length=1, max_length=10_000)
    trial_ids: list[Identifier] = Field(min_length=2, max_length=1_000)
    candidate_system: Identifier
    baseline_system: Identifier | None = None
    cases_sha256: Digest
    candidate_sha256: Digest
    baseline_sha256: Digest | None = None
    evidence_kind: Literal["synthetic", "operational"]
    independent_case_sampling: bool = False
    sampling_description: str = Field(min_length=1, max_length=4_000)
    source_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    model_version: str = Field(min_length=1, max_length=512)
    prompt_version: str = Field(min_length=1, max_length=512)
    tool_version: str = Field(min_length=1, max_length=512)
    runtime_version: str = Field(min_length=1, max_length=512)
    confidence_level: float = Field(default=0.95, ge=0.80, le=0.999)
    required_pass_rate: float = Field(default=0.90, gt=0.0, le=1.0)
    minimum_cases: int = Field(default=20, ge=2, le=10_000)
    maximum_score_regression: float = Field(default=0.02, ge=0.0, le=1.0)
    evaluation_config: EvaluationConfig = Field(default_factory=EvaluationConfig)

    @model_validator(mode="after")
    def validate_design(self) -> ReliabilityManifest:
        """Reject ambiguous sampling grids and unpaired baseline declarations."""
        for name, values in (("case_ids", self.case_ids), ("trial_ids", self.trial_ids)):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {name}")
        if len(self.case_ids) * len(self.trial_ids) > 100_000:
            raise ValueError("trial grid exceeds 100000 observations per system")
        if (self.baseline_system is None) != (self.baseline_sha256 is None):
            raise ValueError("baseline system and digest must be declared together")
        if self.baseline_system == self.candidate_system:
            raise ValueError("baseline and candidate systems must differ")
        for value in (
            self.sampling_description,
            self.model_version,
            self.prompt_version,
            self.tool_version,
            self.runtime_version,
        ):
            if not value.strip():
                raise ValueError("provenance and sampling descriptions must not be blank")
        return self


class MeanInterval(BaseModel):
    """A bounded-mean Hoeffding interval using independent cases, not runs."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    method: Literal["case-level-hoeffding"] = "case-level-hoeffding"
    mean: float
    lower: float
    upper: float
    confidence_level: float
    independent_units: int


class CaseReliability(BaseModel):
    """Descriptive repetition results; absent trials are never successes."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    case_id: str
    observed_trials: int
    expected_trials: int
    passed_trials: int
    observed_pass_rate: float | None
    missing_trial_ids: list[str]


class ReliabilityReport(BaseModel):
    """Replayable evidence; this report never grants execution authority."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal["sentinel.reliability-assessment.v1"] = (
        "sentinel.reliability-assessment.v1"
    )
    manifest: ReliabilityManifest
    input_hashes: dict[str, str]
    status: Literal["pass", "fail", "inconclusive"]
    promotion_recommended: bool
    reasons: list[str]
    cases: list[CaseReliability]
    candidate: SuiteReport
    baseline: SuiteReport | None
    comparison: ComparisonReport | None
    pass_rate_interval: MeanInterval | None
    paired_pass_rate_delta: MeanInterval | None
    interpretation: str = (
        "Equal-weight case means; repeated trials within a case are not independent "
        "sampling units. Bounds require independently sampled representative cases "
        "and a fixed design. Sampling declarations are not independently verified. "
        "A pass is evidence for this declared scope, not universal safety."
    )


def bounded_mean_interval(
    values: list[float], confidence_level: float, *, lower: float = 0.0, upper: float = 1.0
) -> MeanInterval:
    """Two-sided fixed-sample Hoeffding bound for independent bounded means."""
    if not values:
        raise ValueError("at least one independent case is required")
    if not (math.isfinite(lower) and math.isfinite(upper) and lower < upper):
        raise ValueError("invalid support")
    if not math.isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise ValueError("confidence must be between zero and one")
    if any(not math.isfinite(value) or not lower <= value <= upper for value in values):
        raise ValueError("observations must be finite and within support")
    mean = statistics.fmean(values)
    radius = (upper - lower) * math.sqrt(math.log(2 / (1 - confidence_level)) / (2 * len(values)))
    return MeanInterval(
        mean=mean,
        lower=max(lower, mean - radius),
        upper=min(upper, mean + radius),
        confidence_level=confidence_level,
        independent_units=len(values),
    )


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON constant: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number")
    return parsed


def _decode(source: bytes) -> str:
    if len(source) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 10 MiB")
    return source.decode("utf-8")


def _json(source: str) -> object:
    return json.loads(
        source,
        object_pairs_hook=_no_duplicates,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )


def _digest(source: bytes) -> str:
    return hashlib.sha256(source).hexdigest()


def _runs(source: bytes, system: str, manifest: ReliabilityManifest) -> list[AgentRun]:
    runs = [
        AgentRun.model_validate(_json(line), strict=True)
        for line in _decode(source).splitlines()
        if line.strip()
    ]
    seen: set[tuple[str, str]] = set()
    allowed_cases, allowed_trials = set(manifest.case_ids), set(manifest.trial_ids)
    for run in runs:
        key = (run.case_id, run.run_id)
        if run.system != system:
            raise EvaluationInputError("unexpected system; mixed-system files are not allowed")
        if run.case_id not in allowed_cases or run.run_id not in allowed_trials:
            raise EvaluationInputError("run outside declared case/trial grid")
        if key in seen:
            raise EvaluationInputError("duplicate case/trial observation")
        if not math.isfinite(run.cost_usd) or any(
            not math.isfinite(action.cost_usd) for action in run.actions
        ):
            raise EvaluationInputError("cost must be finite")
        seen.add(key)
    return runs


def assess_reliability(
    manifest_source: bytes,
    cases_source: bytes,
    candidate_source: bytes,
    baseline_source: bytes | None = None,
) -> ReliabilityReport:
    """Validate exact artifacts, recompute evaluation, then assess uncertainty."""
    manifest = ReliabilityManifest.model_validate(_json(_decode(manifest_source)))
    sources = {"cases": cases_source, "candidate": candidate_source}
    expected = {"cases": manifest.cases_sha256, "candidate": manifest.candidate_sha256}
    if (baseline_source is None) != (manifest.baseline_system is None):
        raise EvaluationInputError("baseline artifact must match manifest declaration")
    if baseline_source is not None and manifest.baseline_sha256 is not None:
        sources["baseline"] = baseline_source
        expected["baseline"] = manifest.baseline_sha256
    hashes = {"manifest": _digest(manifest_source)}
    for name, source in sources.items():
        _decode(source)
        hashes[name] = _digest(source)
        if hashes[name] != expected[name]:
            raise EvaluationInputError(f"{name} SHA-256 mismatch")
    cases = [
        EvalCase.model_validate(_json(line), strict=True)
        for line in _decode(cases_source).splitlines()
        if line.strip()
    ]
    if len(cases) != len(manifest.case_ids) or {case.id for case in cases} != set(
        manifest.case_ids
    ):
        raise EvaluationInputError("case artifact must exactly match manifest case IDs")
    cases.sort(key=lambda case: case.id)
    candidate_runs = _runs(candidate_source, manifest.candidate_system, manifest)
    candidate = evaluate_suite(
        cases,
        candidate_runs,
        manifest.evaluation_config,
        system=manifest.candidate_system,
        input_hashes=hashes,
    )
    # No wall clock in replayed evidence: provenance is the immutable input hash set.
    candidate.generated_at = "replayed-from-hashed-inputs"
    observed = {(run.case_id, run.run_id) for run in candidate_runs}
    actual_results = [r for r in candidate.results if (r.case_id, r.run_id) in observed]
    by_case: dict[str, list[RunEvaluation]] = defaultdict(list)
    for result in actual_results:
        by_case[result.case_id].append(result)
    summaries: list[CaseReliability] = []
    for case in cases:
        results = by_case[case.id]
        passed = sum(r.passed for r in results)
        summaries.append(
            CaseReliability(
                case_id=case.id,
                observed_trials=len(results),
                expected_trials=len(manifest.trial_ids),
                passed_trials=passed,
                observed_pass_rate=passed / len(results) if results else None,
                missing_trial_ids=sorted(
                    t for t in manifest.trial_ids if (case.id, t) not in observed
                ),
            )
        )
    complete = all(not item.missing_trial_ids for item in summaries)
    failures = [
        f"{r.case_id}/{r.run_id}: {failure}" for r in actual_results for failure in r.hard_failures
    ]
    if any(not r.safety_passed for r in actual_results):
        failures.append("observed safety failure")
    gaps: list[str] = []
    if not complete:
        gaps.append("candidate trial grid is incomplete")
    elif not candidate.gate_passed:
        failures.extend(candidate.gate_failures)
    baseline: SuiteReport | None = None
    comparison: ComparisonReport | None = None
    if baseline_source is not None and manifest.baseline_system is not None:
        baseline_runs = _runs(baseline_source, manifest.baseline_system, manifest)
        baseline = evaluate_suite(
            cases,
            baseline_runs,
            manifest.evaluation_config,
            system=manifest.baseline_system,
            input_hashes=hashes,
        )
        baseline.generated_at = "replayed-from-hashed-inputs"
        baseline_keys = {(run.case_id, run.run_id) for run in baseline_runs}
        baseline_complete = len(baseline_keys) == len(cases) * len(manifest.trial_ids)
        if not baseline_complete:
            gaps.append("baseline trial grid is incomplete; no paired comparison")
        if baseline_complete and complete:
            comparison = compare_reports(
                baseline,
                candidate,
                max_score_regression=manifest.maximum_score_regression,
            )
            failures.extend(
                f"paired regression: {r.case_id}/{r.run_id}: {r.reason}"
                for r in comparison.regressions
            )
    if manifest.evidence_kind == "synthetic":
        gaps.append("synthetic evidence cannot establish operational reliability")
    if not manifest.independent_case_sampling:
        gaps.append("independent representative case sampling is not declared")
    if len(cases) < manifest.minimum_cases:
        gaps.append(f"insufficient cases: {len(cases)} < {manifest.minimum_cases}")
    interval: MeanInterval | None = None
    delta: MeanInterval | None = None
    if not gaps:
        # Bonferroni allocation gives joint coverage for both reported bounds.
        interval_confidence = 1 - (1 - manifest.confidence_level) / (2 if baseline else 1)
        rates = [item.passed_trials / item.expected_trials for item in summaries]
        interval = bounded_mean_interval(rates, interval_confidence)
        if baseline is not None:
            before: dict[str, int] = defaultdict(int)
            for result in baseline.results:
                before[result.case_id] += int(result.passed)
            delta = bounded_mean_interval(
                [
                    rate - before[item.case_id] / item.expected_trials
                    for item, rate in zip(summaries, rates, strict=True)
                ],
                interval_confidence,
                lower=-1.0,
                upper=1.0,
            )
        if interval.upper < manifest.required_pass_rate:
            failures.append("pass-rate upper bound is below the declared target")
        elif interval.lower < manifest.required_pass_rate:
            gaps.append("pass-rate lower bound does not establish the declared target")
    status: Literal["pass", "fail", "inconclusive"] = (
        "fail" if failures else "inconclusive" if gaps else "pass"
    )
    return ReliabilityReport(
        manifest=manifest,
        input_hashes=hashes,
        status=status,
        promotion_recommended=status == "pass",
        reasons=failures + gaps,
        cases=summaries,
        candidate=candidate,
        baseline=baseline,
        comparison=comparison,
        pass_rate_interval=interval,
        paired_pass_rate_delta=delta,
    )


def render_reliability(report: ReliabilityReport) -> str:
    """Render evidence status and missingness without hiding failures."""
    lines = [
        "# Sentinel repeated-trial reliability assessment",
        "",
        f"**Status: {report.status.upper()}**",
        "",
        report.interpretation,
        "",
        f"Evidence kind: {report.manifest.evidence_kind}",
        "",
        "## Decision reasons",
        "",
    ]
    for reason in report.reasons:
        # Encode all punctuation, including Markdown/HTML controls and newlines.
        escaped = "".join(
            char if char.isalnum() or char == " " else f"&#{ord(char)};" for char in reason
        )
        lines.append(f"- {escaped}")
    if not report.reasons:
        lines.append("All declared gates satisfied for this assessment scope.")
    lines.extend(
        [
            "",
            "## Repeated cases",
            "",
            "| Case | Observed | Expected | Passed | Missing trials |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in report.cases:
        lines.append(
            f"| {item.case_id} | {item.observed_trials} | {item.expected_trials} | "
            f"{item.passed_trials} | {', '.join(item.missing_trial_ids) or 'none'} |"
        )
    lines.extend(["", "## Uncertainty", ""])
    for label, interval in (
        ("Pass rate", report.pass_rate_interval),
        ("Paired pass-rate delta", report.paired_pass_rate_delta),
    ):
        if interval is not None:
            lines.append(
                f"{label}: {interval.mean:.6f}; "
                f"{interval.confidence_level:.3%} interval "
                f"[{interval.lower:.6f}, {interval.upper:.6f}]; "
                f"{interval.independent_units} independent cases.\n"
            )
    if report.pass_rate_interval is None:
        lines.append("No inferential interval: evidence prerequisites are not met.")
    lines.extend(["", "## Exact input fingerprints", ""])
    lines.extend(f"- {name}: `{digest}`" for name, digest in sorted(report.input_hashes.items()))
    return "\n".join(lines) + "\n"
