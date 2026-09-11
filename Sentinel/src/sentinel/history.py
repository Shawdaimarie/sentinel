"""PostgreSQL evaluation history with immutable, minimized report snapshots.

The store records reported decisions; it does not attest to source authenticity.
Raw diagnostic text is deliberately excluded from persisted reports.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from importlib.resources import files
from typing import Any, Literal

import psycopg
from psycopg import IsolationLevel
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from sentinel.evaluation import ComparisonReport, RunEvaluation, SuiteReport, compare_reports

MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_RUNS = 10_000
MAX_PAGE_SIZE = 100
MIGRATIONS = ("001_history.sql", "002_history_indexes.sql")
HistoryView = Literal["suites", "runs", "slices", "comparisons"]
Connection = psycopg.Connection[dict[str, Any]]


class HistoryError(ValueError):
    """A report, migration or history operation violates the storage contract."""


def identifier(value: str) -> str:
    """Accept bounded operational identifiers, never arbitrary diagnostic text."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", value):
        raise HistoryError("invalid history identifier; use a non-sensitive slug")
    return value


def fingerprint(value: str) -> str:
    """Validate a SHA-256 reference without including its value in errors."""
    if not re.fullmatch(r"[a-f0-9]{64}", value):
        raise HistoryError("expected a lowercase SHA-256 fingerprint")
    return value


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    except (ValueError, TypeError) as exc:
        raise HistoryError("report contains non-finite or unsupported values") from exc


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HistoryError("duplicate JSON key")
        result[key] = value
    return result


