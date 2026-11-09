from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from sentinel.reliability import (
    MAX_INPUT_BYTES,
    ReliabilityManifest,
    ReliabilityReport,
    assess_reliability,
    bounded_mean_interval,
    render_reliability,
)
from sentinel.reliability_cli import main


def encoded(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def artifacts(
    count: int = 2,
    repeats: int = 2,
    *,
    baseline: bool = False,
    **overrides: object,
) -> tuple[bytes, bytes, bytes, bytes | None]:
    """Generated data tests arithmetic only, even when exercising the operational flag."""
    ids = [f"case-{i}" for i in range(count)]
    trials = [f"trial-{i}" for i in range(repeats)]
    cases = b"\n".join(
        encoded(
            {
                "id": case,
                "task": "Return ok",
                "expected_output_contains": ["ok"],
                "forbidden_actions": ["secrets.read"],
            }
        )
        for case in ids
    )
    runs = b"\n".join(
        encoded(
            {
                "case_id": case,
                "run_id": trial,
                "system": "candidate",
                "output": "ok",
            }
        )
        for case in ids
        for trial in trials
    )
    previous = runs.replace(b'"candidate"', b'"baseline"') if baseline else None
    manifest: dict[str, object] = {
        "schema_version": "sentinel.reliability-manifest.v1",
        "assessment_id": "unit-test",
        "case_ids": ids,
        "trial_ids": trials,
        "candidate_system": "candidate",
        "cases_sha256": hashlib.sha256(cases).hexdigest(),
        "candidate_sha256": hashlib.sha256(runs).hexdigest(),
        "evidence_kind": "operational",
        "independent_case_sampling": True,
        "sampling_description": "Unit test of declarations; not operational evidence.",
        "source_commit": "0" * 40,
        "model_version": "fixture",
        "prompt_version": "fixture",
        "tool_version": "fixture",
        "runtime_version": "fixture",
        "minimum_cases": 2,
    }
    if previous is not None:
        manifest.update(
            baseline_system="baseline", baseline_sha256=hashlib.sha256(previous).hexdigest()
        )
    manifest.update(overrides)
    return encoded(manifest), cases, runs, previous


def replace_runs(
    data: tuple[bytes, bytes, bytes, bytes | None],
    runs: bytes,
    *,
    baseline: bool = False,
) -> tuple[bytes, bytes, bytes, bytes | None]:
    manifest = json.loads(data[0])
    manifest["baseline_sha256" if baseline else "candidate_sha256"] = hashlib.sha256(
        runs
    ).hexdigest()
    return encoded(manifest), data[1], data[2] if baseline else runs, runs if baseline else data[3]


def test_known_answer_bounds_and_support() -> None:
    interval = bounded_mean_interval([1.0] * 200, 0.95)
    assert interval.lower == pytest.approx(0.9039677208680079)
    assert interval.upper == 1.0
    zero = bounded_mean_interval([0.0] * 200, 0.95)
    assert zero.lower == 0.0
    assert zero.upper == pytest.approx(1 - interval.lower)
    delta = bounded_mean_interval([0.0] * 200, 0.95, lower=-1, upper=1)
    assert delta.upper == pytest.approx(2 * zero.upper)
    assert delta.lower == -delta.upper


@pytest.mark.parametrize(
    "values,confidence",
    [
        ([], 0.95),
        ([float("nan")], 0.95),
        ([float("inf")], 0.95),
        ([1.1], 0.95),
        ([0.5], 1.0),
        ([0.5], float("nan")),
    ],
)
def test_invalid_statistical_inputs(values: list[float], confidence: float) -> None:
    with pytest.raises(ValueError):
        bounded_mean_interval(values, confidence)


def test_more_repeats_do_not_inflate_independent_sample_size() -> None:
    small = assess_reliability(*artifacts(count=20, repeats=2))
    large = assess_reliability(*artifacts(count=20, repeats=50))
    assert small.pass_rate_interval == large.pass_rate_interval
    assert large.status == "inconclusive"
    assert not large.promotion_recommended


def test_declared_target_requires_lower_bound() -> None:
    report = assess_reliability(*artifacts(count=200))
    assert report.status == "pass"
    assert report.promotion_recommended
    assert report.pass_rate_interval is not None
    assert report.pass_rate_interval.lower > 0.9


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"evidence_kind": "synthetic"}, "synthetic"),
        ({"independent_case_sampling": False}, "sampling"),
        ({"minimum_cases": 201}, "insufficient cases"),
    ],
)
def test_evidence_gaps_cannot_pass(overrides: dict[str, object], reason: str) -> None:
    report = assess_reliability(*artifacts(count=200, **overrides))
    assert report.status == "inconclusive"
    assert report.pass_rate_interval is None
    assert any(reason in r for r in report.reasons)


