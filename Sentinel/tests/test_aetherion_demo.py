"""Regression tests for the fictional Aetherion Technologies demonstration."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from sentinel.audit import AuditError, AuditLog
from sentinel.evaluation import (
    AgentRun,
    EvalCase,
    EvaluationConfig,
    evaluate_suite,
    load_jsonl,
)
from sentinel.trace_import import TraceImportConfig, import_otel_path

DEMO = Path(__file__).resolve().parents[1] / "examples" / "aetherion"


def _run(tmp_path: Path) -> Path:
    output = tmp_path / "aetherion-evidence"
    process = subprocess.run(
        [sys.executable, str(DEMO / "run_demo.py"), "--output-dir", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    return output


def test_synthetic_policy_and_audit_workflow_passes(tmp_path: Path) -> None:
    output = _run(tmp_path)
    audits = AuditLog(output / "audit.jsonl")
    records = list(audits.records())
    assert audits.verify() == len(records) == 8
    assert all(record.payload["synthetic"] is True for record in records)
    assert any(
        record.action == "database.write" and not record.allowed for record in records
    )
    assert any(
        record.action == "deploy.promote" and not record.allowed for record in records
    )
    assert any(record.action == "tests.run" and record.allowed for record in records)

    runs = load_jsonl(output / "candidate_runs.jsonl", AgentRun)
    assert len(runs) == 3
    assert all(run.system == "aetherion-synthetic-candidate" for run in runs)
    assert all(run.latency_ms == 0 and run.cost_usd == 0.0 for run in runs)

    report = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
    comparison = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
    assert report["gate_passed"] is True
    assert comparison["promotion_recommended"] is True


def test_prohibited_write_is_a_hard_safety_failure(tmp_path: Path) -> None:
    output = _run(tmp_path)
    cases = load_jsonl(DEMO / "cases.jsonl", EvalCase)
    runs = load_jsonl(output / "candidate_runs.jsonl", AgentRun)
    unsafe = runs[0].model_copy(deep=True)
    denied = next(action for action in unsafe.actions if action.name == "database.write")
    denied.status = "executed"
    report = evaluate_suite(
        cases,
        [unsafe, *runs[1:]],
        EvaluationConfig(),
        system="aetherion-synthetic-candidate",
    )
    assert report.gate_passed is False
    assert any(
        "forbidden action not denied" in failure
        for failure in report.results[0].hard_failures
    )


def test_audit_chain_detects_modified_record(tmp_path: Path) -> None:
    output = _run(tmp_path)
    path = output / "audit.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    first["reason"] = "tampered"
    lines[0] = json.dumps(first)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(AuditError, match="tampering"):
        AuditLog(path).verify()


def test_synthetic_otel_trace_import_passes_safety_checks() -> None:
    imported = import_otel_path(DEMO / "otel_trace.json", TraceImportConfig())
    assert len(imported.runs) == imported.manifest.run_count == 1
    assert imported.manifest.partial_runs == 0
    assert any(
        action.name == "deploy.promote" and action.status == "denied"
        for action in imported.runs[0].actions
    )
    cases = load_jsonl(DEMO / "otel_case.jsonl", EvalCase)
    report = evaluate_suite(
        cases, imported.runs, EvaluationConfig(), system=imported.runs[0].system
    )
    assert report.gate_passed is True
