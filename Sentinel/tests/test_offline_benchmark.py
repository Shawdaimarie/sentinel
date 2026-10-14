"""Prevent incomplete or incorrect measurements being reported as capacity passes."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "offline_benchmark", ROOT / "scripts/benchmark-offline-eval.py"
)
assert SPEC and SPEC.loader
BENCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BENCH)
CRITERIA = json.loads((ROOT / "Sentinel/benchmarks/offline-evaluation-v1.json").read_text())


def passing_report():
    return {
        "input_hashes": {"cases": "case-hash", "runs": "run-hash"},
        "run_count": 2,
        "gate_passed": True,
        "safety_pass_rate": 1.0,
        "results": [{"passed": True, "safety_passed": True}] * 2,
    }


@pytest.mark.parametrize(
    "change",
    [
        {"input_hashes": {"cases": "wrong", "runs": "run-hash"}},
        {"run_count": 1},
        {"results": []},
        {"gate_passed": False},
        {"results": [{"passed": False, "safety_passed": True}] * 2},
        {"safety_pass_rate": 0.5},
    ],
)
def test_successful_exit_is_not_enough(change):
    report = passing_report()
    hashes = report["input_hashes"]
    assert BENCH.valid_report(report, hashes, 2)
    report.update(change)
    assert not BENCH.valid_report(report, hashes, 2)


def rows(count=10):
    return [
        {"ok": True, "seconds": 1.0, "peak_rss_mib": 30.0, "cpu_seconds": 0.2} for _ in range(count)
    ]


def summary(values, duration=30):
    return BENCH.summarize(
        values, duration, 1, CRITERIA["acceptance"]["expected"], CRITERIA["acceptance"], 10
    )


def test_failures_remain_in_error_and_latency_denominators():
    values = rows()
    values[-1].update(ok=False, seconds=10.0)
    result = summary(values)
    assert result["status"] == "FAIL"
    assert result["attempts"] == 10
    assert result["validated_batches"] == 9
    assert result["error_rate"] == 0.1
    assert result["p95_seconds"] == 10.0
    assert result["batches_per_second"] == 0.3


def test_insufficient_samples_cannot_pass():
    assert summary(rows(9), duration=1)["status"] == "FAIL"
    assert summary(rows())["status"] == "PASS"


@pytest.mark.parametrize(
    "field,value", [("peak_rss_mib", 513.0), ("seconds", 6.0), ("cpu_seconds", float("nan"))]
)
def test_excess_or_missing_metrics_cannot_pass(field, value):
    values = rows()
    values[-1][field] = value
    assert summary(values)["status"] == "FAIL"


def test_nearest_rank_percentiles_and_empty_rejection():
    assert BENCH.percentile(list(range(1, 101)), 0.95) == 95
    assert BENCH.percentile(list(range(1, 101)), 0.99) == 99
    with pytest.raises(ValueError):
        BENCH.percentile([], 0.95)
