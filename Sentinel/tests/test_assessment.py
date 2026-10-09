from __future__ import annotations

import json
from pathlib import Path

import pytest

from sentinel.assessment import assess_suite, render_assessment
from sentinel.assessment_cli import main
from sentinel.evaluation import AgentRun, EvalCase, EvaluationConfig, evaluate_run

SUITE = Path(__file__).resolve().parents[1] / "examples/reliability_assessment/suite.json"


def test_twenty_labeled_traces_preserve_positive_and_negative_evidence() -> None:
    source = SUITE.read_bytes()
    report = assess_suite(source)
    assert report["scenario_count"] == report["matched_count"] == 20
    assert report["conformance_passed"] is True
    assert report["observed_outcomes"] == {"pass": 6, "fail": 13, "reject": 1}
    assert assess_suite(source) == report
    for category in ("completeness", "retries", "authorization", "evaluation"):
        assert sum(result["category"] == category for result in report["results"]) == 5
    assert "not an agent success rate" in render_assessment(report)


@pytest.mark.parametrize("corruption", ["label", "action", "missing", "diagnostic"])
def test_bad_expectations_cannot_report_success(corruption: str, tmp_path: Path) -> None:
    suite = json.loads(SUITE.read_bytes())
    if corruption == "label":
        suite["scenarios"][0].update(expected_outcome="fail", expected_diagnostics=["failure"])
    elif corruption == "action":
        suite["scenarios"][5]["expected_actions"][0]["status"] = "denied"
    elif corruption == "missing":
        suite["scenarios"][1]["expected_missing_fields"] = []
    else:
        suite["scenarios"][1]["expected_diagnostics"] = ["unrelated failure"]
    source = tmp_path / "suite.json"
    source.write_text(json.dumps(suite))
    out = tmp_path / "evidence"
    assert main(["--suite", str(source), "--output-dir", str(out)]) == 1
    report = json.loads((out / "assessment.json").read_text())
    assert report["conformance_passed"] is False
    assert report["matched_count"] == 19
    assert any(result["mismatches"] for result in report["results"])


@pytest.mark.parametrize("changes", [{"completed": False}, {"error": "provider failed"},
                                     {"error": ""}])
def test_incomplete_or_errored_run_cannot_be_rescued_by_high_score(
    changes: dict[str, object],
) -> None:
    case = EvalCase(id="completion", task="Complete the task", expected_output_contains=["done"])
    run = AgentRun.model_validate(dict(case_id=case.id, run_id="1", output="done", **changes))
    result = evaluate_run(case, run, EvaluationConfig())
    assert result.score > 0.90
    assert result.passed is False
    assert result.safety_passed is True  # Completion failure is distinct from unsafe behavior.
    assert result.hard_failures


def test_invalid_suite_and_existing_results_are_preserved(tmp_path: Path) -> None:
    source = tmp_path / "bad.json"
    source.write_text('{"synthetic": false}')
    out = tmp_path / "evidence"
    assert main(["--suite", str(source), "--output-dir", str(out)]) == 2
    assert not out.exists()
    assert main(["--suite", str(SUITE), "--output-dir", str(out)]) == 0
    original = (out / "assessment.json").read_bytes()
    assert main(["--suite", str(SUITE), "--output-dir", str(out)]) == 2
    assert (out / "assessment.json").read_bytes() == original


def test_duplicate_case_and_wrong_trace_identity_are_rejected() -> None:
    suite = json.loads(SUITE.read_bytes())
    suite["scenarios"].append(suite["scenarios"][0])
    with pytest.raises(ValueError, match="unique"):
        assess_suite(json.dumps(suite).encode())
    suite["scenarios"].pop()
    suite["scenarios"][0]["trace"]["spans"][0]["attributes"]["sentinel.case.id"] = "other"
    with pytest.raises(ValueError, match="exactly its own case"):
        assess_suite(json.dumps(suite).encode())


def test_report_escapes_trace_derived_markdown() -> None:
    report = assess_suite(SUITE.read_bytes())
    report["results"][0]["rationale"] = '<script>alert(1)</script>|`x`\nnext'
    rendered = render_assessment(report)
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered
    assert '&#124;&#96;x&#96; next' in rendered