def test_missing_trial_and_missing_whole_case_are_visible() -> None:
    data = artifacts()
    report = assess_reliability(*replace_runs(data, data[2].splitlines()[0]))
    assert report.status == "inconclusive"
    assert report.cases[0].missing_trial_ids == ["trial-1"]
    assert report.cases[1].observed_pass_rate is None
    assert report.cases[1].missing_trial_ids == ["trial-0", "trial-1"]
    assert report.pass_rate_interval is None
    assert "trial-1" in render_reliability(report)


def test_empty_observations_are_inconclusive() -> None:
    report = assess_reliability(*replace_runs(artifacts(), b""))
    assert report.status == "inconclusive"
    assert all(item.observed_trials == 0 for item in report.cases)


def test_hard_failure_overrides_small_sample_and_relaxed_weights() -> None:
    data = artifacts(
        evaluation_config={
            "suite_min_score": 0.0,
            "required_pass_rate": 0.0,
            "required_safety_pass_rate": 0.0,
        }
    )
    run = json.loads(data[2].splitlines()[0])
    run["actions"] = [{"name": "secrets.read", "status": "executed"}]
    report = assess_reliability(*replace_runs(data, encoded(run)))
    assert report.status == "fail"
    assert not report.promotion_recommended
    assert any("forbidden action" in reason for reason in report.reasons)
    assert any("incomplete" in reason for reason in report.reasons)


def test_deterministic_gate_is_preserved() -> None:
    data = artifacts(count=200)
    report = assess_reliability(*replace_runs(data, data[2].replace(b'"ok"', b'"wrong"')))
    assert report.status == "fail"
    assert not report.candidate.gate_passed


def test_paired_comparison_and_joint_confidence() -> None:
    report = assess_reliability(*artifacts(count=300, baseline=True))
    assert report.status == "pass"
    assert report.comparison is not None
    assert report.comparison.mean_delta == 0.0
    assert report.paired_pass_rate_delta is not None
    assert report.paired_pass_rate_delta.mean == 0.0
    assert report.paired_pass_rate_delta.confidence_level == pytest.approx(0.975)
    assert report.pass_rate_interval is not None
    assert report.pass_rate_interval.confidence_level == pytest.approx(0.975)


def test_baseline_missing_pairs_never_compares_only_successful_subset() -> None:
    data = artifacts(baseline=True)
    assert data[3] is not None
    report = assess_reliability(*replace_runs(data, data[3].splitlines()[0], baseline=True))
    assert report.status == "inconclusive"
    assert report.comparison is None
    assert report.paired_pass_rate_delta is None


def test_paired_regression_blocks_promotion_even_with_relaxed_suite() -> None:
    data = artifacts(
        baseline=True,
        evaluation_config={
            "suite_min_score": 0.0,
            "required_pass_rate": 0.0,
            "required_safety_pass_rate": 0.0,
        },
    )
    report = assess_reliability(*replace_runs(data, data[2].replace(b'"ok"', b'"wrong"')))
    assert report.status == "fail"
    assert any("paired regression" in reason for reason in report.reasons)


@pytest.mark.parametrize("mutation", ["duplicate", "system", "trial", "case", "nan", "coercion"])
def test_invalid_run_contracts(mutation: str) -> None:
    data = artifacts()
    run = json.loads(data[2].splitlines()[0])
    if mutation == "system":
        run["system"] = "other"
    elif mutation == "trial":
        run["run_id"] = "unplanned"
    elif mutation == "case":
        run["case_id"] = "unplanned"
    elif mutation == "coercion":
        run["completed"] = "false"
    elif mutation == "nan":
        run["cost_usd"] = float("nan")
    runs = json.dumps(run).encode()
    if mutation == "duplicate":
        runs += b"\n" + runs
    with pytest.raises(ValueError):
        assess_reliability(*replace_runs(data, runs))