def _load(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_REPORT_BYTES:
        raise HistoryError("report exceeds the 8 MiB import limit")
    try:
        payload = json.loads(raw, object_pairs_hook=_object_pairs)
        if not isinstance(payload, dict):
            raise HistoryError("report must be a JSON object")
        _canonical(payload)
        return payload
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise HistoryError("invalid report JSON") from exc


def minimized_report(raw: bytes) -> tuple[SuiteReport, str]:
    """Validate report consistency and remove all free-text diagnostic fields."""
    payload = _load(raw)
    try:
        report = SuiteReport.model_validate(payload)
    except ValueError as exc:
        raise HistoryError("invalid SuiteReport schema") from exc
    # Pydantic can coerce a numeric string to infinity after JSON validation.
    _canonical(report.model_dump())
    if report.schema_version != "sentinel.eval.v1":
        raise HistoryError("unsupported evaluation schema version")
    identifier(report.system)
    try:
        timestamp = datetime.fromisoformat(report.generated_at)
    except ValueError as exc:
        raise HistoryError("invalid report timestamp") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise HistoryError("report timestamp must include a timezone")
    report.generated_at = timestamp.isoformat()
    if not {"cases", "runs"} <= report.input_hashes.keys():
        raise HistoryError("case and run source fingerprints are required")
    for name, digest in report.input_hashes.items():
        identifier(name)
        fingerprint(digest)
    if not report.results or len(report.results) > MAX_RUNS:
        raise HistoryError("report must contain between 1 and 10000 runs")
    if report.run_count != len(report.results):
        raise HistoryError("run count does not match report results")
    seen: set[tuple[str, str]] = set()
    grouped: dict[str, list[RunEvaluation]] = defaultdict(list)
    for run in report.results:
        identifier(run.case_id)
        identifier(run.run_id)
        key = (run.case_id, run.run_id)
        if key in seen or run.system != report.system:
            raise HistoryError("duplicate run or inconsistent system")
        seen.add(key)
        names = [metric.name for metric in run.metrics]
        if len(set(names)) != len(names) or set(names) != report.config.weights.keys():
            raise HistoryError("run metrics must match evaluator dimensions")
        for metric in run.metrics:
            if metric.weight != report.config.weights[metric.name]:
                raise HistoryError("metric weights do not match report configuration")
            metric.detail = "[omitted by history policy]"
        unrounded_score = sum(m.value * m.weight for m in run.metrics)
        expected_score = round(unrounded_score, 6)
        if not math.isclose(run.score, expected_score, abs_tol=1e-6):
            raise HistoryError("run score does not match its metrics")
        if run.safety_passed != (not run.hard_failures):
            raise HistoryError("inconsistent safety result")
        if run.passed and (not run.safety_passed or unrounded_score < report.config.run_min_score):
            raise HistoryError("invalid passing run")
        if len(set(run.tags)) != len(run.tags):
            raise HistoryError("duplicate run tags")
        for tag in run.tags:
            identifier(tag)
            grouped[tag].append(run)
        run.hard_failures = ["[omitted by history policy]"] * len(run.hard_failures)
    expected = {
        "overall_score": round(statistics.fmean(r.score for r in report.results), 6),
        "pass_rate": round(sum(r.passed for r in report.results) / report.run_count, 6),
        "safety_pass_rate": round(
            sum(r.safety_passed for r in report.results) / report.run_count, 6
        ),
        "mean_latency_ms": round(statistics.fmean(r.latency_ms for r in report.results), 3),
        "total_cost_usd": round(sum(r.cost_usd for r in report.results), 6),
    }
    for name, value in expected.items():
        if not math.isclose(getattr(report, name), value, abs_tol=1e-6):
            raise HistoryError("suite summary does not match run results")
    # Gate thresholds are evaluated on unrounded values, as in evaluate_suite.
    gate_ok = (
        statistics.fmean(r.score for r in report.results) >= report.config.suite_min_score
        and sum(r.passed for r in report.results) / report.run_count
        >= report.config.required_pass_rate
        and sum(r.safety_passed for r in report.results) / report.run_count
        >= report.config.required_safety_pass_rate
    )
    if report.gate_passed != gate_ok or report.gate_passed != (not report.gate_failures):
        raise HistoryError("inconsistent suite gate")
    # Rebuild slices from validated runs instead of trusting supplied aggregates.
    expected_slices = [
        {
            "tag": tag,
            "runs": len(runs),
            "mean_score": round(statistics.fmean(r.score for r in runs), 6),
            "pass_rate": round(sum(r.passed for r in runs) / len(runs), 6),
            "safety_pass_rate": round(sum(r.safety_passed for r in runs) / len(runs), 6),
        }
        for tag, runs in sorted(grouped.items())
    ]
    if [s.model_dump() for s in report.slices] != expected_slices:
        raise HistoryError("slice summaries do not match run results")
    report.gate_failures = ["[omitted by history policy]"] * len(report.gate_failures)
    return report, _digest(payload)


@contextmanager
def _connection(dsn: str, *, readonly: bool = True) -> Iterator[Connection]:
    """Bound each operation to one short transaction, read-only unless requested."""
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
        conn.isolation_level = (
            IsolationLevel.REPEATABLE_READ if readonly else IsolationLevel.READ_COMMITTED
        )
        conn.read_only = readonly
        conn.execute("SET LOCAL statement_timeout = '30s'")
        conn.execute("SET LOCAL lock_timeout = '5s'")
        yield conn


def migrate(dsn: str, *, target: int = len(MIGRATIONS)) -> int:
    """Apply forward-only, checksum-verified migrations atomically as the owner."""
    if target < 1 or target > len(MIGRATIONS):
        raise HistoryError("unsupported migration target")
    with _connection(dsn, readonly=False) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(734928116)")
        conn.execute("CREATE SCHEMA IF NOT EXISTS sentinel_history")
        conn.execute("REVOKE ALL ON SCHEMA sentinel_history FROM PUBLIC")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sentinel_history.schema_migrations "
            "(version integer PRIMARY KEY, sha256 text NOT NULL, "
            "applied_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        applied = {
            row["version"]: row["sha256"]
            for row in conn.execute(
                "SELECT version, sha256 FROM sentinel_history.schema_migrations"
            )
        }
        if sorted(applied) != list(range(1, len(applied) + 1)) or len(applied) > target:
            raise HistoryError("migration history is unsupported; downgrades are not automatic")
        for version, name in enumerate(MIGRATIONS[:target], 1):
            source = files("sentinel").joinpath("migrations", name).read_text(encoding="utf-8")
            digest = hashlib.sha256(source.encode()).hexdigest()
            if version in applied:
                if applied[version] != digest:
                    raise HistoryError("applied migration checksum changed")
                continue
            conn.execute(source)
            conn.execute(
                "INSERT INTO sentinel_history.schema_migrations (version, sha256) VALUES (%s, %s)",
                (version, digest),
            )
    return target


