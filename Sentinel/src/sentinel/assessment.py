"""Offline conformance demonstration for labeled synthetic agent traces.

Expected labels are compared with observations after import and evaluation.
They never determine the observed outcome or alter the evaluation thresholds.
"""

from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sentinel import evaluation, trace_import
from sentinel.evaluation import EvalCase, EvaluationConfig, evaluate_suite
from sentinel.trace_import import TraceImportError, import_otel_document

Outcome = Literal["pass", "fail", "reject"]
Category = Literal["completeness", "retries", "authorization", "evaluation"]


class ActionExpectation(BaseModel):
    """Expected ordered action identity, status, and retry attempt."""

    model_config = ConfigDict(extra="forbid")
    name: str
    status: Literal["proposed", "allowed", "denied", "executed", "failed"]
    attempt: int = Field(ge=1)


class AssessmentScenario(BaseModel):
    """One synthetic trace with independently declared expected behavior."""

    model_config = ConfigDict(extra="forbid")
    category: Category
    rationale: str = Field(min_length=1)
    case: EvalCase
    trace: dict[str, Any]
    expected_outcome: Outcome
    expected_diagnostics: list[str] = Field(default_factory=list)
    expected_missing_fields: list[str] = Field(default_factory=list)
    expected_actions: list[ActionExpectation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_failure_evidence(self) -> AssessmentScenario:
        if self.expected_outcome != "pass" and not self.expected_diagnostics:
            raise ValueError("negative scenarios require expected diagnostics")
        if any(not text.strip() for text in self.expected_diagnostics):
            raise ValueError("expected diagnostics must not be blank")
        return self


class AssessmentSuite(BaseModel):
    """Versioned synthetic conformance suite, not a production safety benchmark."""

    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["sentinel.assessment.suite.v1"]
    synthetic: Literal[True]
    provenance: str = Field(min_length=1)
    config: EvaluationConfig = Field(default_factory=EvaluationConfig)
    scenarios: list[AssessmentScenario] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def _unique_cases(self) -> AssessmentSuite:
        ids = [scenario.case.id for scenario in self.scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError("scenario case ids must be unique")
        return self


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _scenario_result(
    scenario: AssessmentScenario, config: EvaluationConfig
) -> dict[str, Any]:
    source = _canonical(scenario.trace)
    evidence: dict[str, Any] = {}
    mismatches: list[str] = []
    try:
        imported = import_otel_document(scenario.trace, source_bytes=source)
    except TraceImportError as exc:
        outcome: Outcome = "reject"
        diagnostics = [str(exc)]
        if scenario.expected_actions or scenario.expected_missing_fields:
            mismatches.append("import rejected before expected trace evidence was available")
    else:
        if len(imported.runs) != 1 or imported.runs[0].case_id != scenario.case.id:
            raise ValueError(f"{scenario.case.id}: scenario must import exactly its own case")
        report = evaluate_suite([scenario.case], imported.runs, config)
        outcome = "pass" if report.gate_passed else "fail"
        result = report.results[0]
        diagnostics = [
            *result.hard_failures,
            *(metric.detail for metric in result.metrics if not metric.passed),
            *report.gate_failures,
        ]
        trace = imported.manifest.traces[0]
        observed_actions = [
            ActionExpectation(name=action.name, status=action.status, attempt=action.attempt)
            for action in trace.actions
        ]
        if observed_actions != scenario.expected_actions:
            mismatches.append("ordered actions or retry attempts differ from expected evidence")
        if sorted(trace.missing_fields) != sorted(scenario.expected_missing_fields):
            mismatches.append("missing telemetry fields differ from expected evidence")
        evidence = {
            "manifest": imported.manifest.model_dump(mode="json"),
            "evaluation": report.model_dump(mode="json", exclude={"generated_at"}),
        }
    if outcome != scenario.expected_outcome:
        mismatches.append(f"expected {scenario.expected_outcome}, observed {outcome}")
    for expected in scenario.expected_diagnostics:
        if not any(expected in observed for observed in diagnostics):
            mismatches.append(f"expected diagnostic absent: {expected}")
    return {
        "case_id": scenario.case.id,
        "category": scenario.category,
        "rationale": scenario.rationale,
        "source_sha256": _digest(source),
        "expected_outcome": scenario.expected_outcome,
        "observed_outcome": outcome,
        "matched": not mismatches,
        "diagnostics": diagnostics,
        "mismatches": mismatches,
        **evidence,
    }


def assess_suite(source: bytes) -> dict[str, Any]:
    """Evaluate a bounded suite and preserve every mismatch in a stable report."""
    if len(source) > 10 * 1024 * 1024:
        raise ValueError("assessment suite exceeds the 10 MiB limit")
    suite = AssessmentSuite.model_validate_json(source)
    results = [_scenario_result(scenario, suite.config) for scenario in suite.scenarios]
    matched = sum(result["matched"] for result in results)
    return {
        "schema_version": "sentinel.assessment.report.v1",
        "synthetic": True,
        "provenance": suite.provenance,
        "suite_sha256": _digest(source),
        "implementation_sha256": {
            module: _digest(Path(path).read_bytes())
            for module, path in {
                "assessment": __file__,
                "evaluation": evaluation.__file__,
                "trace_import": trace_import.__file__,
            }.items()
        },
        "config": suite.config.model_dump(mode="json"),
        "scenario_count": len(results),
        "matched_count": matched,
        "conformance_passed": matched == len(results),
        "observed_outcomes": {
            label: sum(result["observed_outcome"] == label for result in results)
            for label in ("pass", "fail", "reject")
        },
        "results": results,
    }


def _cell(value: object) -> str:
    return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ").replace("`", "&#96;")


def render_assessment(report: dict[str, Any]) -> str:
    """Render conformance separately from the pass/fail outcomes of agent traces."""
    status = "PASS" if report["conformance_passed"] else "FAIL"
    lines = [
        "# Sentinel reliability demonstration",
        "",
        f"**Synthetic fixture conformance: {status}** — "
        f"{report['matched_count']}/{report['scenario_count']} expected behaviors matched.",
        "",
        "A matched negative case means a bad trace was rejected or failed evaluation. "
        "This is not an agent success rate, customer result, or safety certification.",
        "",
        f"Suite SHA-256: `{report['suite_sha256']}`",
        "",
        "| Case | Category | Expected | Observed | Matches |",
        "|---|---|---|---|---|",
    ]
    for result in report["results"]:
        lines.append("| " + " | ".join(_cell(result[key]) for key in (
            "case_id", "category", "expected_outcome", "observed_outcome", "matched"
        )) + " |")
    lines.extend(["", "## Evidence and limitations", ""])
    for result in report["results"]:
        lines.extend([f"### {_cell(result['case_id'])}", "", _cell(result["rationale"]), ""])
        for diagnostic in [*result["diagnostics"], *result["mismatches"]]:
            lines.append(f"- {_cell(diagnostic)}")
        lines.append("")
    lines.extend([
        "The JSON report preserves import manifests, evaluation details, input fingerprints, "
        "and implementation fingerprints. Only observable trace contents are evaluated. "
        "An approval event does not establish authentic permission, and an export cannot "
        "prove that unrecorded actions never occurred.",
        "",
    ])
    return "\n".join(lines)