def test_duplicate_json_keys_and_artifact_tampering_are_rejected() -> None:
    data = artifacts()
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        assess_reliability(data[0], data[1], data[2] + b" ")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        assess_reliability(b'{"assessment_id":"a","assessment_id":"b"}', data[1], data[2])


@pytest.mark.parametrize(
    "change",
    [
        {"trial_ids": ["same", "same"]},
        {"confidence_level": 1.0},
        {"independent_case_sampling": "true"},
        {"sampling_description": " "},
        {"unexpected": True},
        {"baseline_system": "baseline"},
    ],
)
def test_manifest_rejects_ambiguous_or_coerced_values(change: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        assess_reliability(*artifacts(**change))


def test_oversized_input_is_rejected() -> None:
    data = artifacts()
    with pytest.raises(ValueError, match="10 MiB"):
        assess_reliability(b" " * (MAX_INPUT_BYTES + 1), data[1], data[2])


def test_json_exponent_overflow_is_rejected_before_model_validation() -> None:
    data = artifacts()
    manifest = data[0].replace(b'"minimum_cases": 2', b'"minimum_cases": 1e999')
    with pytest.raises(ValueError, match="non-finite JSON number"):
        assess_reliability(manifest, data[1], data[2])


def test_replay_is_identical_and_report_validates() -> None:
    data = artifacts(baseline=True)
    first = assess_reliability(*data)
    second = assess_reliability(*data)
    assert first.model_dump_json() == second.model_dump_json()
    assert ReliabilityReport.model_validate_json(first.model_dump_json()) == first


def test_cli_artifacts_exit_codes_and_no_overwrite(tmp_path: Path) -> None:
    data = artifacts(evidence_kind="synthetic")
    for name, content in zip(("manifest.json", "cases.jsonl", "runs.jsonl"), data[:3], strict=True):
        (tmp_path / name).write_bytes(content)
    args = [
        "--manifest",
        str(tmp_path / "manifest.json"),
        "--cases",
        str(tmp_path / "cases.jsonl"),
        "--runs",
        str(tmp_path / "runs.jsonl"),
        "--output-dir",
        str(tmp_path / "output"),
    ]
    assert main(args) == 3
    output = tmp_path / "output" / "reliability.json"
    original = output.read_bytes()
    assert json.loads(original)["status"] == "inconclusive"
    assert main(args) == 2
    assert output.read_bytes() == original
    (tmp_path / "runs.jsonl").write_bytes(b"tampered")
    args[-1] = str(tmp_path / "invalid")
    assert main(args) == 2
    assert not (tmp_path / "invalid").exists()


def test_committed_schemas_match_runtime_models() -> None:
    root = Path(__file__).resolve().parents[1] / "schemas"
    for filename, model in (
        ("reliability-manifest-v1.schema.json", ReliabilityManifest),
        ("reliability-assessment-v1.schema.json", ReliabilityReport),
    ):
        assert json.loads((root / filename).read_text()) == model.model_json_schema()


def test_documented_example_replays_expected_report() -> None:
    root = Path(__file__).resolve().parents[1] / "examples/reliability_assessment/repeated_trials"
    report = assess_reliability(
        (root / "manifest.json").read_bytes(),
        (root / "cases.jsonl").read_bytes(),
        (root / "runs.jsonl").read_bytes(),
    )
    assert report.status == "inconclusive"
    assert render_reliability(report) == (root / "expected-report.md").read_text()


@pytest.mark.parametrize("failure,expected", [(False, 0), (True, 1)])
def test_cli_pass_and_failure_codes(tmp_path: Path, failure: bool, expected: int) -> None:
    data = artifacts(count=200)
    if failure:
        data = replace_runs(data, data[2].replace(b'"ok"', b'"wrong"'))
    paths = [tmp_path / name for name in ("manifest", "cases", "runs")]
    for path, content in zip(paths, data[:3], strict=True):
        path.write_bytes(content)
    assert (
        main(
            [
                "--manifest",
                str(paths[0]),
                "--cases",
                str(paths[1]),
                "--runs",
                str(paths[2]),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == expected
    )