def import_suite(dsn: str, raw: bytes, *, suite: str, release: str) -> dict[str, Any]:
    """Atomically import a report; conflicting reuse of a release is rejected."""
    identifier(suite)
    identifier(release)
    report, canonical_sha = minimized_report(raw)
    report_id = _digest([suite, release, canonical_sha])
    source_sha = hashlib.sha256(raw).hexdigest()
    with _connection(dsn, readonly=False) as conn:
        row = conn.execute(
            "INSERT INTO sentinel_history.suites "
            "(id, suite, release, system, generated_at, source_sha256, report) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
            (
                report_id,
                suite,
                release,
                report.system,
                report.generated_at,
                source_sha,
                Jsonb(report.model_dump(mode="json")),
            ),
        ).fetchone()
        if row is None:
            existing = conn.execute(
                "SELECT id FROM sentinel_history.suites "
                "WHERE suite=%s AND release=%s AND system=%s",
                (suite, release, report.system),
            ).fetchone()
            if existing is None or existing["id"] != report_id:
                raise HistoryError("release already has a different report; use a new release ID")
            return {"id": report_id, "inserted": False}
        with conn.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO sentinel_history.sources VALUES (%s, %s, %s)",
                [(report_id, name, digest) for name, digest in report.input_hashes.items()],
            )
            cursor.executemany(
                "INSERT INTO sentinel_history.cases VALUES (%s, %s)",
                [(report_id, case_id) for case_id in sorted({r.case_id for r in report.results})],
            )
            cursor.executemany(
                "INSERT INTO sentinel_history.runs VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    (
                        report_id,
                        r.case_id,
                        r.run_id,
                        r.score,
                        r.passed,
                        r.safety_passed,
                        r.latency_ms,
                        r.cost_usd,
                        r.executed_actions,
                        len(r.hard_failures),
                    )
                    for r in report.results
                ],
            )
            cursor.executemany(
                "INSERT INTO sentinel_history.metrics VALUES (%s, %s, %s, %s, %s, %s, %s)",
                [
                    (report_id, r.case_id, r.run_id, m.name, m.value, m.weight, m.passed)
                    for r in report.results
                    for m in r.metrics
                ],
            )
            cursor.executemany(
                "INSERT INTO sentinel_history.tags VALUES (%s, %s, %s, %s)",
                [(report_id, r.case_id, r.run_id, tag) for r in report.results for tag in r.tags],
            )
    return {"id": report_id, "inserted": True}


def _get(conn: Connection, report_id: str) -> dict[str, Any]:
    fingerprint(report_id)
    row = conn.execute(
        "SELECT id, suite, release, source_sha256, report FROM sentinel_history.suites WHERE id=%s",
        (report_id,),
    ).fetchone()
    if row is None:
        raise HistoryError("report not found")
    return row


def get_report(dsn: str, report_id: str) -> dict[str, Any]:
    """Fetch the minimized snapshot and original artifact fingerprint read-only."""
    with _connection(dsn) as conn:
        return _get(conn, report_id)


def _compare(
    conn: Connection,
    baseline_id: str,
    candidate_id: str,
    max_regression: float,
) -> dict[str, Any]:
    if not math.isfinite(max_regression) or max_regression < 0:
        raise HistoryError("regression tolerance must be finite and non-negative")
    if baseline_id == candidate_id:
        raise HistoryError("select two different reports")
    before = _get(conn, baseline_id)
    after = _get(conn, candidate_id)
    baseline = SuiteReport.model_validate(before["report"])
    candidate = SuiteReport.model_validate(after["report"])
    if (
        before["suite"] != after["suite"]
        or baseline.input_hashes["cases"] != candidate.input_hashes["cases"]
        or baseline.config != candidate.config
        or {(r.case_id, r.run_id) for r in baseline.results}
        != {(r.case_id, r.run_id) for r in candidate.results}
    ):
        raise HistoryError(
            "comparison requires the same suite, case fingerprint, config and run keys"
        )
    comparison = compare_reports(baseline, candidate, max_score_regression=max_regression)
    return {
        "baseline_id": baseline_id,
        "candidate_id": candidate_id,
        "comparison": comparison.model_dump(mode="json"),
        "cost_delta_usd": round(candidate.total_cost_usd - baseline.total_cost_usd, 6),
        "mean_latency_delta_ms": round(candidate.mean_latency_ms - baseline.mean_latency_ms, 3),
    }


def compare_history(
    dsn: str,
    baseline_id: str,
    candidate_id: str,
    *,
    max_regression: float = 0.02,
) -> dict[str, Any]:
    """Reproduce paired release decisions from compatible stored reports without writes."""
    with _connection(dsn) as conn:
        return _compare(conn, baseline_id, candidate_id, max_regression)


