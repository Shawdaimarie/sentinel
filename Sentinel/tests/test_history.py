"""Storage-boundary validation independent of a running PostgreSQL server."""

import json

import psycopg
import pytest

from sentinel import history_cli
from sentinel.evaluation import AgentRun, EvalCase, EvaluationConfig, evaluate_suite
from sentinel.history import HistoryError, identifier, minimized_report, query_history
from tests.history_fixtures import history_report


def test_diagnostics_are_omitted_and_fingerprint_is_format_independent() -> None:
    report = history_report(unsafe=True)
    report.results[0].metrics[0].detail = "Authorization: Bearer secret-marker"
    report.gate_failures = ["private customer identifier"]
    raw = report.model_dump_json().encode()
    minimized, digest = minimized_report(raw)
    assert "secret-marker" not in minimized.model_dump_json()
    assert "private customer" not in minimized.model_dump_json()
    assert minimized.results[0].safety_passed is False
    assert len(minimized.results[0].hard_failures) == 1
    assert minimized_report(json.dumps(json.loads(raw), indent=4).encode())[1] == digest


@pytest.mark.parametrize(
    "change",
    [
        {"schema_version": "future"},
        {"run_count": 2},
        {"gate_passed": False},
        {"input_hashes": {}},
        {"overall_score": 0.4},
        {"slices": []},
        {"generated_at": "2026-09-11T12:00:00"},
        {"total_cost_usd": float("inf")},
    ],
)
def test_invalid_reports_fail_closed(change: dict[str, object]) -> None:
    payload = history_report().model_dump(mode="json")
    payload.update(change)
    with pytest.raises(HistoryError):
        minimized_report(json.dumps(payload).encode())


def test_duplicate_runs_and_duplicate_json_keys_are_rejected() -> None:
    report = history_report()
    report.results.append(report.results[0])
    report.run_count = 2
    with pytest.raises(HistoryError, match="duplicate run"):
        minimized_report(report.model_dump_json().encode())
    with pytest.raises(HistoryError):
        minimized_report(b'{"system":"first","system":"second"}')


def test_numeric_strings_cannot_smuggle_nonfinite_values() -> None:
    payload = history_report().model_dump(mode="json")
    payload["total_cost_usd"] = "Infinity"
    payload["results"][0]["cost_usd"] = "Infinity"
    with pytest.raises(HistoryError, match="non-finite"):
        minimized_report(json.dumps(payload).encode())


def test_valid_gate_near_rounding_boundary_is_preserved() -> None:
    case = EvalCase(id="latency", task="Bound latency", max_latency_ms=100)
    run = AgentRun(case_id="latency", run_id="one", latency_ms=150)
    report = evaluate_suite(
        [case],
        [run],
        EvaluationConfig(run_min_score=0.9833333),
        input_hashes={"cases": "a" * 64, "runs": "b" * 64},
    )
    assert report.results[0].score < report.config.run_min_score
    assert report.results[0].passed
    assert minimized_report(report.model_dump_json().encode())[0].gate_passed


@pytest.mark.parametrize("value", ["", "a@company.example", "x' OR true--", "x" * 129])
def test_operational_identifiers_reject_free_text(value: str) -> None:
    with pytest.raises(HistoryError):
        identifier(value)


def test_pagination_is_validated_before_connecting() -> None:
    with pytest.raises(HistoryError, match="limit"):
        query_history("unused", suite="demo", limit=101)
    with pytest.raises(HistoryError, match="limit"):
        query_history("unused", suite="demo", offset=-1)


def test_cli_does_not_disclose_driver_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "postgresql://private-user:private-password@private-host/db"
    monkeypatch.setenv("SENTINEL_HISTORY_READER_DSN", secret)

    def fail(*args: object, **kwargs: object) -> None:
        raise psycopg.OperationalError(secret)

    monkeypatch.setattr(history_cli, "query_history", fail)
    assert history_cli.main(["query", "--suite", "demo"]) == 2
    output = capsys.readouterr()
    assert "private-" not in output.err + output.out
    assert "database operation failed" in output.err


def test_query_never_falls_back_to_owner_credentials(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("SENTINEL_HISTORY_READER_DSN", raising=False)
    monkeypatch.setenv("SENTINEL_HISTORY_OWNER_DSN", "must-not-be-used")
    assert history_cli.main(["query", "--suite", "demo"]) == 2
    assert "SENTINEL_HISTORY_READER_DSN" in capsys.readouterr().err
