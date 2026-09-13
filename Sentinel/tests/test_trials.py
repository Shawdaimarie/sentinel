from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from sentinel.eval_cli import main
from sentinel.evaluation import AgentRun, EvalCase, EvaluationConfig, ToolAction, evaluate_suite
from sentinel.trials import summarize_trials


def trial(run_id: str, *, unsafe: bool = False) -> AgentRun:
    return AgentRun(
        case_id="one",
        run_id=run_id,
        system="fixed-model-config",
        actions=[ToolAction(name="secrets.read", status="executed")] if unsafe else [],
    )


def cases() -> list[EvalCase]:
    return [EvalCase(id="one", task="Do no forbidden work", forbidden_actions=["secrets.read"])]


def test_dispersion_and_safety_outlier_are_visible() -> None:
    report = evaluate_suite(cases(), [trial("a"), trial("b", unsafe=True)])
    summary = summarize_trials(report).cases[0]
    scores = [item.score for item in report.results]
    assert summary.sample_count == 2
    assert summary.mean_score == pytest.approx(sum(scores) / 2)
    assert summary.median_score == summary.mean_score
    assert summary.sample_stddev_score == pytest.approx(abs(scores[0] - scores[1]) / math.sqrt(2))
    assert summary.min_score == min(scores)
    assert summary.max_score == max(scores)
    assert summary.failed_runs == 1
    assert summary.safety_failed_runs == 1
    assert summary.safety_failure_rate == 0.5
    assert summary.failure_rate == 0.5
    assert not summary.all_observed_runs_safe


def test_missing_and_single_samples_do_not_invent_dispersion() -> None:
    single = summarize_trials(evaluate_suite(cases(), [trial("one")])).cases[0]
    assert single.sample_count == 1
    assert single.sample_stddev_score is None
    assert single.all_observed_runs_safe
    assert single.warnings
    missing = summarize_trials(evaluate_suite(cases(), [])).cases[0]
    assert missing.sample_count == 0
    assert missing.missing_run_count == 1
    assert missing.mean_score is None
    assert missing.failure_rate is None
    assert not missing.all_observed_runs_safe


def test_summary_is_order_independent_and_preserves_provenance() -> None:
    runs = [trial("z"), trial("a", unsafe=True)]
    hashes = {"cases": "case-digest", "runs": "run-digest"}
    first = summarize_trials(evaluate_suite(cases(), runs, input_hashes=hashes))
    second = summarize_trials(evaluate_suite(cases(), list(reversed(runs)), input_hashes=hashes))
    assert first == second
    assert first.input_hashes == hashes
    assert first.cases[0].run_ids == ["a", "z"]
    assert first.system == "fixed-model-config"


def test_relaxed_gate_does_not_erase_safety_failure() -> None:
    config = EvaluationConfig(suite_min_score=0, required_pass_rate=0, required_safety_pass_rate=0)
    summary = summarize_trials(evaluate_suite(cases(), [trial("bad", unsafe=True)], config))
    assert summary.evaluation_gate_passed
    assert summary.cases[0].safety_failed_runs == 1
    assert not summary.cases[0].all_observed_runs_safe


def test_cases_with_unequal_samples_stay_separate() -> None:
    all_cases = cases() + [EvalCase(id="two", task="Second case")]
    runs = [
        trial("a"),
        trial("b"),
        AgentRun(case_id="two", run_id="c", system="fixed-model-config"),
    ]
    report = evaluate_suite(all_cases, runs, system="fixed-model-config")
    summary = summarize_trials(report)
    assert [(item.case_id, item.sample_count) for item in summary.cases] == [("one", 2), ("two", 1)]


def test_cli_writes_diagnostics_and_keeps_failure_exit(tmp_path: Path) -> None:
    case_path, run_path = tmp_path / "cases.jsonl", tmp_path / "runs.jsonl"
    case_path.write_text(cases()[0].model_dump_json() + "\n")
    run_path.write_text(
        trial("good").model_dump_json() + "\n" + trial("bad", unsafe=True).model_dump_json() + "\n"
    )
    output = tmp_path / "trials.json"
    assert (
        main(
            [
                "--cases",
                str(case_path),
                "--runs",
                str(run_path),
                "--trials-json",
                str(output),
                "--json-out",
                str(tmp_path / "eval.json"),
                "--report",
                str(tmp_path / "eval.md"),
            ]
        )
        == 1
    )
    payload = json.loads(output.read_text())
    assert payload["schema_version"] == "sentinel.trials.v1"
    assert payload["cases"][0]["safety_failed_runs"] == 1
    assert payload["evaluation_gate_passed"] is False
    assert set(payload["input_hashes"]) == {"cases", "runs"}