def import_comparison(
    dsn: str,
    raw: bytes,
    *,
    baseline_id: str,
    candidate_id: str,
) -> dict[str, Any]:
    """Persist a comparison only if it matches a replay against stored suite reports."""
    try:
        comparison = ComparisonReport.model_validate(_load(raw))
    except ValueError as exc:
        raise HistoryError("invalid ComparisonReport schema") from exc
    with _connection(dsn, readonly=False) as conn:
        replay = _compare(conn, baseline_id, candidate_id, comparison.max_allowed_regression)
        if comparison.model_dump(mode="json") != replay["comparison"]:
            raise HistoryError("comparison does not match stored reports")
        comparison_id = _digest([baseline_id, candidate_id, replay["comparison"]])
        row = conn.execute(
            "INSERT INTO sentinel_history.comparisons "
            "(id, baseline_id, candidate_id, source_sha256, report) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
            (
                comparison_id,
                baseline_id,
                candidate_id,
                hashlib.sha256(raw).hexdigest(),
                Jsonb(replay["comparison"]),
            ),
        ).fetchone()
        if row is not None:
            with conn.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO sentinel_history.regressions VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    [
                        (
                            comparison_id,
                            r.case_id,
                            r.run_id,
                            r.baseline_score,
                            r.candidate_score,
                            r.delta,
                            r.reason,
                        )
                        for r in comparison.regressions
                    ],
                )
    return {"id": comparison_id, "inserted": row is not None}


def query_history(
    dsn: str,
    *,
    suite: str,
    view: HistoryView = "suites",
    case_id: str | None = None,
    tag: str | None = None,
    safety_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Return one deterministic, bounded page from fixed read-only query templates."""
    identifier(suite)
    if case_id is not None:
        identifier(case_id)
    if tag is not None:
        identifier(tag)
    if not 1 <= limit <= MAX_PAGE_SIZE or not 0 <= offset <= 100_000:
        raise HistoryError("limit must be 1..100 and offset 0..100000")
    if view != "runs" and (case_id is not None or safety_only):
        raise HistoryError("case and safety filters require the runs view")
    if view not in {"runs", "slices"} and tag is not None:
        raise HistoryError("tag filters require the runs or slices view")
    params: tuple[object, ...]
    if view == "suites":
        query = (
            "SELECT id, sequence, release, system, generated_at, imported_at, "
            "report->'overall_score' AS overall_score, report->'gate_passed' AS gate_passed, "
            "report->'pass_rate' AS pass_rate, report->'safety_pass_rate' AS safety_pass_rate, "
            "report->'total_cost_usd' AS total_cost_usd, "
            "report->'mean_latency_ms' AS mean_latency_ms "
            "FROM sentinel_history.suites WHERE suite=%s ORDER BY sequence LIMIT %s OFFSET %s"
        )
        params = (suite, limit + 1, offset)
    elif view == "runs":
        query = (
            "SELECT s.release, s.system, r.* FROM sentinel_history.runs r "
            "JOIN sentinel_history.suites s ON s.id=r.suite_id "
            "WHERE s.suite=%s AND (%s::text IS NULL OR r.case_id=%s) "
            "AND (NOT %s OR NOT r.safety_passed) "
            "AND (%s::text IS NULL OR EXISTS (SELECT 1 FROM sentinel_history.tags t "
            "WHERE t.suite_id=r.suite_id AND t.case_id=r.case_id "
            "AND t.run_id=r.run_id AND t.tag=%s)) "
            "ORDER BY s.sequence, r.case_id, r.run_id LIMIT %s OFFSET %s"
        )
        params = (suite, case_id, case_id, safety_only, tag, tag, limit + 1, offset)
    elif view == "slices":
        query = (
            "SELECT s.id, s.release, s.system, t.tag, count(*) AS runs, "
            "avg(r.score) AS mean_score, avg(r.passed::int) AS pass_rate, "
            "avg(r.safety_passed::int) AS safety_pass_rate, sum(r.cost_usd) AS total_cost_usd, "
            "avg(r.latency_ms) AS mean_latency_ms FROM sentinel_history.tags t "
            "JOIN sentinel_history.runs r USING (suite_id, case_id, run_id) "
            "JOIN sentinel_history.suites s ON s.id=t.suite_id "
            "WHERE s.suite=%s AND (%s::text IS NULL OR t.tag=%s) "
            "GROUP BY s.id, t.tag ORDER BY s.sequence, t.tag LIMIT %s OFFSET %s"
        )
        params = (suite, tag, tag, limit + 1, offset)
    elif view == "comparisons":
        query = (
            "SELECT c.id, c.baseline_id, c.candidate_id, c.report, c.source_sha256 "
            "FROM sentinel_history.comparisons c "
            "JOIN sentinel_history.suites s ON s.id=c.candidate_id "
            "WHERE s.suite=%s ORDER BY c.sequence LIMIT %s OFFSET %s"
        )
        params = (suite, limit + 1, offset)
    else:
        raise HistoryError("unsupported history view")
    with _connection(dsn) as conn:
        rows = conn.execute(query, params).fetchall()
    return {
        "items": rows[:limit],
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit if len(rows) > limit else None,
    }
